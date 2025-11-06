package ethcsv

import (
	"math/big"
	"testing"
)

// TestComputeProposerFee_Legacy tests legacy transaction fee calculation
func TestComputeProposerFee_Legacy(t *testing.T) {
	tests := []struct {
		name     string
		gasUsed  uint64
		gasPrice *big.Int
		want     *big.Int
	}{
		{
			name:     "standard legacy tx",
			gasUsed:  21000,
			gasPrice: big.NewInt(20_000_000_000), // 20 gwei
			want:     big.NewInt(420_000_000_000_000), // 420,000 gwei = 0.00042 ETH
		},
		{
			name:     "zero gas used",
			gasUsed:  0,
			gasPrice: big.NewInt(20_000_000_000),
			want:     big.NewInt(0),
		},
		{
			name:     "nil gas price",
			gasUsed:  21000,
			gasPrice: nil,
			want:     big.NewInt(0),
		},
		{
			name:     "high gas price",
			gasUsed:  100000,
			gasPrice: big.NewInt(500_000_000_000), // 500 gwei
			want:     big.NewInt(50_000_000_000_000_000), // 0.05 ETH
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			row := TxRow{
				EIP2718Type: 0, // legacy
				GasUsed:     tt.gasUsed,
				GasPrice:    tt.gasPrice,
			}
			got := ComputeProposerFee(row)
			if got.Cmp(tt.want) != 0 {
				t.Errorf("ComputeProposerFee() = %v, want %v", got, tt.want)
			}
		})
	}
}

// TestComputeProposerFee_EIP1559 tests EIP-1559 transaction fee calculation
func TestComputeProposerFee_EIP1559(t *testing.T) {
	gwei := func(x int64) *big.Int { return big.NewInt(x * 1_000_000_000) }
	
	tests := []struct {
		name        string
		gasUsed     uint64
		baseFee     *big.Int
		maxFee      *big.Int
		priorityTip *big.Int
		wantTip     *big.Int // tip per gas
		wantTotal   *big.Int // total proposer fee
	}{
		{
			name:        "normal tip case",
			gasUsed:     21000,
			baseFee:     gwei(30),
			maxFee:      gwei(100),
			priorityTip: gwei(2),
			wantTip:     gwei(2),
			wantTotal:   new(big.Int).Mul(gwei(2), big.NewInt(21000)),
		},
		{
			name:        "maxFee limits effective price",
			gasUsed:     21000,
			baseFee:     gwei(30),
			maxFee:      gwei(31), // maxFee < baseFee + priorityTip
			priorityTip: gwei(2),
			wantTip:     gwei(1), // effective = 31, tip = 31 - 30 = 1
			wantTotal:   new(big.Int).Mul(gwei(1), big.NewInt(21000)),
		},
		{
			name:        "maxFee below baseFee",
			gasUsed:     21000,
			baseFee:     gwei(30),
			maxFee:      gwei(29), // maxFee < baseFee
			priorityTip: gwei(2),
			wantTip:     gwei(0), // tip cannot be negative
			wantTotal:   big.NewInt(0),
		},
		{
			name:        "zero priority tip",
			gasUsed:     21000,
			baseFee:     gwei(30),
			maxFee:      gwei(100),
			priorityTip: gwei(0),
			wantTip:     gwei(0),
			wantTotal:   big.NewInt(0),
		},
		{
			name:        "exact match",
			gasUsed:     21000,
			baseFee:     gwei(30),
			maxFee:      gwei(35),
			priorityTip: gwei(5),
			wantTip:     gwei(5),
			wantTotal:   new(big.Int).Mul(gwei(5), big.NewInt(21000)),
		},
		{
			name:        "nil fields",
			gasUsed:     21000,
			baseFee:     nil,
			maxFee:      gwei(100),
			priorityTip: gwei(2),
			wantTotal:   big.NewInt(0),
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			row := TxRow{
				EIP2718Type:          2, // EIP-1559
				GasUsed:              tt.gasUsed,
				BaseFeePerGas:        tt.baseFee,
				MaxFeePerGas:         tt.maxFee,
				MaxPriorityFeePerGas: tt.priorityTip,
			}
			got := ComputeProposerFee(row)
			if got.Cmp(tt.wantTotal) != 0 {
				t.Errorf("ComputeProposerFee() = %v, want %v", got, tt.wantTotal)
			}
		})
	}
}

// TestComputeProposerFee_FailedTx verifies that failed transactions still pay fees
func TestComputeProposerFee_FailedTx(t *testing.T) {
	row := TxRow{
		EIP2718Type: 0,
		GasUsed:     21000,
		GasPrice:    big.NewInt(20_000_000_000), // 20 gwei
		IsError:     true, // Transaction failed
	}
	
	got := ComputeProposerFee(row)
	want := big.NewInt(420_000_000_000_000) // Should still pay fee
	
	if got.Cmp(want) != 0 {
		t.Errorf("Failed tx should still pay fee: got %v, want %v", got, want)
	}
}

// TestComputeProposerFee_BlobTx tests EIP-4844 blob transaction fee calculation
func TestComputeProposerFee_BlobTx(t *testing.T) {
	// Blob transactions (type 3) still have regular execution gas fees (EIP-1559 style)
	row := TxRow{
		EIP2718Type:          3,  // EIP-4844 blob transaction
		GasUsed:              21000,
		BaseFeePerGas:        big.NewInt(30_000_000_000),  // 30 gwei
		MaxFeePerGas:         big.NewInt(100_000_000_000), // 100 gwei
		MaxPriorityFeePerGas: big.NewInt(2_000_000_000),   // 2 gwei tip
		// Blob gas fields (not used for execution gas tip calculation)
		BlobGasUsed:       131072,                        // 128 KB blob
		BlobBaseFeePerGas: big.NewInt(1_000_000_000),     // 1 gwei (burned)
	}
	
	got := ComputeProposerFee(row)
	// Should compute execution gas tip: 21000 * 2 gwei = 42,000 gwei
	// Blob fees not included (no maxFeePerBlobGas field available)
	want := big.NewInt(42_000_000_000_000)
	
	if got.Cmp(want) != 0 {
		t.Errorf("Blob tx execution gas fee: got %v, want %v", got, want)
	}
	
	t.Logf("Blob tx: execution gas tip = %v wei (blob fees not included)", got)
}

// TestMapShard tests deterministic shard mapping
func TestMapShard(t *testing.T) {
	addr1 := "0x1234567890abcdef1234567890abcdef12345678"
	addr2 := "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
	
	shards := 4
	
	// Test determinism
	shard1a := MapShard(addr1, shards)
	shard1b := MapShard(addr1, shards)
	if shard1a != shard1b {
		t.Errorf("MapShard not deterministic: %d != %d", shard1a, shard1b)
	}
	
	// Test range
	if shard1a < 0 || shard1a >= shards {
		t.Errorf("MapShard out of range: %d not in [0, %d)", shard1a, shards)
	}
	
	// Test that different addresses likely map to different shards
	// (not guaranteed, but with SHA-256 should be extremely likely)
	shard2 := MapShard(addr2, shards)
	if shard2 < 0 || shard2 >= shards {
		t.Errorf("MapShard out of range: %d not in [0, %d)", shard2, shards)
	}
	
	// Test with zero shards
	shard0 := MapShard(addr1, 0)
	if shard0 != 0 {
		t.Errorf("MapShard with 0 shards should return 0, got %d", shard0)
	}
	
	// Test with single shard
	shard1 := MapShard(addr1, 1)
	if shard1 != 0 {
		t.Errorf("MapShard with 1 shard should return 0, got %d", shard1)
	}
}

// TestIsCrossShard tests cross-shard detection
func TestIsCrossShard(t *testing.T) {
	addr1 := "0x1234567890abcdef1234567890abcdef12345678"
	addr2 := "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
	
	// Test with multiple shards
	isCross := IsCrossShard(addr1, addr2, 4)
	shard1 := MapShard(addr1, 4)
	shard2 := MapShard(addr2, 4)
	expectedCross := (shard1 != shard2)
	
	if isCross != expectedCross {
		t.Errorf("IsCrossShard inconsistent with MapShard: got %v, want %v", isCross, expectedCross)
	}
	
	// Test with single shard (no cross-shard possible)
	if IsCrossShard(addr1, addr2, 1) {
		t.Errorf("IsCrossShard should be false with 1 shard")
	}
	
	// Test same address (never cross-shard)
	if IsCrossShard(addr1, addr1, 4) {
		t.Errorf("IsCrossShard should be false for same address")
	}
}

// TestToAddress tests address extraction
func TestToAddress(t *testing.T) {
	tests := []struct {
		name     string
		to       string
		toCreate string
		want     string
	}{
		{
			name:     "regular transaction",
			to:       "0xabcd1234",
			toCreate: "",
			want:     "0xabcd1234",
		},
		{
			name:     "contract creation",
			to:       "",
			toCreate: "0xcontract1234",
			want:     "0xcontract1234",
		},
		{
			name:     "prefer to over toCreate",
			to:       "0xabcd1234",
			toCreate: "0xcontract1234",
			want:     "0xabcd1234",
		},
		{
			name:     "both empty",
			to:       "",
			toCreate: "",
			want:     "",
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			row := TxRow{
				To:       tt.to,
				ToCreate: tt.toCreate,
			}
			got := ToAddress(row)
			if got != tt.want {
				t.Errorf("ToAddress() = %v, want %v", got, tt.want)
			}
		})
	}
}

// BenchmarkComputeProposerFee_Legacy benchmarks legacy fee calculation
func BenchmarkComputeProposerFee_Legacy(b *testing.B) {
	row := TxRow{
		EIP2718Type: 0,
		GasUsed:     21000,
		GasPrice:    big.NewInt(20_000_000_000),
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = ComputeProposerFee(row)
	}
}

// BenchmarkComputeProposerFee_EIP1559 benchmarks EIP-1559 fee calculation
func BenchmarkComputeProposerFee_EIP1559(b *testing.B) {
	row := TxRow{
		EIP2718Type:          2,
		GasUsed:              21000,
		BaseFeePerGas:        big.NewInt(30_000_000_000),
		MaxFeePerGas:         big.NewInt(100_000_000_000),
		MaxPriorityFeePerGas: big.NewInt(2_000_000_000),
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = ComputeProposerFee(row)
	}
}

// BenchmarkMapShard benchmarks shard mapping
func BenchmarkMapShard(b *testing.B) {
	addr := "0x1234567890abcdef1234567890abcdef12345678"
	shards := 4
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = MapShard(addr, shards)
	}
}

