// Package justitia implements the Justitia incentive mechanism for cross-shard transactions
package justitia

import (
	"fmt"
	"math/big"
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
	default:
		return "Unknown"
	}
}

// Config holds the configuration for Justitia incentive mechanism
type Config struct {
	Mode         SubsidyMode                          // Subsidy calculation mode
	WindowBlocks int                                  // Number of blocks for rolling average
	CustomF      func(*big.Int, *big.Int) *big.Int   // Custom function for subsidy (if mode is Custom)
	GammaMin     *big.Int                             // Optional: minimum subsidy budget per block
	GammaMax     *big.Int                             // Optional: maximum subsidy budget per block
}

// RAB computes the subsidy R_AB for a cross-shard transaction from shard A to shard B
// EA is E(f_A) (average ITX fee in source shard A)
// EB is E(f_B) (average ITX fee in destination shard B)
// IMPORTANT: This function NEVER uses f_AB (the transaction fee)
// Returns a new big.Int containing the subsidy amount
func RAB(mode SubsidyMode, EA, EB *big.Int, customF func(*big.Int, *big.Int) *big.Int) *big.Int {
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
	// Case2: uA <= EA - EB, drop or defer CTX (very low priority, usually excluded)
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
		return "Case2(Drop)"
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
	TxHash      string
	IsCrossShard bool
	Score       *big.Int  // Fee for ITX, utility for CTX
	Case        Case      // Only relevant for CTX
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
	}
}
