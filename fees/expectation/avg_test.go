package expectation

import (
	"testing"
)

// TestTracker_BasicOperation tests basic tracker operations
func TestTracker_BasicOperation(t *testing.T) {
	tracker := NewTracker(3) // Window size = 3
	shardID := 0

	// Initially, average should be 0
	avg := tracker.GetAvgITXFee(shardID)
	if avg != 0 {
		t.Errorf("Initial avg should be 0, got %d", avg)
	}

	// Add first block with fees [100, 200, 300]
	tracker.OnBlockFinalized(shardID, []uint64{100, 200, 300})
	avg = tracker.GetAvgITXFee(shardID)
	// Block average = (100+200+300)/3 = 200
	// Rolling average = 200 (only one block)
	if avg != 200 {
		t.Errorf("After first block, avg should be 200, got %d", avg)
	}

	// Add second block with fees [400, 500]
	tracker.OnBlockFinalized(shardID, []uint64{400, 500})
	// Block average = (400+500)/2 = 450
	// Rolling average = (200+450)/2 = 325
	avg = tracker.GetAvgITXFee(shardID)
	if avg != 325 {
		t.Errorf("After second block, avg should be 325, got %d", avg)
	}

	// Add third block with fees [600]
	tracker.OnBlockFinalized(shardID, []uint64{600})
	// Block average = 600
	// Rolling average = (200+450+600)/3 = 416
	avg = tracker.GetAvgITXFee(shardID)
	if avg != 416 {
		t.Errorf("After third block, avg should be 416, got %d", avg)
	}

	// Add fourth block with fees [900] (window size = 3, so oldest drops)
	tracker.OnBlockFinalized(shardID, []uint64{900})
	// Block average = 900
	// Rolling average = (450+600+900)/3 = 650 (first block 200 is dropped)
	avg = tracker.GetAvgITXFee(shardID)
	if avg != 650 {
		t.Errorf("After fourth block, avg should be 650, got %d", avg)
	}
}

// TestTracker_EmptyBlocks tests handling of empty blocks (no ITX)
func TestTracker_EmptyBlocks(t *testing.T) {
	tracker := NewTracker(3)
	shardID := 0

	// Add block with no ITX
	tracker.OnBlockFinalized(shardID, []uint64{})
	avg := tracker.GetAvgITXFee(shardID)
	// Empty block contributes 0 to average
	if avg != 0 {
		t.Errorf("Empty block should give avg=0, got %d", avg)
	}

	// Add block with fees
	tracker.OnBlockFinalized(shardID, []uint64{1000})
	avg = tracker.GetAvgITXFee(shardID)
	// Rolling average = (0+1000)/2 = 500
	if avg != 500 {
		t.Errorf("After non-empty block, avg should be 500, got %d", avg)
	}

	// Add another empty block
	tracker.OnBlockFinalized(shardID, []uint64{})
	// Rolling average = (0+1000+0)/3 = 333
	avg = tracker.GetAvgITXFee(shardID)
	if avg != 333 {
		t.Errorf("After another empty block, avg should be 333, got %d", avg)
	}
}

// TestTracker_MultiShard tests tracking multiple shards independently
func TestTracker_MultiShard(t *testing.T) {
	tracker := NewTracker(2)

	// Add block to shard 0
	tracker.OnBlockFinalized(0, []uint64{100, 200})
	// Block avg = 150

	// Add block to shard 1
	tracker.OnBlockFinalized(1, []uint64{500, 600})
	// Block avg = 550

	avg0 := tracker.GetAvgITXFee(0)
	avg1 := tracker.GetAvgITXFee(1)

	if avg0 != 150 {
		t.Errorf("Shard 0 avg should be 150, got %d", avg0)
	}
	if avg1 != 550 {
		t.Errorf("Shard 1 avg should be 550, got %d", avg1)
	}

	// Add second block to shard 0
	tracker.OnBlockFinalized(0, []uint64{300, 400})
	// Block avg = 350
	// Rolling avg = (150+350)/2 = 250

	avg0 = tracker.GetAvgITXFee(0)
	avg1 = tracker.GetAvgITXFee(1) // Should remain unchanged

	if avg0 != 250 {
		t.Errorf("Shard 0 avg should be 250, got %d", avg0)
	}
	if avg1 != 550 {
		t.Errorf("Shard 1 avg should still be 550, got %d", avg1)
	}
}

// TestTracker_WindowSize tests that window is properly maintained
func TestTracker_WindowSize(t *testing.T) {
	windowSize := 5
	tracker := NewTracker(windowSize)
	shardID := 0

	// Add more blocks than window size
	for i := 1; i <= 10; i++ {
		// Each block has average fee = i * 100
		tracker.OnBlockFinalized(shardID, []uint64{uint64(i * 100)})
	}

	// Window should contain last 5 blocks: [600, 700, 800, 900, 1000]
	// Average = (600+700+800+900+1000)/5 = 800
	avg := tracker.GetAvgITXFee(shardID)
	if avg != 800 {
		t.Errorf("After 10 blocks with window=5, avg should be 800, got %d", avg)
	}

	// Verify window size is respected
	blockCount := tracker.GetBlockCount(shardID)
	if blockCount != 10 {
		t.Errorf("Block count should be 10, got %d", blockCount)
	}
}

// TestTracker_ITXOnly tests that only ITX fees are tracked
func TestTracker_ITXOnly(t *testing.T) {
	tracker := NewTracker(3)
	shardID := 0

	// Simulate: block has 3 ITX with fees [100, 200, 300]
	// CTX fees should NOT be included in this call
	itxFees := []uint64{100, 200, 300}
	tracker.OnBlockFinalized(shardID, itxFees)

	avg := tracker.GetAvgITXFee(shardID)
	expected := uint64((100 + 200 + 300) / 3)
	if avg != expected {
		t.Errorf("ITX-only avg should be %d, got %d", expected, avg)
	}
}

// TestTracker_GetAllAvgFees tests snapshot retrieval
func TestTracker_GetAllAvgFees(t *testing.T) {
	tracker := NewTracker(2)

	tracker.OnBlockFinalized(0, []uint64{100})
	tracker.OnBlockFinalized(1, []uint64{200})
	tracker.OnBlockFinalized(2, []uint64{300})

	snapshot := tracker.GetAllAvgFees()

	if len(snapshot) != 3 {
		t.Errorf("Snapshot should have 3 shards, got %d", len(snapshot))
	}
	if snapshot[0] != 100 {
		t.Errorf("Shard 0 avg should be 100, got %d", snapshot[0])
	}
	if snapshot[1] != 200 {
		t.Errorf("Shard 1 avg should be 200, got %d", snapshot[1])
	}
	if snapshot[2] != 300 {
		t.Errorf("Shard 2 avg should be 300, got %d", snapshot[2])
	}
}

// TestTracker_Reset tests reset functionality
func TestTracker_Reset(t *testing.T) {
	tracker := NewTracker(3)
	shardID := 0

	tracker.OnBlockFinalized(shardID, []uint64{100, 200})
	avg := tracker.GetAvgITXFee(shardID)
	if avg == 0 {
		t.Error("Avg should not be 0 before reset")
	}

	tracker.Reset(shardID)
	avg = tracker.GetAvgITXFee(shardID)
	if avg != 0 {
		t.Errorf("After reset, avg should be 0, got %d", avg)
	}

	blockCount := tracker.GetBlockCount(shardID)
	if blockCount != 0 {
		t.Errorf("After reset, block count should be 0, got %d", blockCount)
	}
}

// TestTracker_ResetAll tests resetting all shards
func TestTracker_ResetAll(t *testing.T) {
	tracker := NewTracker(2)

	tracker.OnBlockFinalized(0, []uint64{100})
	tracker.OnBlockFinalized(1, []uint64{200})

	tracker.ResetAll()

	snapshot := tracker.GetAllAvgFees()
	if len(snapshot) != 0 {
		t.Errorf("After ResetAll, snapshot should be empty, got %d shards", len(snapshot))
	}

	avg0 := tracker.GetAvgITXFee(0)
	avg1 := tracker.GetAvgITXFee(1)

	if avg0 != 0 || avg1 != 0 {
		t.Errorf("After ResetAll, all avgs should be 0, got %d and %d", avg0, avg1)
	}
}

// TestTracker_DefaultWindowSize tests default window size
func TestTracker_DefaultWindowSize(t *testing.T) {
	tracker := NewTracker(0) // Invalid window size
	if tracker.WindowSize != 16 {
		t.Errorf("Default window size should be 16, got %d", tracker.WindowSize)
	}

	tracker = NewTracker(-5) // Negative window size
	if tracker.WindowSize != 16 {
		t.Errorf("Default window size should be 16, got %d", tracker.WindowSize)
	}
}

// TestTracker_ConcurrentAccess tests thread safety (basic check)
func TestTracker_ConcurrentAccess(t *testing.T) {
	tracker := NewTracker(10)

	// Launch multiple goroutines to update different shards
	done := make(chan bool)
	for shard := 0; shard < 5; shard++ {
		go func(s int) {
			for i := 0; i < 100; i++ {
				tracker.OnBlockFinalized(s, []uint64{uint64(i * 10)})
				_ = tracker.GetAvgITXFee(s)
			}
			done <- true
		}(shard)
	}

	// Wait for all goroutines to finish
	for i := 0; i < 5; i++ {
		<-done
	}

	// Just verify no crash occurred
	snapshot := tracker.GetAllAvgFees()
	if len(snapshot) != 5 {
		t.Errorf("Expected 5 shards, got %d", len(snapshot))
	}
}

// Benchmark OnBlockFinalized
func BenchmarkTracker_OnBlockFinalized(b *testing.B) {
	tracker := NewTracker(16)
	fees := []uint64{100, 200, 300, 400, 500}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tracker.OnBlockFinalized(0, fees)
	}
}

// Benchmark GetAvgITXFee
func BenchmarkTracker_GetAvgITXFee(b *testing.B) {
	tracker := NewTracker(16)
	tracker.OnBlockFinalized(0, []uint64{100, 200, 300})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tracker.GetAvgITXFee(0)
	}
}

