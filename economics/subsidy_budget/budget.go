// Package subsidy_budget implements per-block subsidy budget controls
package subsidy_budget

import (
	"fmt"
)

// Budget defines the per-block subsidy constraints
type Budget struct {
	Bmin uint64 // Minimum total subsidy per block
	Bmax uint64 // Maximum total subsidy per block
}

// NewBudget creates a new subsidy budget with min and max limits
func NewBudget(min, max uint64) (*Budget, error) {
	if max > 0 && min > max {
		return nil, fmt.Errorf("Bmin (%d) cannot exceed Bmax (%d)", min, max)
	}
	return &Budget{
		Bmin: min,
		Bmax: max,
	}, nil
}

// ScalingFactor represents a rational number (numerator / denominator) for scaling
type ScalingFactor struct {
	Num uint64 // Numerator
	Den uint64 // Denominator
}

// Apply computes the scaling factor to apply to subsidies based on the actual sum
// sumR: the sum of all subsidies R_AB for CTXs to be settled in this block
// Returns: scaling factor (num, den) such that adjusted R = R * num / den
//
// Rules:
// - If sumR > Bmax: scale down proportionally (num < den)
// - If sumR < Bmin: scale up proportionally (num > den)
// - If Bmin <= sumR <= Bmax: no scaling (num = den = 1)
// - If no budget limits set (Bmax = 0): no scaling
func (b *Budget) Apply(sumR uint64) ScalingFactor {
	// No budget limits
	if b.Bmax == 0 {
		return ScalingFactor{Num: 1, Den: 1}
	}

	// Sum exceeds maximum: scale down
	if sumR > b.Bmax {
		return ScalingFactor{
			Num: b.Bmax,
			Den: sumR,
		}
	}

	// Sum below minimum: scale up (if Bmin is set)
	if b.Bmin > 0 && sumR < b.Bmin && sumR > 0 {
		return ScalingFactor{
			Num: b.Bmin,
			Den: sumR,
		}
	}

	// Within bounds or sumR = 0: no scaling
	return ScalingFactor{Num: 1, Den: 1}
}

// ScaleSubsidy applies the scaling factor to a single subsidy value
func (sf ScalingFactor) ScaleSubsidy(R uint64) uint64 {
	if sf.Den == 0 {
		return R
	}
	// Perform multiplication first to maintain precision, then divide
	// Be careful of overflow for very large values
	return (R * sf.Num) / sf.Den
}

// IsScalingNeeded returns true if scaling will be applied
func (sf ScalingFactor) IsScalingNeeded() bool {
	return sf.Num != sf.Den
}

// String returns a string representation of the scaling factor
func (sf ScalingFactor) String() string {
	if sf.Num == sf.Den {
		return "1 (no scaling)"
	}
	return fmt.Sprintf("%d/%d", sf.Num, sf.Den)
}

// AnnualToPerBlock converts annual subsidy budget to per-block budget
// annualBudget: total annual subsidy
// blocksPerYear: expected number of blocks per year
// Returns: per-block budget
func AnnualToPerBlock(annualBudget uint64, blocksPerYear uint64) uint64 {
	if blocksPerYear == 0 {
		return 0
	}
	return annualBudget / blocksPerYear
}

// ComputeBlocksPerYear estimates blocks per year from block interval
// blockIntervalMs: block interval in milliseconds
// Returns: approximate blocks per year
func ComputeBlocksPerYear(blockIntervalMs int) uint64 {
	if blockIntervalMs <= 0 {
		return 0
	}
	// blocks per year = (365.25 days * 24 hours * 60 min * 60 sec * 1000 ms) / blockIntervalMs
	msPerYear := uint64(365.25 * 24 * 60 * 60 * 1000)
	return msPerYear / uint64(blockIntervalMs)
}

// BudgetConfig holds configuration for subsidy budgeting
type BudgetConfig struct {
	GammaMinAnnual uint64 // Minimum annual subsidy
	GammaMaxAnnual uint64 // Maximum annual subsidy
	BlockIntervalMs int    // Block interval in milliseconds
}

// ToBudget converts annual budget configuration to per-block budget
func (cfg *BudgetConfig) ToBudget() (*Budget, error) {
	blocksPerYear := ComputeBlocksPerYear(cfg.BlockIntervalMs)
	if blocksPerYear == 0 {
		return nil, fmt.Errorf("invalid block interval: %d ms", cfg.BlockIntervalMs)
	}

	bmin := AnnualToPerBlock(cfg.GammaMinAnnual, blocksPerYear)
	bmax := AnnualToPerBlock(cfg.GammaMaxAnnual, blocksPerYear)

	return NewBudget(bmin, bmax)
}

// ApplyBudgetToBlock applies budget constraints to a set of subsidies
// Returns: scaled subsidies and the scaling factor used
func ApplyBudgetToBlock(budget *Budget, subsidies []uint64) ([]uint64, ScalingFactor) {
	// Calculate sum of all subsidies
	var sumR uint64
	for _, r := range subsidies {
		sumR += r
	}

	// Get scaling factor
	sf := budget.Apply(sumR)

	// If no scaling needed, return original
	if !sf.IsScalingNeeded() {
		return subsidies, sf
	}

	// Apply scaling to each subsidy
	scaled := make([]uint64, len(subsidies))
	for i, r := range subsidies {
		scaled[i] = sf.ScaleSubsidy(r)
	}

	return scaled, sf
}

