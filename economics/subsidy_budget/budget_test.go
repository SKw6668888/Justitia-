package subsidy_budget

import (
	"testing"
)

// TestNewBudget tests budget creation
func TestNewBudget(t *testing.T) {
	// Valid budget
	b, err := NewBudget(100, 1000)
	if err != nil {
		t.Errorf("Valid budget should not error: %v", err)
	}
	if b.Bmin != 100 || b.Bmax != 1000 {
		t.Errorf("Budget values incorrect: got Bmin=%d, Bmax=%d", b.Bmin, b.Bmax)
	}

	// Invalid: min > max
	_, err = NewBudget(1000, 100)
	if err == nil {
		t.Error("Should error when Bmin > Bmax")
	}

	// Valid: no limits
	b, err = NewBudget(0, 0)
	if err != nil {
		t.Errorf("Zero limits should be valid: %v", err)
	}
}

// TestBudget_Apply_NoScaling tests when no scaling is needed
func TestBudget_Apply_NoScaling(t *testing.T) {
	b, _ := NewBudget(100, 1000)

	// sumR within bounds
	sf := b.Apply(500)
	if sf.Num != 1 || sf.Den != 1 {
		t.Errorf("No scaling needed, expected 1/1, got %d/%d", sf.Num, sf.Den)
	}
	if sf.IsScalingNeeded() {
		t.Error("IsScalingNeeded should be false")
	}

	// sumR exactly at Bmin
	sf = b.Apply(100)
	if sf.Num != 1 || sf.Den != 1 {
		t.Errorf("At Bmin, expected 1/1, got %d/%d", sf.Num, sf.Den)
	}

	// sumR exactly at Bmax
	sf = b.Apply(1000)
	if sf.Num != 1 || sf.Den != 1 {
		t.Errorf("At Bmax, expected 1/1, got %d/%d", sf.Num, sf.Den)
	}
}

// TestBudget_Apply_ScaleDown tests scaling down when exceeding max
func TestBudget_Apply_ScaleDown(t *testing.T) {
	b, _ := NewBudget(100, 1000)

	// sumR exceeds Bmax
	sf := b.Apply(2000)
	if sf.Num != 1000 || sf.Den != 2000 {
		t.Errorf("Scale down: expected 1000/2000, got %d/%d", sf.Num, sf.Den)
	}
	if !sf.IsScalingNeeded() {
		t.Error("IsScalingNeeded should be true")
	}

	// Test actual scaling
	R := uint64(200)
	scaled := sf.ScaleSubsidy(R)
	expected := (200 * 1000) / 2000 // = 100
	if scaled != expected {
		t.Errorf("Scaled subsidy should be %d, got %d", expected, scaled)
	}
}

// TestBudget_Apply_ScaleUp tests scaling up when below min
func TestBudget_Apply_ScaleUp(t *testing.T) {
	b, _ := NewBudget(1000, 5000)

	// sumR below Bmin
	sf := b.Apply(500)
	if sf.Num != 1000 || sf.Den != 500 {
		t.Errorf("Scale up: expected 1000/500, got %d/%d", sf.Num, sf.Den)
	}
	if !sf.IsScalingNeeded() {
		t.Error("IsScalingNeeded should be true")
	}

	// Test actual scaling
	R := uint64(100)
	scaled := sf.ScaleSubsidy(R)
	expected := (100 * 1000) / 500 // = 200
	if scaled != expected {
		t.Errorf("Scaled subsidy should be %d, got %d", expected, scaled)
	}
}

// TestBudget_Apply_NoLimits tests when no budget limits are set
func TestBudget_Apply_NoLimits(t *testing.T) {
	b, _ := NewBudget(0, 0)

	// Any sumR should result in no scaling
	sf := b.Apply(9999999)
	if sf.Num != 1 || sf.Den != 1 {
		t.Errorf("No limits: expected 1/1, got %d/%d", sf.Num, sf.Den)
	}

	sf = b.Apply(1)
	if sf.Num != 1 || sf.Den != 1 {
		t.Errorf("No limits: expected 1/1, got %d/%d", sf.Num, sf.Den)
	}
}

// TestBudget_Apply_ZeroSum tests when sumR = 0
func TestBudget_Apply_ZeroSum(t *testing.T) {
	b, _ := NewBudget(100, 1000)

	// sumR = 0 should not scale up
	sf := b.Apply(0)
	if sf.Num != 1 || sf.Den != 1 {
		t.Errorf("Zero sum: expected 1/1, got %d/%d", sf.Num, sf.Den)
	}
}

// TestScalingFactor_ScaleSubsidy tests subsidy scaling
func TestScalingFactor_ScaleSubsidy(t *testing.T) {
	sf := ScalingFactor{Num: 3, Den: 2}

	// R = 100, scaled = 100 * 3 / 2 = 150
	scaled := sf.ScaleSubsidy(100)
	if scaled != 150 {
		t.Errorf("Expected 150, got %d", scaled)
	}

	// R = 0
	scaled = sf.ScaleSubsidy(0)
	if scaled != 0 {
		t.Errorf("Expected 0, got %d", scaled)
	}

	// R = 1
	scaled = sf.ScaleSubsidy(1)
	expected := uint64(1 * 3 / 2) // = 1 (integer division)
	if scaled != expected {
		t.Errorf("Expected %d, got %d", expected, scaled)
	}
}

// TestScalingFactor_String tests string representation
func TestScalingFactor_String(t *testing.T) {
	sf := ScalingFactor{Num: 1, Den: 1}
	if sf.String() != "1 (no scaling)" {
		t.Errorf("Expected '1 (no scaling)', got '%s'", sf.String())
	}

	sf = ScalingFactor{Num: 2, Den: 3}
	if sf.String() != "2/3" {
		t.Errorf("Expected '2/3', got '%s'", sf.String())
	}
}

// TestAnnualToPerBlock tests annual to per-block conversion
func TestAnnualToPerBlock(t *testing.T) {
	annual := uint64(1000000)
	blocksPerYear := uint64(100000)

	perBlock := AnnualToPerBlock(annual, blocksPerYear)
	expected := uint64(10)
	if perBlock != expected {
		t.Errorf("Expected %d, got %d", expected, perBlock)
	}

	// Zero blocks
	perBlock = AnnualToPerBlock(annual, 0)
	if perBlock != 0 {
		t.Errorf("Zero blocks should return 0, got %d", perBlock)
	}
}

// TestComputeBlocksPerYear tests blocks per year calculation
func TestComputeBlocksPerYear(t *testing.T) {
	// 5 second blocks: 365.25 * 24 * 60 * 60 / 5 = 6,311,520
	blocks := ComputeBlocksPerYear(5000) // 5000 ms = 5 sec
	expected := uint64(365.25 * 24 * 60 * 60 * 1000 / 5000)
	if blocks != expected {
		t.Errorf("Expected ~%d blocks, got %d", expected, blocks)
	}

	// 10 second blocks
	blocks = ComputeBlocksPerYear(10000)
	expected = uint64(365.25 * 24 * 60 * 60 * 1000 / 10000)
	if blocks != expected {
		t.Errorf("Expected ~%d blocks, got %d", expected, blocks)
	}

	// Invalid interval
	blocks = ComputeBlocksPerYear(0)
	if blocks != 0 {
		t.Errorf("Zero interval should return 0, got %d", blocks)
	}
}

// TestBudgetConfig_ToBudget tests config conversion
func TestBudgetConfig_ToBudget(t *testing.T) {
	cfg := &BudgetConfig{
		GammaMinAnnual:  100000,
		GammaMaxAnnual:  1000000,
		BlockIntervalMs: 5000, // 5 sec blocks
	}

	b, err := cfg.ToBudget()
	if err != nil {
		t.Errorf("Valid config should not error: %v", err)
	}

	// Verify per-block values
	blocksPerYear := ComputeBlocksPerYear(5000)
	expectedMin := uint64(100000) / blocksPerYear
	expectedMax := uint64(1000000) / blocksPerYear

	if b.Bmin != expectedMin {
		t.Errorf("Bmin: expected %d, got %d", expectedMin, b.Bmin)
	}
	if b.Bmax != expectedMax {
		t.Errorf("Bmax: expected %d, got %d", expectedMax, b.Bmax)
	}

	// Invalid interval
	cfg.BlockIntervalMs = 0
	_, err = cfg.ToBudget()
	if err == nil {
		t.Error("Invalid interval should error")
	}
}

// TestApplyBudgetToBlock tests applying budget to multiple subsidies
func TestApplyBudgetToBlock(t *testing.T) {
	b, _ := NewBudget(100, 500)

	// Within bounds
	subsidies := []uint64{100, 150, 200}
	scaled, sf := ApplyBudgetToBlock(b, subsidies)

	if sf.IsScalingNeeded() {
		t.Error("Should not need scaling")
	}
	for i, s := range scaled {
		if s != subsidies[i] {
			t.Errorf("Index %d: expected %d, got %d", i, subsidies[i], s)
		}
	}

	// Exceeds max (sum = 900 > 500)
	subsidies = []uint64{300, 400, 200}
	scaled, sf = ApplyBudgetToBlock(b, subsidies)

	if !sf.IsScalingNeeded() {
		t.Error("Should need scaling")
	}

	// Sum of scaled should be close to Bmax
	var sumScaled uint64
	for _, s := range scaled {
		sumScaled += s
	}
	// Due to integer division, sum might be slightly less than Bmax
	if sumScaled > b.Bmax || sumScaled < b.Bmax-uint64(len(subsidies)) {
		t.Errorf("Scaled sum should be ~%d, got %d", b.Bmax, sumScaled)
	}
}

// Benchmark Apply
func BenchmarkBudget_Apply(b *testing.B) {
	budget, _ := NewBudget(100, 1000)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		budget.Apply(500)
	}
}

// Benchmark ScaleSubsidy
func BenchmarkScalingFactor_ScaleSubsidy(b *testing.B) {
	sf := ScalingFactor{Num: 3, Den: 2}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		sf.ScaleSubsidy(12345)
	}
}

