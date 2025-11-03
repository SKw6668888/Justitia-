// Package pending manages pending cross-shard transaction rewards
package pending

import (
	"fmt"
	"sync"
)

// Pending represents a cross-shard transaction awaiting settlement
// Created when source shard A includes CTX
// Settled when destination shard B includes CTX'
type Pending struct {
	PairID        string // Unique identifier (typically TxHash)
	ShardA        int    // Source shard
	ShardB        int    // Destination shard
	FAB           uint64 // Transaction fee f_AB
	R             uint64 // Subsidy R_AB
	EA            uint64 // E(f_A) at the time of CTX inclusion
	EB            uint64 // E(f_B) at the time of CTX inclusion
	UtilityA      uint64 // uA (computed at creation)
	UtilityB      uint64 // uB (computed at creation)
	SourceBlockID string // Block ID where CTX was included in shard A
	CreatedAt     int64  // Timestamp of creation (for cleanup)
}

// Ledger maintains the set of pending cross-shard transactions
type Ledger struct {
	mu       sync.RWMutex
	pending  map[string]*Pending // PairID -> Pending entry
	settled  map[string]bool     // Track settled PairIDs to prevent double settlement
}

// NewLedger creates a new pending rewards ledger
func NewLedger() *Ledger {
	return &Ledger{
		pending: make(map[string]*Pending),
		settled: make(map[string]bool),
	}
}

// Add adds a new pending cross-shard transaction to the ledger
// Returns error if PairID already exists
func (l *Ledger) Add(p *Pending) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	// Check if already settled
	if l.settled[p.PairID] {
		return fmt.Errorf("transaction %s already settled", p.PairID)
	}

	// Check if already pending
	if _, exists := l.pending[p.PairID]; exists {
		return fmt.Errorf("transaction %s already pending", p.PairID)
	}

	l.pending[p.PairID] = p
	return nil
}

// Get retrieves a pending entry by PairID
func (l *Ledger) Get(pairID string) (*Pending, bool) {
	l.mu.RLock()
	defer l.mu.RUnlock()

	p, exists := l.pending[pairID]
	return p, exists
}

// Settle settles a cross-shard transaction when CTX' is included in destination shard
// Calls the credit function to distribute rewards to both proposers
// Returns error if PairID not found or already settled
func (l *Ledger) Settle(pairID string, destBlockID string, creditFunc func(shardID int, proposerID string, amount uint64)) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	// Check if already settled
	if l.settled[pairID] {
		return fmt.Errorf("transaction %s already settled", pairID)
	}

	// Get pending entry
	p, exists := l.pending[pairID]
	if !exists {
		return fmt.Errorf("transaction %s not found in pending ledger", pairID)
	}

	// Credit rewards to proposers
	// In a real system, we'd get actual proposer IDs from blocks
	// For now, we use shard ID as a placeholder
	sourceProposerID := fmt.Sprintf("proposer_shard_%d_block_%s", p.ShardA, p.SourceBlockID)
	destProposerID := fmt.Sprintf("proposer_shard_%d_block_%s", p.ShardB, destBlockID)

	// Credit uA to source shard proposer
	creditFunc(p.ShardA, sourceProposerID, p.UtilityA)

	// Credit uB to destination shard proposer
	creditFunc(p.ShardB, destProposerID, p.UtilityB)

	// Mark as settled and remove from pending
	l.settled[pairID] = true
	delete(l.pending, pairID)

	return nil
}

// IsPending checks if a transaction is still pending
func (l *Ledger) IsPending(pairID string) bool {
	l.mu.RLock()
	defer l.mu.RUnlock()

	_, exists := l.pending[pairID]
	return exists
}

// IsSettled checks if a transaction has been settled
func (l *Ledger) IsSettled(pairID string) bool {
	l.mu.RLock()
	defer l.mu.RUnlock()

	return l.settled[pairID]
}

// GetPendingCount returns the number of pending transactions
func (l *Ledger) GetPendingCount() int {
	l.mu.RLock()
	defer l.mu.RUnlock()

	return len(l.pending)
}

// GetSettledCount returns the number of settled transactions
func (l *Ledger) GetSettledCount() int {
	l.mu.RLock()
	defer l.mu.RUnlock()

	return len(l.settled)
}

// GetAllPending returns a snapshot of all pending transactions
func (l *Ledger) GetAllPending() []*Pending {
	l.mu.RLock()
	defer l.mu.RUnlock()

	result := make([]*Pending, 0, len(l.pending))
	for _, p := range l.pending {
		// Create a copy to avoid concurrent modification
		pCopy := *p
		result = append(result, &pCopy)
	}
	return result
}

// CleanupOld removes pending entries older than the specified timestamp
// Useful for cleaning up transactions that may have been lost
func (l *Ledger) CleanupOld(olderThan int64) int {
	l.mu.Lock()
	defer l.mu.Unlock()

	count := 0
	for pairID, p := range l.pending {
		if p.CreatedAt < olderThan {
			delete(l.pending, pairID)
			count++
		}
	}
	return count
}

// Reset clears all pending and settled records (for testing)
func (l *Ledger) Reset() {
	l.mu.Lock()
	defer l.mu.Unlock()

	l.pending = make(map[string]*Pending)
	l.settled = make(map[string]bool)
}

// Stats returns statistics about the ledger
type Stats struct {
	PendingCount int
	SettledCount int
	TotalSubsidy uint64 // Total subsidy R in pending transactions
	TotalFees    uint64 // Total fees f_AB in pending transactions
}

// GetStats returns current ledger statistics
func (l *Ledger) GetStats() Stats {
	l.mu.RLock()
	defer l.mu.RUnlock()

	stats := Stats{
		PendingCount: len(l.pending),
		SettledCount: len(l.settled),
	}

	for _, p := range l.pending {
		stats.TotalSubsidy += p.R
		stats.TotalFees += p.FAB
	}

	return stats
}

