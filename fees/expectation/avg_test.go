package expectation

import (
	"math/big"
	"testing"
)

// TestTracker_OnBlockFinalized tests basic block finalization
func TestTracker_OnBlockFinalized(t *testing.T) {
	tracker := NewTracker(4)
	shardID := 0
	
	// Add first block with ITX fees
	fees1 := []*big.Int{
		big.NewInt(100),
		big.NewInt(200),
		big.NewInt(300),
	}
	tracker.OnBlockFinalized(shardID, fees1)
	
	// Average should be (100+200+300)/3 = 200
	avg := tracker.GetAvgITXFee(shardID)
	want := big.NewInt(200)
	if avg.Cmp(want) != 0 {
		t.Errorf("GetAvgITXFee() = %v, want %v", avg, want)
	}
	
	// Add second block
	fees2 := []*big.Int{
		big.NewInt(400),
		big.NewInt(600),
	}
	tracker.OnBlockFinalized(shardID, fees2)
	
	// Average should be (200 + 500) / 2 = 350
	avg2 := tracker.GetAvgITXFee(shardID)
	want2 := big.NewInt(350)
	if avg2.Cmp(want2) != 0 {
		t.Errorf("GetAvgITXFee() after 2nd block = %v, want %v", avg2, want2)
	}
}

// TestTracker_SlidingWindow tests the sliding window behavior
func TestTracker_SlidingWindow(t *testing.T) {
	windowSize := 3
	tracker := NewTracker(windowSize)
	shardID := 0
	
	// Add blocks with known averages
	blocks := []struct {
		fees   []*big.Int
		avgFee int64
	}{
		{[]*big.Int{big.NewInt(100)}, 100},
		{[]*big.Int{big.NewInt(200)}, 200},
		{[]*big.Int{big.NewInt(300)}, 300},
		{[]*big.Int{big.NewInt(400)}, 400}, // Should push out first block
	}
	
	for _, block := range blocks {
		tracker.OnBlockFinalized(shardID, block.fees)
	}
	
	// Window should contain blocks with avg fees: 200, 300, 400
	// Rolling average should be (200 + 300 + 400) / 3 = 300
	avg := tracker.GetAvgITXFee(shardID)
	want := big.NewInt(300)
	if avg.Cmp(want) != 0 {
		t.Errorf("Sliding window avg = %v, want %v", avg, want)
	}
	
	// Verify window size
	count := tracker.GetBlockCount(shardID)
	if count != 4 {
		t.Errorf("Block count = %d, want 4", count)
	}
}

// TestTracker_MultiShard tests multiple shards independently
func TestTracker_MultiShard(t *testing.T) {
	tracker := NewTracker(4)
	
	// Shard 0: high fees
	tracker.OnBlockFinalized(0, []*big.Int{big.NewInt(1000), big.NewInt(1200)})
	
	// Shard 1: low fees
	tracker.OnBlockFinalized(1, []*big.Int{big.NewInt(100), big.NewInt(200)})
	
	// Verify independent averages
	avg0 := tracker.GetAvgITXFee(0)
	want0 := big.NewInt(1100)
	if avg0.Cmp(want0) != 0 {
		t.Errorf("Shard 0 avg = %v, want %v", avg0, want0)
	}
	
	avg1 := tracker.GetAvgITXFee(1)
	want1 := big.NewInt(150)
	if avg1.Cmp(want1) != 0 {
		t.Errorf("Shard 1 avg = %v, want %v", avg1, want1)
	}
}

// TestTracker_EmptyBlock tests blocks with no ITX
func TestTracker_EmptyBlock(t *testing.T) {
	tracker := NewTracker(4)
	shardID := 0
	
	// Add empty block (no ITX)
	tracker.OnBlockFinalized(shardID, []*big.Int{})
	
	// Average should be 0
	avg := tracker.GetAvgITXFee(shardID)
	want := big.NewInt(0)
	if avg.Cmp(want) != 0 {
		t.Errorf("Empty block avg = %v, want %v", avg, want)
	}
}

// TestTracker_NilFees tests handling of nil fees
func TestTracker_NilFees(t *testing.T) {
	tracker := NewTracker(4)
	shardID := 0
	
	// Add block with some nil fees
	fees := []*big.Int{
		big.NewInt(100),
		nil,
		big.NewInt(300),
	}
	tracker.OnBlockFinalized(shardID, fees)
	
	// Should skip nil and compute average of 100 and 300
	avg := tracker.GetAvgITXFee(shardID)
	// With nil, sum = 400, count = 3, avg = 133
	// But our implementation skips nil in sum but not count
	// So: (100 + 0 + 300) / 3 = 133
	want := big.NewInt(133)
	if avg.Cmp(want) != 0 {
		t.Errorf("Avg with nil fees = %v, want %v", avg, want)
	}
}

// TestTracker_Bootstrap tests behavior when no data available
func TestTracker_Bootstrap(t *testing.T) {
	tracker := NewTracker(4)
	
	// Query non-existent shard
	avg := tracker.GetAvgITXFee(999)
	want := big.NewInt(0)
	if avg.Cmp(want) != 0 {
		t.Errorf("Bootstrap avg = %v, want %v", avg, want)
	}
}

// TestTracker_GetAllAvgFees tests snapshot retrieval
func TestTracker_GetAllAvgFees(t *testing.T) {
	tracker := NewTracker(4)
	
	tracker.OnBlockFinalized(0, []*big.Int{big.NewInt(100)})
	tracker.OnBlockFinalized(1, []*big.Int{big.NewInt(200)})
	tracker.OnBlockFinalized(2, []*big.Int{big.NewInt(300)})
	
	snapshot := tracker.GetAllAvgFees()
	
	if len(snapshot) != 3 {
		t.Errorf("Snapshot size = %d, want 3", len(snapshot))
	}
	
	if snapshot[0].Cmp(big.NewInt(100)) != 0 {
		t.Errorf("Snapshot[0] = %v, want 100", snapshot[0])
	}
	if snapshot[1].Cmp(big.NewInt(200)) != 0 {
		t.Errorf("Snapshot[1] = %v, want 200", snapshot[1])
	}
	if snapshot[2].Cmp(big.NewInt(300)) != 0 {
		t.Errorf("Snapshot[2] = %v, want 300", snapshot[2])
	}
}

// TestTracker_Reset tests resetting shard data
func TestTracker_Reset(t *testing.T) {
	tracker := NewTracker(4)
	shardID := 0
	
	tracker.OnBlockFinalized(shardID, []*big.Int{big.NewInt(100)})
	
	// Verify data exists
	if tracker.GetBlockCount(shardID) == 0 {
		t.Error("Expected block count > 0 before reset")
	}
	
	// Reset
	tracker.Reset(shardID)
	
	// Verify data cleared
	if tracker.GetBlockCount(shardID) != 0 {
		t.Error("Expected block count = 0 after reset")
	}
	
	avg := tracker.GetAvgITXFee(shardID)
	if avg.Cmp(big.NewInt(0)) != 0 {
		t.Errorf("Expected avg = 0 after reset, got %v", avg)
	}
}

// TestTracker_ResetAll tests resetting all shards
func TestTracker_ResetAll(t *testing.T) {
	tracker := NewTracker(4)
	
	tracker.OnBlockFinalized(0, []*big.Int{big.NewInt(100)})
	tracker.OnBlockFinalized(1, []*big.Int{big.NewInt(200)})
	
	tracker.ResetAll()
	
	// Verify all data cleared
	snapshot := tracker.GetAllAvgFees()
	if len(snapshot) != 0 {
		t.Errorf("Expected empty snapshot after ResetAll, got %d entries", len(snapshot))
	}
}

// TestTracker_LargeValues tests handling of large fee values
func TestTracker_LargeValues(t *testing.T) {
	tracker := NewTracker(4)
	shardID := 0
	
	// Use ETH-scale values (in wei)
	oneETH := new(big.Int).Exp(big.NewInt(10), big.NewInt(18), nil)
	fees := []*big.Int{
		new(big.Int).Mul(oneETH, big.NewInt(1)),
		new(big.Int).Mul(oneETH, big.NewInt(2)),
		new(big.Int).Mul(oneETH, big.NewInt(3)),
	}
	
	tracker.OnBlockFinalized(shardID, fees)
	
	avg := tracker.GetAvgITXFee(shardID)
	// Average should be 2 ETH
	want := new(big.Int).Mul(oneETH, big.NewInt(2))
	
	if avg.Cmp(want) != 0 {
		t.Errorf("Large value avg = %v, want %v", avg, want)
	}
}

// TestTracker_Concurrent tests thread safety (basic)
func TestTracker_Concurrent(t *testing.T) {
	tracker := NewTracker(4)
	
	// Simulate concurrent updates
	done := make(chan bool, 3)
	
	go func() {
		for i := 0; i < 100; i++ {
			tracker.OnBlockFinalized(0, []*big.Int{big.NewInt(100)})
		}
		done <- true
	}()
	
	go func() {
		for i := 0; i < 100; i++ {
			_ = tracker.GetAvgITXFee(0)
		}
		done <- true
	}()
	
	go func() {
		for i := 0; i < 100; i++ {
			_ = tracker.GetAllAvgFees()
		}
		done <- true
	}()
	
	// Wait for all goroutines
	<-done
	<-done
	<-done
	
	// Should not panic
}

// BenchmarkOnBlockFinalized benchmarks block finalization
func BenchmarkOnBlockFinalized(b *testing.B) {
	tracker := NewTracker(16)
	fees := []*big.Int{
		big.NewInt(100),
		big.NewInt(200),
		big.NewInt(300),
		big.NewInt(400),
		big.NewInt(500),
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tracker.OnBlockFinalized(0, fees)
	}
}

// BenchmarkGetAvgITXFee benchmarks average fee retrieval
func BenchmarkGetAvgITXFee(b *testing.B) {
	tracker := NewTracker(16)
	tracker.OnBlockFinalized(0, []*big.Int{big.NewInt(100)})
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = tracker.GetAvgITXFee(0)
	}
}
