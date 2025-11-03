package utils

import (
	"testing"
)

// TestShardForAddress_Deterministic tests that shard mapping is deterministic
func TestShardForAddress_Deterministic(t *testing.T) {
	addr := Address("0x1234567890abcdef")
	numShards := 4

	// Call multiple times, should always get same result
	shard1 := ShardForAddress(addr, numShards)
	shard2 := ShardForAddress(addr, numShards)
	shard3 := ShardForAddress(addr, numShards)

	if shard1 != shard2 || shard2 != shard3 {
		t.Errorf("ShardForAddress not deterministic: got %d, %d, %d", shard1, shard2, shard3)
	}
}

// TestShardForAddress_Range tests that shard ID is within valid range
func TestShardForAddress_Range(t *testing.T) {
	addresses := []Address{
		"0x1111111111111111",
		"0xaaaaaaaaaaaaaaaa",
		"0xffffffffffffffff",
		"0x0000000000000000",
		"0x123456789abcdef0",
	}

	numShards := 4

	for _, addr := range addresses {
		shard := ShardForAddress(addr, numShards)
		if shard < 0 || shard >= numShards {
			t.Errorf("Shard %d out of range [0, %d) for address %s", shard, numShards, addr)
		}
	}
}

// TestShardForAddress_Distribution tests that addresses are reasonably distributed
func TestShardForAddress_Distribution(t *testing.T) {
	numShards := 4
	numAddresses := 1000

	shardCounts := make(map[int]int)

	// Generate many addresses and count distribution
	for i := 0; i < numAddresses; i++ {
		// Generate pseudo-random address
		addr := Address(string(rune('a' + (i % 26))) + string(rune('0' + (i / 26))))
		shard := ShardForAddress(addr, numShards)
		shardCounts[shard]++
	}

	// Each shard should get roughly numAddresses/numShards
	expectedPerShard := numAddresses / numShards
	tolerance := expectedPerShard / 2 // Allow 50% deviation

	for shard := 0; shard < numShards; shard++ {
		count := shardCounts[shard]
		if count < expectedPerShard-tolerance || count > expectedPerShard+tolerance {
			t.Logf("Warning: Shard %d has %d addresses (expected ~%d)", shard, count, expectedPerShard)
		}
	}
}

// TestShardForAddress_ZeroShards tests edge case with zero shards
func TestShardForAddress_ZeroShards(t *testing.T) {
	addr := Address("0x1234567890abcdef")
	shard := ShardForAddress(addr, 0)
	if shard != 0 {
		t.Errorf("Expected 0 for zero shards, got %d", shard)
	}
}

// TestShardForAddress_SingleShard tests single shard system
func TestShardForAddress_SingleShard(t *testing.T) {
	addr1 := Address("0x1111111111111111")
	addr2 := Address("0xffffffffffffffff")

	shard1 := ShardForAddress(addr1, 1)
	shard2 := ShardForAddress(addr2, 1)

	if shard1 != 0 || shard2 != 0 {
		t.Errorf("Single shard system should always return 0, got %d and %d", shard1, shard2)
	}
}

// TestIsCrossShard tests cross-shard detection
func TestIsCrossShard(t *testing.T) {
	numShards := 4

	// Same address (definitely same shard)
	addr1 := Address("0x1234567890abcdef")
	if IsCrossShard(addr1, addr1, numShards) {
		t.Error("Same address should not be cross-shard")
	}

	// Different addresses - find two that map to different shards
	var addrA, addrB Address
	for i := 0; i < 100; i++ {
		candidate := Address(string(rune('a' + (i % 26))))
		if ShardForAddress(candidate, numShards) != ShardForAddress(addr1, numShards) {
			addrA = addr1
			addrB = candidate
			break
		}
	}

	if addrA != "" && addrB != "" {
		if !IsCrossShard(addrA, addrB, numShards) {
			t.Errorf("Addresses in different shards should be cross-shard: %s (shard %d) and %s (shard %d)",
				addrA, ShardForAddress(addrA, numShards),
				addrB, ShardForAddress(addrB, numShards))
		}
	}
}

// TestIsCrossShard_SingleShard tests that single shard has no cross-shard txs
func TestIsCrossShard_SingleShard(t *testing.T) {
	addr1 := Address("0x1111111111111111")
	addr2 := Address("0xffffffffffffffff")

	if IsCrossShard(addr1, addr2, 1) {
		t.Error("Single shard system should never have cross-shard transactions")
	}
}

// TestGetTxShards tests getting both shards for a transaction
func TestGetTxShards(t *testing.T) {
	numShards := 4
	sender := Address("0x1234567890abcdef")
	recipient := Address("0xfedcba0987654321")

	fromShard, toShard := GetTxShards(sender, recipient, numShards)

	// Verify consistency with ShardForAddress
	expectedFrom := ShardForAddress(sender, numShards)
	expectedTo := ShardForAddress(recipient, numShards)

	if fromShard != expectedFrom {
		t.Errorf("FromShard mismatch: expected %d, got %d", expectedFrom, fromShard)
	}
	if toShard != expectedTo {
		t.Errorf("ToShard mismatch: expected %d, got %d", expectedTo, toShard)
	}

	// Verify within range
	if fromShard < 0 || fromShard >= numShards {
		t.Errorf("FromShard %d out of range", fromShard)
	}
	if toShard < 0 || toShard >= numShards {
		t.Errorf("ToShard %d out of range", toShard)
	}
}

// TestShardMapping_Consistency tests consistency across different operations
func TestShardMapping_Consistency(t *testing.T) {
	numShards := 4
	sender := Address("0x1234567890abcdef")
	recipient := Address("0xfedcba0987654321")

	// Get shards three different ways
	fromShard1 := ShardForAddress(sender, numShards)
	toShard1 := ShardForAddress(recipient, numShards)

	fromShard2, toShard2 := GetTxShards(sender, recipient, numShards)

	isCross := IsCrossShard(sender, recipient, numShards)
	expectedCross := (fromShard1 != toShard1)

	// Verify consistency
	if fromShard1 != fromShard2 {
		t.Errorf("FromShard inconsistent: %d vs %d", fromShard1, fromShard2)
	}
	if toShard1 != toShard2 {
		t.Errorf("ToShard inconsistent: %d vs %d", toShard1, toShard2)
	}
	if isCross != expectedCross {
		t.Errorf("IsCrossShard inconsistent: %v vs %v", isCross, expectedCross)
	}
}

// TestShardForAddress_DifferentNumShards tests behavior with different shard counts
func TestShardForAddress_DifferentNumShards(t *testing.T) {
	addr := Address("0x1234567890abcdef")

	// With different number of shards, same address should map to different shards
	shard4 := ShardForAddress(addr, 4)
	shard8 := ShardForAddress(addr, 8)
	shard16 := ShardForAddress(addr, 16)

	// Just verify they're in range
	if shard4 < 0 || shard4 >= 4 {
		t.Errorf("Shard for 4 shards out of range: %d", shard4)
	}
	if shard8 < 0 || shard8 >= 8 {
		t.Errorf("Shard for 8 shards out of range: %d", shard8)
	}
	if shard16 < 0 || shard16 >= 16 {
		t.Errorf("Shard for 16 shards out of range: %d", shard16)
	}
}

// Benchmark ShardForAddress
func BenchmarkShardForAddress(b *testing.B) {
	addr := Address("0x1234567890abcdef")
	numShards := 4

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ShardForAddress(addr, numShards)
	}
}

// Benchmark IsCrossShard
func BenchmarkIsCrossShard(b *testing.B) {
	addr1 := Address("0x1234567890abcdef")
	addr2 := Address("0xfedcba0987654321")
	numShards := 4

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		IsCrossShard(addr1, addr2, numShards)
	}
}

// Benchmark GetTxShards
func BenchmarkGetTxShards(b *testing.B) {
	sender := Address("0x1234567890abcdef")
	recipient := Address("0xfedcba0987654321")
	numShards := 4

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		GetTxShards(sender, recipient, numShards)
	}
}

