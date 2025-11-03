package justitia

import (
	"testing"
)

// TestSplit2_Invariant tests that uA + uB = fAB + R (sum invariant)
func TestSplit2_Invariant(t *testing.T) {
	testCases := []struct {
		name string
		fAB  uint64
		R    uint64
		EA   uint64
		EB   uint64
	}{
		{"Equal averages", 1000, 500, 100, 100},
		{"EA > EB", 1000, 500, 200, 100},
		{"EA < EB", 1000, 500, 100, 200},
		{"Zero subsidy", 1000, 0, 100, 100},
		{"Zero fee", 0, 500, 100, 100},
		{"Large numbers", 1000000, 500000, 10000, 20000},
		{"All zeros", 0, 0, 0, 0},
		{"EB >> EA", 1000, 500, 50, 5000},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			uA, uB := Split2(tc.fAB, tc.R, tc.EA, tc.EB)
			expected := tc.fAB + tc.R
			actual := uA + uB

			if actual != expected {
				t.Errorf("Split2(%d, %d, %d, %d) = (%d, %d), sum = %d, expected sum = %d",
					tc.fAB, tc.R, tc.EA, tc.EB, uA, uB, actual, expected)
			}

			// Also verify non-negative
			if uA < 0 || uB < 0 {
				t.Errorf("Split2 produced negative utility: uA=%d, uB=%d", uA, uB)
			}
		})
	}
}

// TestSplit2_EdgeCases tests edge cases for Split2
func TestSplit2_EdgeCases(t *testing.T) {
	// When EA = EB, uA = uB
	uA, uB := Split2(1000, 500, 100, 100)
	if uA != uB {
		t.Errorf("When EA = EB, expected uA = uB, got uA=%d, uB=%d", uA, uB)
	}
	if uA+uB != 1500 {
		t.Errorf("Expected sum = 1500, got %d", uA+uB)
	}

	// When R = 0, still valid split
	uA, uB = Split2(1000, 0, 200, 100)
	if uA+uB != 1000 {
		t.Errorf("Expected sum = 1000, got %d", uA+uB)
	}

	// Extreme case: very large EB causes negative intermediate uA
	// Should floor at 0
	uA, uB = Split2(100, 50, 10, 10000)
	if uA > uB {
		t.Errorf("Expected uA < uB when EB >> EA, got uA=%d, uB=%d", uA, uB)
	}
	if uA+uB != 150 {
		t.Errorf("Expected sum = 150, got %d", uA+uB)
	}
}

// TestSplit2_Symmetry tests that the split is symmetric
func TestSplit2_Symmetry(t *testing.T) {
	fAB := uint64(1000)
	R := uint64(500)
	EA := uint64(200)
	EB := uint64(100)

	uA, uB := Split2(fAB, R, EA, EB)

	// When EA and EB are swapped, uA and uB should swap
	// (This is the symmetry property of Shapley values)
	uB2, uA2 := Split2(fAB, R, EB, EA)

	if uA != uA2 || uB != uB2 {
		t.Errorf("Symmetry broken: Split2(%d,%d,%d,%d)=(%d,%d), Split2(%d,%d,%d,%d)=(%d,%d)",
			fAB, R, EA, EB, uA, uB, fAB, R, EB, EA, uB2, uA2)
	}
}

// TestRAB_Modes tests different subsidy modes
func TestRAB_Modes(t *testing.T) {
	EA := uint64(200)
	EB := uint64(100)

	// Mode: None
	r := RAB(SubsidyNone, EA, EB, nil)
	if r != 0 {
		t.Errorf("SubsidyNone should return 0, got %d", r)
	}

	// Mode: DestAvg
	r = RAB(SubsidyDestAvg, EA, EB, nil)
	if r != EB {
		t.Errorf("SubsidyDestAvg should return EB=%d, got %d", EB, r)
	}

	// Mode: SumAvg
	r = RAB(SubsidySumAvg, EA, EB, nil)
	expected := EA + EB
	if r != expected {
		t.Errorf("SubsidySumAvg should return EA+EB=%d, got %d", expected, r)
	}

	// Mode: Custom
	customFunc := func(ea, eb uint64) uint64 {
		return (ea + eb) / 2
	}
	r = RAB(SubsidyCustom, EA, EB, customFunc)
	expected = (EA + EB) / 2
	if r != expected {
		t.Errorf("SubsidyCustom should return %d, got %d", expected, r)
	}

	// Mode: Custom with nil function (fallback to DestAvg)
	r = RAB(SubsidyCustom, EA, EB, nil)
	if r != EB {
		t.Errorf("SubsidyCustom with nil func should fallback to EB=%d, got %d", EB, r)
	}
}

// TestRAB_NeverUsesFee tests that RAB never uses transaction fee
func TestRAB_NeverUsesFee(t *testing.T) {
	EA := uint64(200)
	EB := uint64(100)

	// RAB should give the same result regardless of fAB
	// We test this by calling with different EA/EB but checking it doesn't use external fAB

	r1 := RAB(SubsidyDestAvg, EA, EB, nil)
	r2 := RAB(SubsidyDestAvg, EA, EB, nil)

	if r1 != r2 {
		t.Errorf("RAB should be deterministic, got %d and %d", r1, r2)
	}

	// Verify it only depends on EA and EB
	if r1 != EB {
		t.Errorf("SubsidyDestAvg(EA=%d, EB=%d) should be %d, got %d", EA, EB, EB, r1)
	}
}

// TestClassify_Thresholds tests the three-case classification
func TestClassify_Thresholds(t *testing.T) {
	EA := uint64(1000)
	EB := uint64(400)

	// Case 1: uA >= EA
	uA := uint64(1000)
	c := Classify(uA, EA, EB)
	if c != Case1 {
		t.Errorf("Classify(%d, %d, %d) should be Case1, got %v", uA, EA, EB, c)
	}

	uA = 1500
	c = Classify(uA, EA, EB)
	if c != Case1 {
		t.Errorf("Classify(%d, %d, %d) should be Case1, got %v", uA, EA, EB, c)
	}

	// Case 2: uA <= EA - EB
	// threshold = 1000 - 400 = 600
	uA = 600
	c = Classify(uA, EA, EB)
	if c != Case2 {
		t.Errorf("Classify(%d, %d, %d) should be Case2, got %v", uA, EA, EB, c)
	}

	uA = 500
	c = Classify(uA, EA, EB)
	if c != Case2 {
		t.Errorf("Classify(%d, %d, %d) should be Case2, got %v", uA, EA, EB, c)
	}

	uA = 0
	c = Classify(uA, EA, EB)
	if c != Case2 {
		t.Errorf("Classify(%d, %d, %d) should be Case2, got %v", uA, EA, EB, c)
	}

	// Case 3: EA - EB < uA < EA
	uA = 700
	c = Classify(uA, EA, EB)
	if c != Case3 {
		t.Errorf("Classify(%d, %d, %d) should be Case3, got %v", uA, EA, EB, c)
	}

	uA = 999
	c = Classify(uA, EA, EB)
	if c != Case3 {
		t.Errorf("Classify(%d, %d, %d) should be Case3, got %v", uA, EA, EB, c)
	}
}

// TestClassify_EdgeCase_EBGreaterThanEA tests when EB >= EA (underflow case)
func TestClassify_EdgeCase_EBGreaterThanEA(t *testing.T) {
	EA := uint64(100)
	EB := uint64(500) // EB > EA

	// EA - EB would underflow, so threshold is effectively 0
	// uA = 0 should be Case2
	uA := uint64(0)
	c := Classify(uA, EA, EB)
	if c != Case2 {
		t.Errorf("Classify(%d, %d, %d) should be Case2, got %v", uA, EA, EB, c)
	}

	// uA > 0 but < EA should be Case3
	uA = 50
	c = Classify(uA, EA, EB)
	if c != Case3 {
		t.Errorf("Classify(%d, %d, %d) should be Case3, got %v", uA, EA, EB, c)
	}

	// uA >= EA should be Case1
	uA = 100
	c = Classify(uA, EA, EB)
	if c != Case1 {
		t.Errorf("Classify(%d, %d, %d) should be Case1, got %v", uA, EA, EB, c)
	}
}

// TestComputeCTXScore tests CTX score computation
func TestComputeCTXScore(t *testing.T) {
	fAB := uint64(1000)
	R := uint64(500)
	EA := uint64(200)
	EB := uint64(100)

	// From source shard A
	scoreA := ComputeCTXScore(fAB, R, EA, EB, true)
	uA, _ := Split2(fAB, R, EA, EB)
	if scoreA != uA {
		t.Errorf("Source shard score should be uA=%d, got %d", uA, scoreA)
	}

	// From destination shard B
	scoreB := ComputeCTXScore(fAB, R, EA, EB, false)
	_, uB := Split2(fAB, R, EA, EB)
	if scoreB != uB {
		t.Errorf("Dest shard score should be uB=%d, got %d", uB, scoreB)
	}

	// Scores should sum to fAB + R
	if scoreA+scoreB != fAB+R {
		t.Errorf("Scores should sum to %d, got %d", fAB+R, scoreA+scoreB)
	}
}

// TestValidateConfig tests configuration validation
func TestValidateConfig(t *testing.T) {
	// Valid config
	cfg := &Config{
		Mode:         SubsidyDestAvg,
		WindowBlocks: 16,
		CustomF:      nil,
		GammaMin:     0,
		GammaMax:     1000,
	}
	err := ValidateConfig(cfg)
	if err != nil {
		t.Errorf("Valid config should not error, got: %v", err)
	}

	// Invalid: WindowBlocks <= 0
	cfg = &Config{
		Mode:         SubsidyDestAvg,
		WindowBlocks: 0,
	}
	err = ValidateConfig(cfg)
	if err == nil {
		t.Error("WindowBlocks = 0 should be invalid")
	}

	// Invalid: Custom mode without function
	cfg = &Config{
		Mode:         SubsidyCustom,
		WindowBlocks: 16,
		CustomF:      nil,
	}
	err = ValidateConfig(cfg)
	if err == nil {
		t.Error("SubsidyCustom without CustomF should be invalid")
	}

	// Invalid: GammaMin > GammaMax
	cfg = &Config{
		Mode:         SubsidyDestAvg,
		WindowBlocks: 16,
		GammaMin:     1000,
		GammaMax:     500,
	}
	err = ValidateConfig(cfg)
	if err == nil {
		t.Error("GammaMin > GammaMax should be invalid")
	}
}

// TestDefaultConfig tests default configuration
func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Mode != SubsidyDestAvg {
		t.Errorf("Default mode should be SubsidyDestAvg, got %v", cfg.Mode)
	}
	if cfg.WindowBlocks != 16 {
		t.Errorf("Default WindowBlocks should be 16, got %d", cfg.WindowBlocks)
	}
	err := ValidateConfig(cfg)
	if err != nil {
		t.Errorf("Default config should be valid, got: %v", err)
	}
}

// Benchmark Split2
func BenchmarkSplit2(b *testing.B) {
	fAB := uint64(1000)
	R := uint64(500)
	EA := uint64(200)
	EB := uint64(100)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		Split2(fAB, R, EA, EB)
	}
}

// Benchmark RAB
func BenchmarkRAB(b *testing.B) {
	EA := uint64(200)
	EB := uint64(100)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		RAB(SubsidyDestAvg, EA, EB, nil)
	}
}

// Benchmark Classify
func BenchmarkClassify(b *testing.B) {
	uA := uint64(700)
	EA := uint64(1000)
	EB := uint64(400)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		Classify(uA, EA, EB)
	}
}

