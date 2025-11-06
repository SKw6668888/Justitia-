package justitia

import (
	"math/big"
	"testing"
)

// TestRAB_Modes tests all subsidy modes
func TestRAB_Modes(t *testing.T) {
	EA := big.NewInt(100)
	EB := big.NewInt(200)
	
	tests := []struct {
		name string
		mode SubsidyMode
		want *big.Int
	}{
		{
			name: "None mode",
			mode: SubsidyNone,
			want: big.NewInt(0),
		},
		{
			name: "DestAvg mode",
			mode: SubsidyDestAvg,
			want: big.NewInt(200), // EB
		},
		{
			name: "SumAvg mode",
			mode: SubsidySumAvg,
			want: big.NewInt(300), // EA + EB
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := RAB(tt.mode, EA, EB, nil)
			if got.Cmp(tt.want) != 0 {
				t.Errorf("RAB() = %v, want %v", got, tt.want)
			}
		})
	}
}

// TestRAB_CustomMode tests custom subsidy function
func TestRAB_CustomMode(t *testing.T) {
	EA := big.NewInt(100)
	EB := big.NewInt(200)
	
	// Custom function: R = max(EA, EB)
	customF := func(ea, eb *big.Int) *big.Int {
		if ea.Cmp(eb) > 0 {
			return new(big.Int).Set(ea)
		}
		return new(big.Int).Set(eb)
	}
	
	got := RAB(SubsidyCustom, EA, EB, customF)
	want := big.NewInt(200) // max(100, 200)
	
	if got.Cmp(want) != 0 {
		t.Errorf("RAB(Custom) = %v, want %v", got, want)
	}
	
	// Test fallback when no custom function
	got2 := RAB(SubsidyCustom, EA, EB, nil)
	want2 := EB // Should fallback to DestAvg
	if got2.Cmp(want2) != 0 {
		t.Errorf("RAB(Custom, nil func) = %v, want %v", got2, want2)
	}
}

// TestRAB_NilInputs tests handling of nil inputs
func TestRAB_NilInputs(t *testing.T) {
	tests := []struct {
		name string
		mode SubsidyMode
		EA   *big.Int
		EB   *big.Int
	}{
		{"DestAvg with nil EB", SubsidyDestAvg, big.NewInt(100), nil},
		{"SumAvg with nil EA", SubsidySumAvg, nil, big.NewInt(200)},
		{"SumAvg with both nil", SubsidySumAvg, nil, nil},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := RAB(tt.mode, tt.EA, tt.EB, nil)
			if got == nil {
				t.Errorf("RAB() returned nil, should return big.Int")
			}
		})
	}
}

// TestSplit2_Conservation tests the invariant uA + uB = fAB + R
func TestSplit2_Conservation(t *testing.T) {
	tests := []struct {
		name string
		fAB  *big.Int
		R    *big.Int
		EA   *big.Int
		EB   *big.Int
	}{
		{
			name: "balanced",
			fAB:  big.NewInt(100),
			R:    big.NewInt(50),
			EA:   big.NewInt(80),
			EB:   big.NewInt(70),
		},
		{
			name: "EA > EB",
			fAB:  big.NewInt(200),
			R:    big.NewInt(100),
			EA:   big.NewInt(150),
			EB:   big.NewInt(50),
		},
		{
			name: "EB > EA",
			fAB:  big.NewInt(300),
			R:    big.NewInt(150),
			EA:   big.NewInt(60),
			EB:   big.NewInt(140),
		},
		{
			name: "large values",
			fAB:  new(big.Int).Exp(big.NewInt(10), big.NewInt(18), nil), // 1 ETH in wei
			R:    new(big.Int).Exp(big.NewInt(10), big.NewInt(17), nil), // 0.1 ETH
			EA:   big.NewInt(1000000000000000000),
			EB:   big.NewInt(500000000000000000),
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			uA, uB := Split2(tt.fAB, tt.R, tt.EA, tt.EB)
			
			// Check conservation: uA + uB = fAB + R
			sum := new(big.Int).Add(uA, uB)
			total := new(big.Int).Add(tt.fAB, tt.R)
			
			if sum.Cmp(total) != 0 {
				t.Errorf("Conservation violated: uA(%v) + uB(%v) = %v, want %v", uA, uB, sum, total)
			}
			
			// Check non-negativity
			if uA.Sign() < 0 {
				t.Errorf("uA is negative: %v", uA)
			}
			if uB.Sign() < 0 {
				t.Errorf("uB is negative: %v", uB)
			}
		})
	}
}

// TestSplit2_Symmetry tests that swapping A and B swaps uA and uB
func TestSplit2_Symmetry(t *testing.T) {
	fAB := big.NewInt(100)
	R := big.NewInt(50)
	EA := big.NewInt(80)
	EB := big.NewInt(70)
	
	uA1, uB1 := Split2(fAB, R, EA, EB)
	uA2, uB2 := Split2(fAB, R, EB, EA) // Swap EA and EB
	
	// uA with (EA, EB) should equal uB with (EB, EA)
	if uA1.Cmp(uB2) != 0 {
		t.Errorf("Symmetry violated: uA(%v) != uB_swapped(%v)", uA1, uB2)
	}
	if uB1.Cmp(uA2) != 0 {
		t.Errorf("Symmetry violated: uB(%v) != uA_swapped(%v)", uB1, uA2)
	}
}

// TestSplit2_EdgeCases tests edge cases
func TestSplit2_EdgeCases(t *testing.T) {
	tests := []struct {
		name string
		fAB  *big.Int
		R    *big.Int
		EA   *big.Int
		EB   *big.Int
	}{
		{
			name: "all zero",
			fAB:  big.NewInt(0),
			R:    big.NewInt(0),
			EA:   big.NewInt(0),
			EB:   big.NewInt(0),
		},
		{
			name: "nil inputs",
			fAB:  nil,
			R:    nil,
			EA:   nil,
			EB:   nil,
		},
		{
			name: "very large EA-EB diff",
			fAB:  big.NewInt(100),
			R:    big.NewInt(50),
			EA:   big.NewInt(10000),
			EB:   big.NewInt(10),
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			uA, uB := Split2(tt.fAB, tt.R, tt.EA, tt.EB)
			
			// Should not panic
			if uA == nil || uB == nil {
				t.Errorf("Split2 returned nil")
			}
			
			// Should be non-negative
			if uA.Sign() < 0 || uB.Sign() < 0 {
				t.Errorf("Split2 returned negative values: uA=%v, uB=%v", uA, uB)
			}
		})
	}
}

// TestClassify_Case1 tests Case1 classification (uA >= EA)
func TestClassify_Case1(t *testing.T) {
	EA := big.NewInt(100)
	EB := big.NewInt(80)
	
	tests := []struct {
		name string
		uA   *big.Int
	}{
		{"uA equals EA", big.NewInt(100)},
		{"uA greater than EA", big.NewInt(150)},
		{"uA much greater", big.NewInt(1000)},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Classify(tt.uA, EA, EB)
			if got != Case1 {
				t.Errorf("Classify(%v, %v, %v) = %v, want Case1", tt.uA, EA, EB, got)
			}
		})
	}
}

// TestClassify_Case2 tests Case2 classification (uA <= EA - EB)
func TestClassify_Case2(t *testing.T) {
	EA := big.NewInt(100)
	EB := big.NewInt(80)
	threshold := big.NewInt(20) // EA - EB
	
	tests := []struct {
		name string
		uA   *big.Int
	}{
		{"uA at threshold", threshold},
		{"uA below threshold", big.NewInt(10)},
		{"uA is zero", big.NewInt(0)},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Classify(tt.uA, EA, EB)
			if got != Case2 {
				t.Errorf("Classify(%v, %v, %v) = %v, want Case2", tt.uA, EA, EB, got)
			}
		})
	}
}

// TestClassify_Case3 tests Case3 classification (EA - EB < uA < EA)
func TestClassify_Case3(t *testing.T) {
	EA := big.NewInt(100)
	EB := big.NewInt(80)
	
	tests := []struct {
		name string
		uA   *big.Int
	}{
		{"uA in middle", big.NewInt(50)},
		{"uA just above threshold", big.NewInt(21)},
		{"uA just below EA", big.NewInt(99)},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Classify(tt.uA, EA, EB)
			if got != Case3 {
				t.Errorf("Classify(%v, %v, %v) = %v, want Case3", tt.uA, EA, EB, got)
			}
		})
	}
}

// TestClassify_EBGreaterThanEA tests when EB >= EA
func TestClassify_EBGreaterThanEA(t *testing.T) {
	EA := big.NewInt(80)
	EB := big.NewInt(100) // EB > EA
	
	tests := []struct {
		name string
		uA   *big.Int
		want Case
	}{
		{"uA is zero", big.NewInt(0), Case2},
		{"uA is positive", big.NewInt(50), Case3},
		{"uA >= EA", big.NewInt(80), Case1},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Classify(tt.uA, EA, EB)
			if got != tt.want {
				t.Errorf("Classify(%v, %v, %v) = %v, want %v", tt.uA, EA, EB, got, tt.want)
			}
		})
	}
}

// TestComputeCTXScore tests CTX score computation
func TestComputeCTXScore(t *testing.T) {
	fAB := big.NewInt(100)
	R := big.NewInt(50)
	EA := big.NewInt(80)
	EB := big.NewInt(70)
	
	// Compute expected values
	expectedUA, expectedUB := Split2(fAB, R, EA, EB)
	
	// Test source shard perspective
	scoreA := ComputeCTXScore(fAB, R, EA, EB, true)
	if scoreA.Cmp(expectedUA) != 0 {
		t.Errorf("Source shard score = %v, want %v", scoreA, expectedUA)
	}
	
	// Test destination shard perspective
	scoreB := ComputeCTXScore(fAB, R, EA, EB, false)
	if scoreB.Cmp(expectedUB) != 0 {
		t.Errorf("Dest shard score = %v, want %v", scoreB, expectedUB)
	}
}

// TestValidateConfig tests configuration validation
func TestValidateConfig(t *testing.T) {
	tests := []struct {
		name    string
		cfg     *Config
		wantErr bool
	}{
		{
			name: "valid default config",
			cfg:  DefaultConfig(),
			wantErr: false,
		},
		{
			name: "invalid window size",
			cfg: &Config{
				Mode:         SubsidyDestAvg,
				WindowBlocks: 0,
			},
			wantErr: true,
		},
		{
			name: "custom mode without function",
			cfg: &Config{
				Mode:         SubsidyCustom,
				WindowBlocks: 16,
				CustomF:      nil,
			},
			wantErr: true,
		},
		{
			name: "GammaMin exceeds GammaMax",
			cfg: &Config{
				Mode:         SubsidyDestAvg,
				WindowBlocks: 16,
				GammaMin:     big.NewInt(1000),
				GammaMax:     big.NewInt(500),
			},
			wantErr: true,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateConfig(tt.cfg)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateConfig() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

// BenchmarkSplit2 benchmarks the Split2 function
func BenchmarkSplit2(b *testing.B) {
	fAB := big.NewInt(100)
	R := big.NewInt(50)
	EA := big.NewInt(80)
	EB := big.NewInt(70)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = Split2(fAB, R, EA, EB)
	}
}

// BenchmarkClassify benchmarks the Classify function
func BenchmarkClassify(b *testing.B) {
	uA := big.NewInt(50)
	EA := big.NewInt(100)
	EB := big.NewInt(80)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = Classify(uA, EA, EB)
	}
}
