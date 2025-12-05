// Package justitia implements the Justitia incentive mechanism for cross-shard transactions
package justitia

import (
	"fmt"
	"math"
	"math/big"
	"sync"
	"time"
)

// SubsidyMode defines how the subsidy R_AB is calculated
type SubsidyMode int

const (
	// SubsidyNone means no subsidy (R = 0)
	SubsidyNone SubsidyMode = iota
	// SubsidyDestAvg means R = E(f_B) (destination shard average)
	SubsidyDestAvg
	// SubsidySumAvg means R = E(f_A) + E(f_B) (sum of both averages)
	SubsidySumAvg
	// SubsidyCustom means use a custom function to compute R
	SubsidyCustom
	// SubsidyExtremeFixed means fixed subsidy of 1 ETH per cross-shard transaction
	SubsidyExtremeFixed
	// SubsidyPID means use PID controller for dynamic subsidy
	SubsidyPID
	// SubsidyLagrangian means use Lagrangian optimization for dynamic subsidy
	SubsidyLagrangian
)

// String returns the string representation of the subsidy mode
func (m SubsidyMode) String() string {
	switch m {
	case SubsidyNone:
		return "None"
	case SubsidyDestAvg:
		return "DestAvg"
	case SubsidySumAvg:
		return "SumAvg"
	case SubsidyCustom:
		return "Custom"
	case SubsidyExtremeFixed:
		return "ExtremeFixed"
	case SubsidyPID:
		return "PID"
	case SubsidyLagrangian:
		return "Lagrangian"
	default:
		return "Unknown"
	}
}

// DynamicMetrics holds dynamic blockchain state for incentive calculation
type DynamicMetrics struct {
	QueueLengthA     int64     // Queue length in Shard A
	QueueLengthB     int64     // Queue length in Shard B
	AvgWaitTimeA     float64   // Avg wait time in Shard A (ms)
	AvgWaitTimeB     float64   // Avg wait time in Shard B (ms)
	CurrentInflation *big.Int  // Total subsidy issued in current epoch
}

// PIDState holds the internal state for PID controller
type PIDState struct {
	Integral   float64   // Accumulated integral term
	PrevError  float64   // Previous error for derivative calculation
	LastUpdate time.Time // Last update timestamp
}

// PIDParams holds PID controller parameters
type PIDParams struct {
	Kp               float64 // Proportional gain
	Ki               float64 // Integral gain
	Kd               float64 // Derivative gain
	TargetUtilization float64 // Target queue utilization (0.0 to 1.0)
	CapacityB        float64 // Capacity of destination shard queue
	MinSubsidy       float64 // Minimum subsidy multiplier
	MaxSubsidy       float64 // Maximum subsidy multiplier
}

// LagrangianState holds the internal state for Lagrangian optimization
type LagrangianState struct {
	Lambda           float64   // Shadow price (Lagrange multiplier)
	TotalSubsidy     *big.Int  // Total subsidy issued in current epoch
	LastUpdate       time.Time // Last update timestamp
	EpochStartTime   time.Time // Start of current epoch
}

// LagrangianParams holds Lagrangian optimization parameters
type LagrangianParams struct {
	Alpha            float64   // Learning rate for shadow price update
	WindowSize       float64   // Reference window size for congestion normalization
	MinLambda        float64   // Minimum shadow price (prevents division by zero)
	MaxLambda        float64   // Maximum shadow price (prevents extreme values)
	CongestionExp    float64   // Exponent for congestion factor (default: 2.0 for quadratic)
}


// Config holds the configuration for Justitia incentive mechanism
type Config struct {
	Mode         SubsidyMode                       // Subsidy calculation mode
	WindowBlocks int                               // Number of blocks for rolling average
	CustomF      func(*big.Int, *big.Int) *big.Int // Custom function for subsidy (if mode is Custom)
	GammaMin     *big.Int                          // Optional: minimum subsidy budget per block
	GammaMax     *big.Int                          // Optional: maximum subsidy budget per block
	
	// Dynamic algorithm parameters
	PIDParams        PIDParams        // PID controller parameters
	LagrangianParams LagrangianParams // Lagrangian optimization parameters
	MaxInflation     *big.Int         // Maximum inflation limit per epoch
	TargetQueueLen   int64            // Target queue length for dynamic algorithms (deprecated, use PIDParams.TargetUtilization)
}

// Mechanism holds the stateful Justitia incentive mechanism
type Mechanism struct {
	config          *Config
	pidState        *PIDState
	lagrangianState *LagrangianState
	stateLock       sync.Mutex
}

// NewMechanism creates a new Justitia mechanism with the given configuration
func NewMechanism(config *Config) *Mechanism {
	if config == nil {
		config = DefaultConfig()
	}
	now := time.Now()
	m := &Mechanism{
		config: config,
		pidState: &PIDState{
			Integral:   0.0,
			PrevError:  0.0,
			LastUpdate: now,
		},
		lagrangianState: &LagrangianState{
			Lambda:         1.0,
			TotalSubsidy:   big.NewInt(0),
			LastUpdate:     now,
			EpochStartTime: now,
		},
	}
	
	return m
}

// calcPIDSubsidy computes the PID-controlled subsidy based on queue metrics
func calcPIDSubsidy(metrics *DynamicMetrics, config *Config, state *PIDState, EB *big.Int) *big.Int {
	if metrics == nil || EB == nil {
		return big.NewInt(0)
	}

	params := config.PIDParams
	now := time.Now()
	
	// Calculate current utilization (error signal)
	// Error = QueueLengthB / CapacityB - TargetUtilization
	var currentUtilization float64
	if params.CapacityB > 0 {
		currentUtilization = float64(metrics.QueueLengthB) / params.CapacityB
	} else {
		// Fallback: normalize by a reasonable default capacity (e.g., 1000)
		currentUtilization = float64(metrics.QueueLengthB) / 1000.0
	}
	
	error := currentUtilization - params.TargetUtilization
	
	// Calculate time delta for integral and derivative
	dt := now.Sub(state.LastUpdate).Seconds()
	if dt <= 0 {
		dt = 1.0 // Prevent division by zero
	}
	
	// Update integral (with anti-windup)
	state.Integral += error * dt
	// Anti-windup: clamp integral to reasonable bounds
	maxIntegral := 10.0
	if state.Integral > maxIntegral {
		state.Integral = maxIntegral
	} else if state.Integral < -maxIntegral {
		state.Integral = -maxIntegral
	}
	
	// Calculate derivative
	derivative := (error - state.PrevError) / dt
	
	// PID output
	output := params.Kp*error + params.Ki*state.Integral + params.Kd*derivative
	
	// Update state for next iteration
	state.PrevError = error
	state.LastUpdate = now
	
	// Calculate subsidy multiplier: R = EB * (1 + output)
	// Clamp output to reasonable bounds
	multiplier := 1.0 + output
	if multiplier < params.MinSubsidy {
		multiplier = params.MinSubsidy
	}
	if multiplier > params.MaxSubsidy {
		multiplier = params.MaxSubsidy
	}
	
	// Convert EB to float, apply multiplier, convert back to big.Int
	ebFloat := new(big.Float).SetInt(EB)
	resultFloat := new(big.Float).Mul(ebFloat, big.NewFloat(multiplier))
	
	// Convert back to big.Int (truncate)
	result, _ := resultFloat.Int(nil)
	
	// Ensure non-negative
	if result.Sign() < 0 {
		return big.NewInt(0)
	}
	
	return result
}

// calcLagrangianSubsidy computes the Lagrangian-optimized subsidy based on congestion and shadow price
// Formula: R_AB = (EB * CongestionFactor) / Lambda
// where CongestionFactor = (QueueLengthB / WindowSize)^CongestionExp
func calcLagrangianSubsidy(metrics *DynamicMetrics, config *Config, state *LagrangianState, EB *big.Int) *big.Int {
	if metrics == nil || EB == nil {
		return big.NewInt(0)
	}

	params := config.LagrangianParams
	
	// Calculate congestion factor: (QueueLengthB / WindowSize)^CongestionExp
	// This gives quadratic (or higher) preference to congested shards
	var congestionFactor float64
	if params.WindowSize > 0 {
		utilization := float64(metrics.QueueLengthB) / params.WindowSize
		congestionFactor = math.Pow(utilization, params.CongestionExp)
	} else {
		// Fallback: use normalized queue length with default window
		utilization := float64(metrics.QueueLengthB) / 1000.0
		congestionFactor = math.Pow(utilization, params.CongestionExp)
	}
	
	// Apply shadow price (Lagrange multiplier)
	// Higher lambda means we're approaching inflation limit, so reduce subsidy
	lambda := state.Lambda
	if lambda < params.MinLambda {
		lambda = params.MinLambda
	}
	
	// Calculate subsidy: R = EB * CongestionFactor / Lambda
	// Convert EB to float
	ebFloat := new(big.Float).SetInt(EB)
	
	// Apply congestion factor and shadow price
	multiplier := congestionFactor / lambda
	
	// Calculate result
	resultFloat := new(big.Float).Mul(ebFloat, big.NewFloat(multiplier))
	
	// Convert back to big.Int (truncate)
	result, _ := resultFloat.Int(nil)
	
	// Ensure non-negative
	if result.Sign() < 0 {
		return big.NewInt(0)
	}
	
	return result
}

// UpdateShadowPrice updates the Lagrange multiplier (shadow price) based on inflation constraint
// This should be called periodically (e.g., at the end of each block or epoch)
// Formula: Lambda_new = Lambda_old + Alpha * (TotalSubsidy - InflationLimit)
func (m *Mechanism) UpdateShadowPrice(totalSubsidyIssued *big.Int, inflationLimit *big.Int) {
	m.stateLock.Lock()
	defer m.stateLock.Unlock()
	
	if totalSubsidyIssued == nil || inflationLimit == nil {
		return
	}
	
	params := m.config.LagrangianParams
	state := m.lagrangianState
	
	// Calculate constraint violation: TotalSubsidy - Limit
	violation := new(big.Int).Sub(totalSubsidyIssued, inflationLimit)
	
	// Convert to float for calculation
	violationFloat := new(big.Float).SetInt(violation)
	violationVal, _ := violationFloat.Float64()
	
	// Normalize by inflation limit to make alpha scale-independent
	limitFloat := new(big.Float).SetInt(inflationLimit)
	limitVal, _ := limitFloat.Float64()
	
	var normalizedViolation float64
	if limitVal > 0 {
		normalizedViolation = violationVal / limitVal
	} else {
		normalizedViolation = 0
	}
	
	// Update shadow price: Lambda = Lambda + Alpha * NormalizedViolation
	newLambda := state.Lambda + params.Alpha*normalizedViolation
	
	// Clamp lambda to reasonable bounds
	if newLambda < params.MinLambda {
		newLambda = params.MinLambda
	}
	if newLambda > params.MaxLambda {
		newLambda = params.MaxLambda
	}
	
	// Update state
	state.Lambda = newLambda
	state.TotalSubsidy = new(big.Int).Set(totalSubsidyIssued)
	state.LastUpdate = time.Now()
}

// ResetEpoch resets the Lagrangian state for a new epoch
// This should be called at the start of each new epoch
func (m *Mechanism) ResetEpoch() {
	m.stateLock.Lock()
	defer m.stateLock.Unlock()
	
	now := time.Now()
	m.lagrangianState.TotalSubsidy = big.NewInt(0)
	m.lagrangianState.EpochStartTime = now
	m.lagrangianState.LastUpdate = now
	// Note: Lambda is NOT reset - it carries over to provide continuity
}

// GetShadowPrice returns the current shadow price (Lambda)
// This is useful for monitoring and debugging
func (m *Mechanism) GetShadowPrice() float64 {
	m.stateLock.Lock()
	defer m.stateLock.Unlock()
	return m.lagrangianState.Lambda
}

// GetConfig returns the mechanism's configuration
func (m *Mechanism) GetConfig() *Config {
	return m.config
}


// CalculateRAB computes the subsidy R_AB for a cross-shard transaction from shard A to shard B
// EA is E(f_A) (average ITX fee in source shard A)
// EB is E(f_B) (average ITX fee in destination shard B)
// metrics contains dynamic blockchain state (can be nil for static modes)
// IMPORTANT: This function NEVER uses f_AB (the transaction fee)
// Returns a new big.Int containing the subsidy amount
func (m *Mechanism) CalculateRAB(EA, EB *big.Int, metrics *DynamicMetrics) *big.Int {
	m.stateLock.Lock()
	defer m.stateLock.Unlock()
	
	return m.calculateRABInternal(EA, EB, metrics)
}

// calculateRABInternal is the internal implementation (caller must hold lock)
func (m *Mechanism) calculateRABInternal(EA, EB *big.Int, metrics *DynamicMetrics) *big.Int {
	zero := big.NewInt(0)
	mode := m.config.Mode
	customF := m.config.CustomF
	
	switch mode {
	case SubsidyNone:
		return zero
	
	case SubsidyDestAvg:
		if EB == nil {
			return zero
		}
		return new(big.Int).Set(EB)
	
	case SubsidySumAvg:
		if EA == nil && EB == nil {
			return zero
		}
		if EA == nil {
			return new(big.Int).Set(EB)
		}
		if EB == nil {
			return new(big.Int).Set(EA)
		}
		// R = EA + EB
		return new(big.Int).Add(EA, EB)
	
	case SubsidyCustom:
		if customF != nil {
			result := customF(EA, EB)
			if result == nil {
				return zero
			}
			return result
		}
		// Fallback to DestAvg if no custom function provided
		if EB != nil {
			return new(big.Int).Set(EB)
		}
		return zero
	
	case SubsidyExtremeFixed:
		// Extreme fixed subsidy: 1 ETH = 10^18 wei
		return big.NewInt(1000000000000000000)
	
	case SubsidyPID:
		// PID controller-based dynamic subsidy
		return calcPIDSubsidy(metrics, m.config, m.pidState, EB)
	
	case SubsidyLagrangian:
		// Lagrangian optimization-based dynamic subsidy
		// Uses shadow price to enforce inflation constraint
		return calcLagrangianSubsidy(metrics, m.config, m.lagrangianState, EB)
	
	default:
		return zero
	}
}

// RAB is a backward-compatible stateless function for subsidy calculation
// For PID mode, this will not maintain state across calls (use Mechanism instead)
// EA is E(f_A) (average ITX fee in source shard A)
// EB is E(f_B) (average ITX fee in destination shard B)
// metrics contains dynamic blockchain state (can be nil for static modes)
// IMPORTANT: This function NEVER uses f_AB (the transaction fee)
// Returns a new big.Int containing the subsidy amount
func RAB(mode SubsidyMode, EA, EB *big.Int, metrics *DynamicMetrics, customF func(*big.Int, *big.Int) *big.Int) *big.Int {
	zero := big.NewInt(0)

	switch mode {
	case SubsidyNone:
		return zero

	case SubsidyDestAvg:
		if EB == nil {
			return zero
		}
		return new(big.Int).Set(EB)

	case SubsidySumAvg:
		if EA == nil && EB == nil {
			return zero
		}
		if EA == nil {
			return new(big.Int).Set(EB)
		}
		if EB == nil {
			return new(big.Int).Set(EA)
		}
		// R = EA + EB
		return new(big.Int).Add(EA, EB)

	case SubsidyCustom:
		if customF != nil {
			result := customF(EA, EB)
			if result == nil {
				return zero
			}
			return result
		}
		// Fallback to DestAvg if no custom function provided
		if EB != nil {
			return new(big.Int).Set(EB)
		}
		return zero

	case SubsidyExtremeFixed:
		// Extreme fixed subsidy: 1 ETH = 10^18 wei
		return big.NewInt(1000000000000000000)

	case SubsidyPID:
		// PID controller-based dynamic subsidy
		// WARNING: Stateless RAB cannot maintain PID state
		// Use Mechanism.CalculateRAB() for proper PID functionality
		// Fallback to DestAvg
		if EB != nil {
			return new(big.Int).Set(EB)
		}
		return zero

	case SubsidyLagrangian:
		// Lagrangian optimization-based dynamic subsidy
		// WARNING: Stateless RAB cannot maintain shadow price state
		// Use Mechanism.CalculateRAB() for proper Lagrangian functionality
		// Fallback to DestAvg
		if EB != nil {
			return new(big.Int).Set(EB)
		}
		return zero

	default:
		return zero
	}
}

// Split2 performs the 2-party Shapley value split for a cross-shard transaction
// fAB: transaction fee paid by the user
// R: subsidy R_AB (computed by RAB function)
// EA: E(f_A) average ITX fee in source shard A
// EB: E(f_B) average ITX fee in destination shard B
// Returns: (uA, uB) where uA is the utility for shard A proposer, uB for shard B proposer
// Invariant: uA + uB = fAB + R (total rewards are conserved)
func Split2(fAB, R, EA, EB *big.Int) (uA, uB *big.Int) {
	// Ensure all inputs are non-nil
	if fAB == nil {
		fAB = big.NewInt(0)
	}
	if R == nil {
		R = big.NewInt(0)
	}
	if EA == nil {
		EA = big.NewInt(0)
	}
	if EB == nil {
		EB = big.NewInt(0)
	}

	// total = fAB + R
	total := new(big.Int).Add(fAB, R)

	// diff = EA - EB
	diff := new(big.Int).Sub(EA, EB)

	// Shapley formula:
	// uA = (fAB + R + EA - EB) / 2 = (total + diff) / 2
	// uB = (fAB + R + EB - EA) / 2 = (total - diff) / 2
	two := big.NewInt(2)

	uA_calc := new(big.Int).Add(total, diff)
	uA_calc.Div(uA_calc, two)

	uB_calc := new(big.Int).Sub(total, diff)
	uB_calc.Div(uB_calc, two)

	// Ensure non-negative while preserving the invariant uA + uB = total
	zero := big.NewInt(0)
	if uA_calc.Cmp(zero) < 0 {
		// If uA would be negative, give all to uB
		uA = big.NewInt(0)
		uB = new(big.Int).Set(total)
	} else if uB_calc.Cmp(zero) < 0 {
		// If uB would be negative, give all to uA
		uA = new(big.Int).Set(total)
		uB = big.NewInt(0)
	} else {
		// Both positive, use calculated values
		uA = uA_calc
		uB = uB_calc
	}

	return uA, uB
}

// Case represents the three decision cases for including a cross-shard transaction
type Case int

const (
	// Case1: uA >= EA, include CTX in block (high priority)
	Case1 Case = iota + 1
	// Case2: uA <= EA - EB, defer CTX to lowest priority (Phase 3, not dropped)
	Case2
	// Case3: EA - EB < uA < EA, include CTX only if space remains (medium priority)
	Case3
)

// String returns the string representation of the case
func (c Case) String() string {
	switch c {
	case Case1:
		return "Case1(Include)"
	case Case2:
		return "Case2(Defer)"
	case Case3:
		return "Case3(IfSpace)"
	default:
		return "Unknown"
	}
}

// Classify determines which case a cross-shard transaction falls into
// based on the source shard proposer's utility uA
func Classify(uA, EA, EB *big.Int) Case {
	// Ensure all inputs are non-nil
	if uA == nil {
		uA = big.NewInt(0)
	}
	if EA == nil {
		EA = big.NewInt(0)
	}
	if EB == nil {
		EB = big.NewInt(0)
	}

	// Case 1: uA >= EA → always include
	if uA.Cmp(EA) >= 0 {
		return Case1
	}

	// Case 2: uA <= EA - EB → drop/defer
	// Handle underflow: if EB >= EA, then EA - EB <= 0
	if EB.Cmp(EA) >= 0 {
		// EA - EB <= 0, so uA <= EA - EB only if uA <= 0
		if uA.Sign() <= 0 {
			return Case2
		}
		// Otherwise uA > 0 >= EA - EB, so it's Case3
		return Case3
	}

	threshold := new(big.Int).Sub(EA, EB)
	if uA.Cmp(threshold) <= 0 {
		return Case2
	}

	// Case 3: EA - EB < uA < EA → include if space
	return Case3
}

// TxScore computes the score for transaction selection
// For ITX: score = feeToProposer
// For CTX: score = u (utility for the local shard)
type TxScore struct {
	TxHash       string
	IsCrossShard bool
	Score        *big.Int // Fee for ITX, utility for CTX
	Case         Case     // Only relevant for CTX
}

// ComputeCTXScore computes the score for a cross-shard transaction from the perspective of a shard
// isSourceShard: true if computing from source shard A, false if from destination shard B
func ComputeCTXScore(fAB, R, EA, EB *big.Int, isSourceShard bool) *big.Int {
	uA, uB := Split2(fAB, R, EA, EB)
	if isSourceShard {
		return uA
	}
	return uB
}

// ComputeCTXScore computes the score for a cross-shard transaction using the mechanism
// This method automatically calculates the subsidy R_AB using the mechanism's state
func (m *Mechanism) ComputeCTXScore(fAB, EA, EB *big.Int, metrics *DynamicMetrics, isSourceShard bool) *big.Int {
	R := m.CalculateRAB(EA, EB, metrics)
	uA, uB := Split2(fAB, R, EA, EB)
	if isSourceShard {
		return uA
	}
	return uB
}

// ValidateConfig validates the Justitia configuration
func ValidateConfig(cfg *Config) error {
	if cfg.WindowBlocks <= 0 {
		return fmt.Errorf("WindowBlocks must be positive, got %d", cfg.WindowBlocks)
	}
	if cfg.Mode == SubsidyCustom && cfg.CustomF == nil {
		return fmt.Errorf("CustomF function must be provided when mode is SubsidyCustom")
	}
	zero := big.NewInt(0)
	if cfg.GammaMax != nil && cfg.GammaMax.Cmp(zero) > 0 {
		if cfg.GammaMin != nil && cfg.GammaMin.Cmp(cfg.GammaMax) > 0 {
			return fmt.Errorf("GammaMin cannot exceed GammaMax")
		}
	}
	return nil
}

// DefaultConfig returns a default Justitia configuration
func DefaultConfig() *Config {
	return &Config{
		Mode:         SubsidyDestAvg,
		WindowBlocks: 16,
		CustomF:      nil,
		GammaMin:     big.NewInt(0),
		GammaMax:     big.NewInt(0),
		PIDParams: PIDParams{
			Kp:                1.5,    // Proportional gain
			Ki:                0.1,    // Integral gain
			Kd:                0.05,   // Derivative gain
			TargetUtilization: 0.7,    // Target 70% queue utilization
			CapacityB:         1000.0, // Default queue capacity
			MinSubsidy:        0.0,    // Minimum subsidy multiplier (can be 0)
			MaxSubsidy:        5.0,    // Maximum subsidy multiplier (5x EB)
		},
		LagrangianParams: LagrangianParams{
			Alpha:         0.01,   // Learning rate for shadow price update
			WindowSize:    1000.0, // Reference window size for congestion normalization
			MinLambda:     1.0,    // Minimum shadow price
			MaxLambda:     10.0,   // Maximum shadow price (10x reduction at most)
			CongestionExp: 2.0,    // Quadratic congestion preference
		},
		MaxInflation:   big.NewInt(1000000000000000000), // 1 ETH default
		TargetQueueLen: 100,
	}
}
