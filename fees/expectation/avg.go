// Package expectation tracks per-shard average fees for ITX (intra-shard transactions)
package expectation

import (
	"sync"
)

// Tracker maintains a sliding window of ITX fees per shard and computes rolling averages
type Tracker struct {
	WindowSize int                        // Number of blocks in the sliding window
	mu         sync.RWMutex              // Protects concurrent access
	itxWindows map[int][]uint64          // shard -> list of per-block average ITX fees
	blockCount map[int]int               // shard -> number of blocks processed
	avg        map[int]uint64            // shard -> current E(f_s)
}

// NewTracker creates a new fee expectation tracker with the specified window size
func NewTracker(windowSize int) *Tracker {
	if windowSize <= 0 {
		windowSize = 16 // default window size
	}
	return &Tracker{
		WindowSize: windowSize,
		itxWindows: make(map[int][]uint64),
		blockCount: make(map[int]int),
		avg:        make(map[int]uint64),
	}
}

// OnBlockFinalized is called when a block is finalized in a shard
// It updates the sliding window with ITX fees from that block and recomputes E(f_s)
// itxFeesInBlock contains only the proposer fees from intra-shard transactions
func (t *Tracker) OnBlockFinalized(shardID int, itxFeesInBlock []uint64) {
	t.mu.Lock()
	defer t.mu.Unlock()

	// Calculate average fee for this block (only from ITX)
	var blockAvg uint64
	if len(itxFeesInBlock) > 0 {
		var sum uint64
		for _, fee := range itxFeesInBlock {
			sum += fee
		}
		blockAvg = sum / uint64(len(itxFeesInBlock))
	}

	// Initialize shard data if not exists
	if _, exists := t.itxWindows[shardID]; !exists {
		t.itxWindows[shardID] = make([]uint64, 0, t.WindowSize)
		t.blockCount[shardID] = 0
		t.avg[shardID] = 0
	}

	// Add block average to window
	t.itxWindows[shardID] = append(t.itxWindows[shardID], blockAvg)
	t.blockCount[shardID]++

	// Keep only last WindowSize blocks
	if len(t.itxWindows[shardID]) > t.WindowSize {
		t.itxWindows[shardID] = t.itxWindows[shardID][len(t.itxWindows[shardID])-t.WindowSize:]
	}

	// Recompute rolling average E(f_s)
	t.recomputeAvg(shardID)
}

// recomputeAvg recalculates the average ITX fee for a shard
// Must be called with lock held
func (t *Tracker) recomputeAvg(shardID int) {
	window := t.itxWindows[shardID]
	if len(window) == 0 {
		t.avg[shardID] = 0
		return
	}

	var sum uint64
	for _, blockAvg := range window {
		sum += blockAvg
	}
	t.avg[shardID] = sum / uint64(len(window))
}

// GetAvgITXFee returns the current rolling average ITX fee E(f_s) for a shard
func (t *Tracker) GetAvgITXFee(shardID int) uint64 {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if avg, exists := t.avg[shardID]; exists {
		return avg
	}
	return 0 // Return 0 if no data yet (bootstrap phase)
}

// GetAllAvgFees returns a snapshot of all shard averages (for metrics/debugging)
func (t *Tracker) GetAllAvgFees() map[int]uint64 {
	t.mu.RLock()
	defer t.mu.RUnlock()

	snapshot := make(map[int]uint64)
	for shardID, avg := range t.avg {
		snapshot[shardID] = avg
	}
	return snapshot
}

// GetBlockCount returns the number of blocks processed for a shard
func (t *Tracker) GetBlockCount(shardID int) int {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if count, exists := t.blockCount[shardID]; exists {
		return count
	}
	return 0
}

// Reset clears all tracking data for a shard (useful for testing)
func (t *Tracker) Reset(shardID int) {
	t.mu.Lock()
	defer t.mu.Unlock()

	delete(t.itxWindows, shardID)
	delete(t.blockCount, shardID)
	delete(t.avg, shardID)
}

// ResetAll clears all tracking data for all shards
func (t *Tracker) ResetAll() {
	t.mu.Lock()
	defer t.mu.Unlock()

	t.itxWindows = make(map[int][]uint64)
	t.blockCount = make(map[int]int)
	t.avg = make(map[int]uint64)
}

