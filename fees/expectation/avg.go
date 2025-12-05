// Package expectation tracks per-shard average fees for ITX (intra-shard transactions)
package expectation

import (
	"math/big"
	"sort"
	"sync"
)

// Tracker maintains a sliding window of ITX fees per shard and computes rolling averages
type Tracker struct {
	WindowSize int                // Number of blocks in the sliding window
	mu         sync.RWMutex       // Protects concurrent access
	itxWindows map[int][]*big.Int // shard -> list of per-block average ITX fees
	blockCount map[int]int        // shard -> number of blocks processed
	avg        map[int]*big.Int   // shard -> current E(f_s)
}

// NewTracker creates a new fee expectation tracker with the specified window size
func NewTracker(windowSize int) *Tracker {
	if windowSize <= 0 {
		windowSize = 16 // default window size
	}
	return &Tracker{
		WindowSize: windowSize,
		itxWindows: make(map[int][]*big.Int),
		blockCount: make(map[int]int),
		avg:        make(map[int]*big.Int),
	}
}

// OnBlockFinalized is called when a block is finalized in a shard
// It updates the sliding window with ITX fees from that block and recomputes E(f_s)
// itxFeesInBlock contains only the proposer fees from intra-shard transactions
func (t *Tracker) OnBlockFinalized(shardID int, itxFeesInBlock []*big.Int) {
	t.mu.Lock()
	defer t.mu.Unlock()

	// Calculate average fee for this block (only from ITX)
	// Use capped mean: ignore fees above 99th percentile threshold
	// This prevents extreme outliers from distorting the average
	blockAvg := big.NewInt(0)
	if len(itxFeesInBlock) > 0 {
		// Set a reasonable cap: 0.0001 ETH = 1e14 wei (99th percentile from data)
		// Fees above this are likely errors or test transactions
		cap := big.NewInt(1e14) // 0.0001 ETH
		
		sum := big.NewInt(0)
		count := 0
		for _, fee := range itxFeesInBlock {
			if fee != nil && fee.Sign() > 0 {
				// Use the fee if below cap, otherwise use the cap value
				cappedFee := new(big.Int).Set(fee)
				if fee.Cmp(cap) > 0 {
					cappedFee = cap
				}
				sum.Add(sum, cappedFee)
				count++
			}
		}
		if count > 0 {
			blockAvg.Div(sum, big.NewInt(int64(count)))
		}
	}

	// Initialize shard data if not exists
	if _, exists := t.itxWindows[shardID]; !exists {
		t.itxWindows[shardID] = make([]*big.Int, 0, t.WindowSize)
		t.blockCount[shardID] = 0
		t.avg[shardID] = big.NewInt(0)
	}

	// Add block average to window (make a copy to avoid sharing)
	t.itxWindows[shardID] = append(t.itxWindows[shardID], new(big.Int).Set(blockAvg))
	t.blockCount[shardID]++

	// Keep only last WindowSize blocks
	if len(t.itxWindows[shardID]) > t.WindowSize {
		t.itxWindows[shardID] = t.itxWindows[shardID][len(t.itxWindows[shardID])-t.WindowSize:]
	}

	// Recompute rolling average E(f_s)
	t.recomputeAvg(shardID)
}

// trimExtremes removes the top and bottom percentiles from a fee list
// This implements a trimmed mean to reduce the impact of extreme values
// percentile: percentage to remove from each end (e.g., 25 means remove top 25% and bottom 25%)
func (t *Tracker) trimExtremes(fees []*big.Int, percentile int) []*big.Int {
	if len(fees) < 4 {
		// Too few samples (need at least 4 to meaningfully trim 25% from each end)
		// Return all fees without trimming
		return fees
	}

	// Copy and filter out nil/zero values
	validFees := make([]*big.Int, 0, len(fees))
	for _, fee := range fees {
		if fee != nil && fee.Sign() > 0 {
			validFees = append(validFees, new(big.Int).Set(fee))
		}
	}

	if len(validFees) < 4 {
		return validFees
	}

	// Sort fees
	sort.Slice(validFees, func(i, j int) bool {
		return validFees[i].Cmp(validFees[j]) < 0
	})

	// Calculate how many elements to remove from each end
	n := len(validFees)
	trimCount := (n * percentile) / 100

	// Ensure we don't trim everything
	if trimCount*2 >= n {
		trimCount = (n - 1) / 2
	}

	// Return the middle portion (50% if percentile=25)
	start := trimCount
	end := n - trimCount

	return validFees[start:end]
}

// recomputeAvg recalculates the average ITX fee for a shard
// Must be called with lock held
func (t *Tracker) recomputeAvg(shardID int) {
	window := t.itxWindows[shardID]
	if len(window) == 0 {
		t.avg[shardID] = big.NewInt(0)
		return
	}

	sum := big.NewInt(0)
	for _, blockAvg := range window {
		if blockAvg != nil {
			sum.Add(sum, blockAvg)
		}
	}
	// Integer division: avg = sum / len
	t.avg[shardID] = new(big.Int).Div(sum, big.NewInt(int64(len(window))))
}

// GetAvgITXFee returns the current rolling average ITX fee E(f_s) for a shard
// Returns a copy to prevent concurrent modification
func (t *Tracker) GetAvgITXFee(shardID int) *big.Int {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if avg, exists := t.avg[shardID]; exists {
		return new(big.Int).Set(avg)
	}
	return big.NewInt(0) // Return 0 if no data yet (bootstrap phase)
}

// GetAllAvgFees returns a snapshot of all shard averages (for metrics/debugging)
func (t *Tracker) GetAllAvgFees() map[int]*big.Int {
	t.mu.RLock()
	defer t.mu.RUnlock()

	snapshot := make(map[int]*big.Int)
	for shardID, avg := range t.avg {
		snapshot[shardID] = new(big.Int).Set(avg)
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

	t.itxWindows = make(map[int][]*big.Int)
	t.blockCount = make(map[int]int)
	t.avg = make(map[int]*big.Int)
}

// UpdateRemoteShardFee updates the average fee for a remote shard
// This is called when receiving fee sync messages from other shards in multi-process architecture
// Unlike OnBlockFinalized, this directly sets the average without maintaining a window
func (t *Tracker) UpdateRemoteShardFee(shardID int, avgFee *big.Int) {
	t.mu.Lock()
	defer t.mu.Unlock()

	if avgFee == nil {
		avgFee = big.NewInt(0)
	}

	// Initialize shard data if not exists
	if _, exists := t.avg[shardID]; !exists {
		t.itxWindows[shardID] = make([]*big.Int, 0, t.WindowSize)
		t.blockCount[shardID] = 0
	}

	// Directly update the average (make a copy to avoid concurrent modification)
	t.avg[shardID] = new(big.Int).Set(avgFee)
}

// GetLastUpdateTime returns when a shard's fee info was last updated (for debugging)
// Returns zero time if shard has no data
func (t *Tracker) GetLastUpdateTime(shardID int) int {
	t.mu.RLock()
	defer t.mu.RUnlock()

	return t.blockCount[shardID]
}
