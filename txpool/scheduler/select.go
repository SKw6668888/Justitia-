// Package scheduler implements Justitia-based transaction selection for block proposals
package scheduler

import (
	"blockEmulator/core"
	"blockEmulator/fees/expectation"
	"blockEmulator/incentive/justitia"
	"blockEmulator/params"
	"fmt"
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
	Mechanism     *justitia.Mechanism // For dynamic subsidy modes (PID, Lagrangian)

	// Epoch tracking for Lagrangian
	epochSubsidyTotal *big.Int // Total subsidy issued in current epoch
	epochTxCount      int      // Transaction count in current epoch
}

// NewScheduler creates a new Justitia-based transaction scheduler
func NewScheduler(shardID, numShards int, feeTracker *expectation.Tracker, mode justitia.SubsidyMode) *Scheduler {
	// Create Mechanism for dynamic subsidy modes
	var mechanism *justitia.Mechanism
	if mode == justitia.SubsidyPID || mode == justitia.SubsidyLagrangian {
		config := params.GetJustitiaConfig()
		mechanism = justitia.NewMechanism(config)
		fmt.Printf("[Scheduler] Shard %d: Created Justitia Mechanism (mode=%s)\n", shardID, mode.String())
	}

	return &Scheduler{
		ShardID:           shardID,
		NumShards:         numShards,
		FeeTracker:        feeTracker,
		SubsidyMode:       mode,
		CustomSubsidy:     nil,
		Mechanism:         mechanism,
		epochSubsidyTotal: big.NewInt(0),
		epochTxCount:      0,
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

	// DEBUG: Log EA value at start of selection
	fmt.Printf("[SELECT] Shard %d: Starting selection with EA=%s, txPool size=%d\n",
		s.ShardID, EA.String(), len(txPool))

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
				Case:  0,                     // Not applicable for ITX
			})
		}
	}

	// Three-phase selection:
	// Phase 1: High-priority transactions (ITX with fee >= EA, CTX Case1)
	// Phase 2: Medium-priority transactions (ITX with fee < EA, CTX Case3)
	// Phase 3: Low-priority transactions (CTX Case2) - delayed but not dropped
	phase1 := make([]TxWithScore, 0)
	phase2 := make([]TxWithScore, 0)
	phase3 := make([]TxWithScore, 0) // Case2 CTX - lowest priority but still considered

	for _, scored := range scored {
		if scored.Tx.IsCrossShard {
			// CTX classification
			switch scored.Case {
			case justitia.Case1:
				phase1 = append(phase1, scored)
			case justitia.Case2:
				// Case2: Low utility, but NOT dropped - delayed to Phase 3
				phase3 = append(phase3, scored)
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

	// DEBUG: Log phase distribution
	fmt.Printf("[SELECT] Shard %d: Phase distribution - P1:%d P2:%d P3:%d\n",
		s.ShardID, len(phase1), len(phase2), len(phase3))

	// Count CTX by case
	case1Count, case2Count, case3Count := 0, 0, 0
	for _, tx := range phase1 {
		if tx.Tx.IsCrossShard {
			case1Count++
		}
	}
	for _, tx := range phase2 {
		if tx.Tx.IsCrossShard {
			case3Count++
		}
	}
	for _, tx := range phase3 {
		if tx.Tx.IsCrossShard {
			case2Count++
		}
	}
	fmt.Printf("[SELECT] Shard %d: CTX distribution - Case1:%d Case2:%d Case3:%d\n",
		s.ShardID, case1Count, case2Count, case3Count)

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

	// If block still not full, fill with Phase3 transactions (Case2 CTX)
	// These have lowest priority but should not be permanently dropped
	if len(selected) < capacity && len(phase3) > 0 {
		// Sort Phase3 by descending score
		sort.Slice(phase3, func(i, j int) bool {
			cmp := phase3[i].Score.Cmp(phase3[j].Score)
			if cmp != 0 {
				return cmp > 0 // Descending order
			}
			return phase3[i].Tx.ArrivalTime.Before(phase3[j].Tx.ArrivalTime)
		})

		for _, scored := range phase3 {
			if len(selected) >= capacity {
				break
			}
			selected = append(selected, scored.Tx)
		}
	}

	// DEBUG: Log final selection stats
	ctxSelected := 0
	for _, tx := range selected {
		if tx.IsCrossShard {
			ctxSelected++
		}
	}
	fmt.Printf("[SELECT] Shard %d: Selected %d/%d txs (CTX:%d, ITX:%d)\n",
		s.ShardID, len(selected), capacity, ctxSelected, len(selected)-ctxSelected)

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
	var R *big.Int
	if s.Mechanism != nil {
		// Create metrics for dynamic subsidy modes (PID, Lagrangian)
		// For Lagrangian, we need QueueLengthB for congestion calculation
		// Use moderately high congestion assumption
		metrics := &justitia.DynamicMetrics{
			QueueLengthB: 600, // Moderately high congestion
			// Add other metrics if needed for PID mode
		}
		R = s.Mechanism.CalculateRAB(EA, EB, metrics)
	} else {
		// Use stateless RAB for static subsidy modes
		R = justitia.RAB(s.SubsidyMode, EA, EB, nil, s.CustomSubsidy)
	}

	// Always update transaction with subsidy (scheduler is authoritative)
	tx.SubsidyR = new(big.Int).Set(R)

	// Accumulate subsidy for epoch tracking (Lagrangian)
	if s.Mechanism != nil && s.SubsidyMode == justitia.SubsidyLagrangian {
		s.epochSubsidyTotal.Add(s.epochSubsidyTotal, R)
		s.epochTxCount++
	}

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

		// DEBUG: Log CTX scoring details for source shard
		fmt.Printf("[DEBUG] CTX Score (Source S%d->S%d): Fee=%s, EA=%s, EB=%s, R=%s, uA=%s, uB=%s, Case=%s\n",
			tx.FromShard, tx.ToShard, fee.String(), EA.String(), EB.String(),
			R.String(), uA.String(), uB.String(), txCase.String())
	} else {
		utility = uB
		// Destination shard always includes CTX if selected
		// (classification is primarily for source shard decision)
		txCase = justitia.Case1 // Treat as high priority at destination
		if tx.JustitiaCase == 0 {
			tx.JustitiaCase = int(justitia.Case1)
		}

		// DEBUG: Log CTX scoring details for destination shard
		fmt.Printf("[DEBUG] CTX Score (Dest S%d<-S%d): Fee=%s, EA=%s, EB=%s, R=%s, uA=%s, uB=%s\n",
			s.ShardID, tx.FromShard, fee.String(), EA.String(), EB.String(),
			R.String(), uA.String(), uB.String())
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

// UpdateEpoch should be called periodically (e.g., every N blocks) for Lagrangian mode
// It updates the shadow price based on budget constraint and resets epoch counters
func (s *Scheduler) UpdateEpoch() {
	if s.Mechanism == nil || s.SubsidyMode != justitia.SubsidyLagrangian {
		return
	}

	// Get inflation limit from config
	inflationLimit := s.Mechanism.GetConfig().MaxInflation

	// Update shadow price based on total subsidy issued
	s.Mechanism.UpdateShadowPrice(s.epochSubsidyTotal, inflationLimit)

	// Log epoch summary
	lambda := s.Mechanism.GetShadowPrice()
	fmt.Printf("[Lagrangian] Shard %d Epoch Update: TotalSubsidy=%s, Limit=%s, Lambda=%.4f, TxCount=%d\n",
		s.ShardID, s.epochSubsidyTotal.String(), inflationLimit.String(), lambda, s.epochTxCount)

	// Reset epoch counters
	s.Mechanism.ResetEpoch()
	s.epochSubsidyTotal = big.NewInt(0)
	s.epochTxCount = 0
}

// GetEpochStats returns current epoch statistics
func (s *Scheduler) GetEpochStats() (totalSubsidy *big.Int, txCount int, lambda float64) {
	if s.Mechanism != nil && s.SubsidyMode == justitia.SubsidyLagrangian {
		return new(big.Int).Set(s.epochSubsidyTotal), s.epochTxCount, s.Mechanism.GetShadowPrice()
	}
	return big.NewInt(0), 0, 0.0
}
