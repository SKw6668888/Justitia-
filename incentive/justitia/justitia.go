// Package justitia implements the Justitia incentive mechanism for cross-shard transactions
package justitia

import (
	"fmt"
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
	CustomF      func(uint64, uint64) uint64         // Custom function for subsidy (if mode is Custom)
	GammaMin     uint64                               // Optional: minimum subsidy budget per block
	GammaMax     uint64                               // Optional: maximum subsidy budget per block
}

// RAB computes the subsidy R_AB for a cross-shard transaction from shard A to shard B
// EA is E(f_A) (average ITX fee in source shard A)
// EB is E(f_B) (average ITX fee in destination shard B)
// IMPORTANT: This function NEVER uses f_AB (the transaction fee)
func RAB(mode SubsidyMode, EA, EB uint64, customF func(uint64, uint64) uint64) uint64 {
	switch mode {
	case SubsidyNone:
		return 0
	case SubsidyDestAvg:
		return EB
	case SubsidySumAvg:
		return EA + EB
	case SubsidyCustom:
		if customF != nil {
			return customF(EA, EB)
		}
		// Fallback to DestAvg if no custom function provided
		return EB
	default:
		return 0
	}
}

// Split2 performs the 2-party Shapley value split for a cross-shard transaction
// fAB: transaction fee paid by the user
// R: subsidy R_AB (computed by RAB function)
// EA: E(f_A) average ITX fee in source shard A
// EB: E(f_B) average ITX fee in destination shard B
// Returns: (uA, uB) where uA is the utility for shard A proposer, uB for shard B proposer
// Invariant: uA + uB = fAB + R (total rewards are conserved)
func Split2(fAB, R, EA, EB uint64) (uA, uB uint64) {
	// Use signed arithmetic to handle potential negative intermediate values
	total := int64(fAB) + int64(R)
	diff := int64(EA) - int64(EB)
	
	// Shapley formula:
	// uA = (fAB + R + EA - EB) / 2
	// uB = (fAB + R + EB - EA) / 2
	uA_signed := (total + diff) / 2
	uB_signed := (total - diff) / 2
	
	// Ensure non-negative while preserving the invariant uA + uB = total
	if uA_signed < 0 {
		// If uA would be negative, give all to uB
		uA = 0
		uB = uint64(total)
	} else if uB_signed < 0 {
		// If uB would be negative, give all to uA
		uA = uint64(total)
		uB = 0
	} else {
		// Both positive, use calculated values
		uA = uint64(uA_signed)
		uB = uint64(uB_signed)
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
func Classify(uA, EA, EB uint64) Case {
	// Case 1: uA >= EA → always include
	if uA >= EA {
		return Case1
	}
	
	// Case 2: uA <= EA - EB → drop/defer
	// Handle underflow: if EB >= EA, then EA - EB would underflow, so check first
	if EB >= EA {
		// EA - EB <= 0, so uA <= EA - EB only if uA == 0
		if uA == 0 {
			return Case2
		}
		// Otherwise uA > 0 >= EA - EB, so it's Case3
		return Case3
	}
	
	threshold := EA - EB
	if uA <= threshold {
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
	Score       uint64  // Fee for ITX, utility for CTX
	Case        Case    // Only relevant for CTX
}

// ComputeCTXScore computes the score for a cross-shard transaction from the perspective of a shard
// isSourceShard: true if computing from source shard A, false if from destination shard B
func ComputeCTXScore(fAB, R, EA, EB uint64, isSourceShard bool) uint64 {
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
	if cfg.GammaMax > 0 && cfg.GammaMin > cfg.GammaMax {
		return fmt.Errorf("GammaMin (%d) cannot exceed GammaMax (%d)", cfg.GammaMin, cfg.GammaMax)
	}
	return nil
}

// DefaultConfig returns a default Justitia configuration
func DefaultConfig() *Config {
	return &Config{
		Mode:         SubsidyDestAvg,
		WindowBlocks: 16,
		CustomF:      nil,
		GammaMin:     0,
		GammaMax:     0,
	}
}

