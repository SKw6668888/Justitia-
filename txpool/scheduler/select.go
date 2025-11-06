// Package scheduler implements Justitia-based transaction selection for block proposals
package scheduler

import (
	"blockEmulator/core"
	"blockEmulator/fees/expectation"
	"blockEmulator/incentive/justitia"
	"math/big"
	"sort"
)

// TxWithScore wraps a transaction with its computed score for selection
type TxWithScore struct {
	Tx    *core.Transaction
	Score *big.Int
	Case  justitia.Case // Only relevant for CTX
}

// Scheduler handles transaction selection using Justitia incentive mechanism
type Scheduler struct {
	ShardID       int
	NumShards     int
	FeeTracker    *expectation.Tracker
	SubsidyMode   justitia.SubsidyMode
	CustomSubsidy func(*big.Int, *big.Int) *big.Int
}

// NewScheduler creates a new Justitia-based transaction scheduler
func NewScheduler(shardID, numShards int, feeTracker *expectation.Tracker, mode justitia.SubsidyMode) *Scheduler {
	return &Scheduler{
		ShardID:       shardID,
		NumShards:     numShards,
		FeeTracker:    feeTracker,
		SubsidyMode:   mode,
		CustomSubsidy: nil,
	}
}

// SetCustomSubsidy sets a custom subsidy function
func (s *Scheduler) SetCustomSubsidy(f func(*big.Int, *big.Int) *big.Int) {
	s.CustomSubsidy = f
}

// SelectForBlock selects transactions for a new block using Justitia scoring
// capacity: maximum number of transactions the block can hold
// txPool: available transactions (ITX and CTX)
// Returns: selected transactions in priority order
func (s *Scheduler) SelectForBlock(capacity int, txPool []*core.Transaction) []*core.Transaction {
	if capacity <= 0 || len(txPool) == 0 {
		return nil
	}

	// Get current average ITX fee for this shard
	EA := s.FeeTracker.GetAvgITXFee(s.ShardID)

	// Compute scores for all transactions
	scored := make([]TxWithScore, 0, len(txPool))

	for _, tx := range txPool {
		if tx.IsCrossShard {
			// Cross-shard transaction (CTX)
			score, txCase := s.scoreCTX(tx, EA)
			scored = append(scored, TxWithScore{
				Tx:    tx,
				Score: score,
				Case:  txCase,
			})
		} else {
			// Intra-shard transaction (ITX)
			// Ensure FeeToProposer is not nil
			fee := tx.FeeToProposer
			if fee == nil {
				fee = big.NewInt(0)
			}
			scored = append(scored, TxWithScore{
				Tx:    tx,
				Score: new(big.Int).Set(fee), // ITX score = fee
				Case:  0,                      // Not applicable for ITX
			})
		}
	}

	// Phase 1: Select high-priority transactions
	// - ITX with fee >= EA
	// - CTX in Case1 (uA >= EA)
	phase1 := make([]TxWithScore, 0)
	phase2 := make([]TxWithScore, 0) // For remaining ITX and Case3 CTX
	excluded := 0                     // Case2 CTX are excluded

	for _, scored := range scored {
		if scored.Tx.IsCrossShard {
			// CTX classification
			switch scored.Case {
			case justitia.Case1:
				phase1 = append(phase1, scored)
			case justitia.Case2:
				excluded++
				// Drop Case2 CTX
			case justitia.Case3:
				phase2 = append(phase2, scored)
			}
		} else {
			// ITX
			if scored.Score.Cmp(EA) >= 0 {
				phase1 = append(phase1, scored)
			} else {
				phase2 = append(phase2, scored)
			}
		}
	}

	// Sort Phase1 by descending score (highest score first)
	sort.Slice(phase1, func(i, j int) bool {
		cmp := phase1[i].Score.Cmp(phase1[j].Score)
		if cmp != 0 {
			return cmp > 0 // Descending order
		}
		// Tie-breaker: FIFO (earlier arrival time)
		return phase1[i].Tx.ArrivalTime.Before(phase1[j].Tx.ArrivalTime)
	})

	// Fill block with Phase1 transactions
	selected := make([]*core.Transaction, 0, capacity)
	for _, scored := range phase1 {
		if len(selected) >= capacity {
			break
		}
		selected = append(selected, scored.Tx)
	}

	// If block not full, fill with Phase2 transactions
	if len(selected) < capacity {
		// Sort Phase2 by descending score
		sort.Slice(phase2, func(i, j int) bool {
			cmp := phase2[i].Score.Cmp(phase2[j].Score)
			if cmp != 0 {
				return cmp > 0 // Descending order
			}
			return phase2[i].Tx.ArrivalTime.Before(phase2[j].Tx.ArrivalTime)
		})

		for _, scored := range phase2 {
			if len(selected) >= capacity {
				break
			}
			selected = append(selected, scored.Tx)
		}
	}

	return selected
}

// scoreCTX computes the score and case classification for a cross-shard transaction
// from the perspective of the current shard
func (s *Scheduler) scoreCTX(tx *core.Transaction, EA *big.Int) (score *big.Int, txCase justitia.Case) {
	// Determine if this shard is source (A) or destination (B)
	isSourceShard := (tx.FromShard == s.ShardID)

	// Get average fees for both shards
	var EB *big.Int
	if isSourceShard {
		// This is shard A (source), get EB from destination shard
		EB = s.FeeTracker.GetAvgITXFee(tx.ToShard)
	} else {
		// This is shard B (destination), get EA from source shard
		EA = s.FeeTracker.GetAvgITXFee(tx.FromShard)
		EB = s.FeeTracker.GetAvgITXFee(s.ShardID) // Local shard is B
	}

	// Compute subsidy R_AB (CRITICAL: This NEVER uses tx.FeeToProposer)
	R := justitia.RAB(s.SubsidyMode, EA, EB, s.CustomSubsidy)

	// Always update transaction with subsidy (scheduler is authoritative)
	tx.SubsidyR = new(big.Int).Set(R)

	// Ensure FeeToProposer is not nil
	fee := tx.FeeToProposer
	if fee == nil {
		fee = big.NewInt(0)
	}

	// Compute Shapley split
	uA, uB := justitia.Split2(fee, R, EA, EB)

	// Update transaction utilities
	tx.UtilityA = new(big.Int).Set(uA)
	tx.UtilityB = new(big.Int).Set(uB)

	// Determine score based on which shard we are
	var utility *big.Int
	if isSourceShard {
		utility = uA
		// Classify from source shard perspective
		txCase = justitia.Classify(uA, EA, EB)
		tx.JustitiaCase = int(txCase)
	} else {
		utility = uB
		// Destination shard always includes CTX if selected
		// (classification is primarily for source shard decision)
		txCase = justitia.Case1 // Treat as high priority at destination
		if tx.JustitiaCase == 0 {
			tx.JustitiaCase = int(justitia.Case1)
		}
	}

	return new(big.Int).Set(utility), txCase
}

// EstimateBlockReward estimates the total reward for proposing a block with given transactions
func (s *Scheduler) EstimateBlockReward(txs []*core.Transaction) *big.Int {
	totalReward := big.NewInt(0)

	for _, tx := range txs {
		if tx.FromShard == s.ShardID {
			// Source shard: get uA
			if tx.UtilityA != nil {
				totalReward.Add(totalReward, tx.UtilityA)
			}
		} else if tx.ToShard == s.ShardID {
			// Destination shard: get uB
			if tx.UtilityB != nil {
				totalReward.Add(totalReward, tx.UtilityB)
			}
		}
	}

	return totalReward
}
