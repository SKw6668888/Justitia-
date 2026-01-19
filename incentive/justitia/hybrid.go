// Package justitia implements hybrid PID-Lagrangian subsidy control
// Hierarchical Control: Lagrangian sets strategic targets, PID provides tactical tracking
package justitia

import (
	"fmt"
	"math/big"
	"time"
)

// HybridController implements hierarchical control combining Lagrangian and PID
type HybridController struct {
	// Lagrangian layer (slow, strategic)
	lagMechanism      *Mechanism
	epochInterval     int       // Blocks per epoch
	targetSubsidy     *big.Int  // Current target set by Lagrangian
	epochSubsidyTotal *big.Int  // Total subsidy issued this epoch
	epochTxCount      int       // Transaction count this epoch
	
	// PID layer (fast, tactical)
	pidState  *PIDState
	pidParams *PIDParams
	
	// Tracking
	blocksSinceEpoch int
	shardID          int
}

// NewHybridController creates a new hybrid controller
func NewHybridController(config *Config, shardID int, epochInterval int) *HybridController {
	if epochInterval <= 0 {
		epochInterval = 10 // Default: 10 blocks per epoch
	}
	
	return &HybridController{
		lagMechanism:      NewMechanism(config),
		epochInterval:     epochInterval,
		targetSubsidy:     big.NewInt(0),
		epochSubsidyTotal: big.NewInt(0),
		epochTxCount:      0,
		pidState: &PIDState{
			Integral:   0.0,
			PrevError:  0.0,
			LastUpdate: time.Now(),
		},
		pidParams:        &config.PIDParams,
		blocksSinceEpoch: 0,
		shardID:          shardID,
	}
}

// CalculateSubsidy computes subsidy using hierarchical control
// Lagrangian sets target R*, PID tracks it with fast adjustments
func (h *HybridController) CalculateSubsidy(metrics *DynamicMetrics, EA, EB *big.Int) *big.Int {
	if metrics == nil || EA == nil || EB == nil {
		return big.NewInt(0)
	}
	
	// Step 1: Check if we need Epoch update (Lagrangian layer)
	h.blocksSinceEpoch++
	if h.blocksSinceEpoch >= h.epochInterval {
		h.updateEpochTarget(metrics, EA, EB)
		h.blocksSinceEpoch = 0
	}
	
	// Step 2: PID tracking (fast layer)
	R_final := h.pidTracking(metrics, EB)
	
	// Step 3: Accumulate for next epoch update
	h.epochSubsidyTotal.Add(h.epochSubsidyTotal, R_final)
	h.epochTxCount++
	
	return R_final
}

// updateEpochTarget uses Lagrangian to compute optimal target subsidy
func (h *HybridController) updateEpochTarget(metrics *DynamicMetrics, EA, EB *big.Int) {
	// Lagrangian computes globally optimal target
	h.targetSubsidy = h.lagMechanism.CalculateRAB(EA, EB, metrics)
	
	// Update shadow price based on budget constraint
	inflationLimit := h.lagMechanism.GetConfig().MaxInflation
	h.lagMechanism.UpdateShadowPrice(h.epochSubsidyTotal, inflationLimit)
	
	// Get updated lambda
	lambda := h.lagMechanism.GetShadowPrice()
	
	// Log epoch summary
	fmt.Printf("[Hybrid] Shard %d Epoch Update: Target=%s ETH, TotalSubsidy=%s ETH, Lambda=%.4f, TxCount=%d\n",
		h.shardID,
		new(big.Float).Quo(new(big.Float).SetInt(h.targetSubsidy), big.NewFloat(1e18)),
		new(big.Float).Quo(new(big.Float).SetInt(h.epochSubsidyTotal), big.NewFloat(1e18)),
		lambda,
		h.epochTxCount)
	
	// Reset epoch counters
	h.lagMechanism.ResetEpoch()
	h.epochSubsidyTotal = big.NewInt(0)
	h.epochTxCount = 0
}

// pidTracking uses PID to track Lagrangian's target with fast adjustments
func (h *HybridController) pidTracking(metrics *DynamicMetrics, EB *big.Int) *big.Int {
	now := time.Now()
	
	// Calculate current utilization (error signal)
	var currentUtilization float64
	if h.pidParams.CapacityB > 0 {
		currentUtilization = float64(metrics.QueueLengthB) / h.pidParams.CapacityB
	} else {
		currentUtilization = float64(metrics.QueueLengthB) / 1000.0
	}
	
	// Error = current utilization - target utilization
	error := currentUtilization - h.pidParams.TargetUtilization
	
	// Time delta
	dt := now.Sub(h.pidState.LastUpdate).Seconds()
	if dt <= 0 {
		dt = 1.0
	}
	
	// Update integral with Anti-Windup (stricter bounds for hybrid)
	h.pidState.Integral += error * dt
	maxIntegral := 5.0 // Tighter than standalone PID (was 10.0)
	if h.pidState.Integral > maxIntegral {
		h.pidState.Integral = maxIntegral
	} else if h.pidState.Integral < -maxIntegral {
		h.pidState.Integral = -maxIntegral
	}
	
	// Calculate derivative
	derivative := (error - h.pidState.PrevError) / dt
	
	// PID output (correction term)
	correction := h.pidParams.Kp*error + h.pidParams.Ki*h.pidState.Integral + h.pidParams.Kd*derivative
	
	// Update state
	h.pidState.PrevError = error
	h.pidState.LastUpdate = now
	
	// Final subsidy = Lagrangian target + PID correction
	targetFloat := new(big.Float).SetInt(h.targetSubsidy)
	
	// Convert EB to float for scaling correction
	ebFloat := new(big.Float).SetInt(EB)
	correctionScaled := new(big.Float).Mul(ebFloat, big.NewFloat(correction))
	
	// Add correction to target
	finalFloat := new(big.Float).Add(targetFloat, correctionScaled)
	
	// Clamp to [MinSubsidy * EB, MaxSubsidy * EB]
	minBound := new(big.Float).Mul(ebFloat, big.NewFloat(h.pidParams.MinSubsidy))
	maxBound := new(big.Float).Mul(ebFloat, big.NewFloat(h.pidParams.MaxSubsidy))
	
	if finalFloat.Cmp(minBound) < 0 {
		finalFloat = minBound
	}
	if finalFloat.Cmp(maxBound) > 0 {
		finalFloat = maxBound
	}
	
	// Convert back to big.Int
	result, _ := finalFloat.Int(nil)
	
	// Ensure non-negative
	if result.Sign() < 0 {
		return big.NewInt(0)
	}
	
	return result
}

// GetEpochStats returns current epoch statistics
func (h *HybridController) GetEpochStats() (totalSubsidy *big.Int, txCount int, lambda float64, target *big.Int) {
	return new(big.Int).Set(h.epochSubsidyTotal),
		h.epochTxCount,
		h.lagMechanism.GetShadowPrice(),
		new(big.Int).Set(h.targetSubsidy)
}

// GetConfig returns the underlying configuration
func (h *HybridController) GetConfig() *Config {
	return h.lagMechanism.GetConfig()
}

// UpdateShadowPrice manually updates lambda (for testing)
func (h *HybridController) UpdateShadowPrice(totalSubsidy, inflationLimit *big.Int) {
	h.lagMechanism.UpdateShadowPrice(totalSubsidy, inflationLimit)
}

// GetShadowPrice returns current shadow price
func (h *HybridController) GetShadowPrice() float64 {
	return h.lagMechanism.GetShadowPrice()
}

// ResetEpoch resets epoch counters (for testing)
func (h *HybridController) ResetEpoch() {
	h.epochSubsidyTotal = big.NewInt(0)
	h.epochTxCount = 0
	h.blocksSinceEpoch = 0
	h.lagMechanism.ResetEpoch()
}
