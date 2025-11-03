// Package scheduler implements Justitia-based transaction selection for block proposals
package scheduler

import (
	"blockEmulator/core"
	"blockEmulator/fees/expectation"
	"blockEmulator/incentive/justitia"
	"sort"
)

// TxWithScore wraps a transaction with its computed score for selection
type TxWithScore struct {
	Tx    *core.Transaction
	Score uint64
	Case  justitia.Case // Only relevant for CTX
}

// Scheduler handles transaction selection using Justitia incentive mechanism
type Scheduler struct {
	ShardID      int
	NumShards    int
	FeeTracker   *expectation.Tracker
	SubsidyMode  justitia.SubsidyMode
	CustomSubsidy func(uint64, uint64) uint64
}

// NewScheduler creates a new Justitia-based transaction scheduler
func NewScheduler(shardID, numShards int, feeTracker *expectation.Tracker, mode justitia.SubsidyMode) *Scheduler {
	return &Scheduler{
		ShardID:      shardID,
		NumShards:    numShards,
		FeeTracker:   feeTracker,
		SubsidyMode:  mode,
		CustomSubsidy: nil,
	}
}

// SetCustomSubsidy sets a custom subsidy function
func (s *Scheduler) SetCustomSubsidy(f func(uint64, uint64) uint64) {
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
			scored = append(scored, TxWithScore{
				Tx:    tx,
				Score: tx.FeeToProposer, // ITX score = fee
				Case:  0,                 // Not applicable for ITX
			})
		}
	}

	// Phase 1: Select high-priority transactions
	// - ITX with fee >= EA
	// - CTX in Case1 (uA >= EA)
	phase1 := make([]TxWithScore, 0)
	phase2 := make([]TxWithScore, 0) // For remaining ITX and Case3 CTX
	excluded := 0 // Case2 CTX are excluded

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
			if scored.Score >= EA {
				phase1 = append(phase1, scored)
			} else {
				phase2 = append(phase2, scored)
			}
		}
	}

	// Sort Phase1 by descending score (highest score first)
	sort.Slice(phase1, func(i, j int) bool {
		if phase1[i].Score != phase1[j].Score {
			return phase1[i].Score > phase1[j].Score
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
			if phase2[i].Score != phase2[j].Score {
				return phase2[i].Score > phase2[j].Score
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
func (s *Scheduler) scoreCTX(tx *core.Transaction, EA uint64) (score uint64, txCase justitia.Case) {
	// Determine if this shard is source (A) or destination (B)
	isSourceShard := (tx.FromShard == s.ShardID)
	
	// Get average fees for both shards
	var EB uint64
	if isSourceShard {
		// This is shard A (source), get EB from destination shard
		EB = s.FeeTracker.GetAvgITXFee(tx.ToShard)
	} else {
		// This is shard B (destination), get EA from source shard
		EA = s.FeeTracker.GetAvgITXFee(tx.FromShard)
		EB = s.FeeTracker.GetAvgITXFee(s.ShardID) // Local shard is B
	}

	// Compute subsidy R_AB
	R := justitia.RAB(s.SubsidyMode, EA, EB, s.CustomSubsidy)
	
	// Update transaction with subsidy (if not already set)
	if tx.SubsidyR == 0 {
		tx.SubsidyR = R
	}

	// Compute Shapley split
	uA, uB := justitia.Split2(tx.FeeToProposer, R, EA, EB)
	
	// Update transaction utilities
	tx.UtilityA = uA
	tx.UtilityB = uB

	// Determine score based on which shard we are
	var utility uint64
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

	return utility, txCase
}

// EstimateBlockReward estimates the total reward for proposing a block with given transactions
func (s *Scheduler) EstimateBlockReward(txs []*core.Transaction) uint64 {
	var totalReward uint64
	
	for _, tx := range txs {
		if tx.FromShard == s.ShardID {
			// Source shard: get uA
			totalReward += tx.UtilityA
		} else if tx.ToShard == s.ShardID {
			// Destination shard: get uB
			totalReward += tx.UtilityB
		}
	}
	
	return totalReward
}

