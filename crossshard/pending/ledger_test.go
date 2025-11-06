package pending

import (
	"math/big"
	"testing"
	"time"
)

// TestLedger_AddAndGet tests basic add and get operations
func TestLedger_AddAndGet(t *testing.T) {
	ledger := NewLedger()
	
	p := &Pending{
		PairID:        "tx123",
		ShardA:        0,
		ShardB:        1,
		FAB:           big.NewInt(100),
		R:             big.NewInt(50),
		EA:            big.NewInt(80),
		EB:            big.NewInt(70),
		UtilityA:      big.NewInt(75),
		UtilityB:      big.NewInt(75),
		SourceBlockID: "block_A_1",
		CreatedAt:     time.Now().Unix(),
	}
	
	// Add pending
	err := ledger.Add(p)
	if err != nil {
		t.Fatalf("Add() failed: %v", err)
	}
	
	// Retrieve pending
	retrieved, exists := ledger.Get("tx123")
	if !exists {
		t.Fatal("Get() failed: pending not found")
	}
	
	// Verify fields
	if retrieved.PairID != p.PairID {
		t.Errorf("PairID mismatch: got %v, want %v", retrieved.PairID, p.PairID)
	}
	if retrieved.FAB.Cmp(p.FAB) != 0 {
		t.Errorf("FAB mismatch: got %v, want %v", retrieved.FAB, p.FAB)
	}
}

// TestLedger_AddDuplicate tests adding duplicate entries
func TestLedger_AddDuplicate(t *testing.T) {
	ledger := NewLedger()
	
	p := &Pending{
		PairID:    "tx123",
		FAB:       big.NewInt(100),
		CreatedAt: time.Now().Unix(),
	}
	
	// First add should succeed
	err := ledger.Add(p)
	if err != nil {
		t.Fatalf("First Add() failed: %v", err)
	}
	
	// Second add should fail
	err = ledger.Add(p)
	if err == nil {
		t.Error("Second Add() should have failed")
	}
}

// TestLedger_Settle tests settlement process
func TestLedger_Settle(t *testing.T) {
	ledger := NewLedger()
	
	p := &Pending{
		PairID:        "tx123",
		ShardA:        0,
		ShardB:        1,
		FAB:           big.NewInt(100),
		R:             big.NewInt(50),
		EA:            big.NewInt(80),
		EB:            big.NewInt(70),
		UtilityA:      big.NewInt(75),
		UtilityB:      big.NewInt(75),
		SourceBlockID: "block_A_1",
		CreatedAt:     time.Now().Unix(),
	}
	
	ledger.Add(p)
	
	// Track credited amounts
	credited := make(map[int]*big.Int)
	creditFunc := func(shardID int, proposerID string, amount *big.Int) {
		if _, exists := credited[shardID]; !exists {
			credited[shardID] = big.NewInt(0)
		}
		credited[shardID].Add(credited[shardID], amount)
	}
	
	// Settle
	err := ledger.Settle("tx123", "block_B_1", creditFunc)
	if err != nil {
		t.Fatalf("Settle() failed: %v", err)
	}
	
	// Verify credits
	if credited[0].Cmp(big.NewInt(75)) != 0 {
		t.Errorf("Shard A credit = %v, want 75", credited[0])
	}
	if credited[1].Cmp(big.NewInt(75)) != 0 {
		t.Errorf("Shard B credit = %v, want 75", credited[1])
	}
	
	// Verify pending removed
	if ledger.IsPending("tx123") {
		t.Error("Transaction should not be pending after settlement")
	}
	
	// Verify marked as settled
	if !ledger.IsSettled("tx123") {
		t.Error("Transaction should be marked as settled")
	}
}

// TestLedger_SettleNonExistent tests settling non-existent transaction
func TestLedger_SettleNonExistent(t *testing.T) {
	ledger := NewLedger()
	
	creditFunc := func(shardID int, proposerID string, amount *big.Int) {
		// Should not be called
		t.Error("creditFunc should not be called")
	}
	
	err := ledger.Settle("nonexistent", "block", creditFunc)
	if err == nil {
		t.Error("Settle() should fail for non-existent transaction")
	}
}

// TestLedger_DoubleSettlement tests prevention of double settlement
func TestLedger_DoubleSettlement(t *testing.T) {
	ledger := NewLedger()
	
	p := &Pending{
		PairID:        "tx123",
		ShardA:        0,
		ShardB:        1,
		FAB:           big.NewInt(100),
		R:             big.NewInt(50),
		UtilityA:      big.NewInt(75),
		UtilityB:      big.NewInt(75),
		SourceBlockID: "block_A_1",
		CreatedAt:     time.Now().Unix(),
	}
	
	ledger.Add(p)
	
	callCount := 0
	creditFunc := func(shardID int, proposerID string, amount *big.Int) {
		callCount++
	}
	
	// First settlement should succeed
	err := ledger.Settle("tx123", "block_B_1", creditFunc)
	if err != nil {
		t.Fatalf("First Settle() failed: %v", err)
	}
	
	if callCount != 2 {
		t.Errorf("creditFunc called %d times, want 2", callCount)
	}
	
	// Second settlement should fail
	err = ledger.Settle("tx123", "block_B_2", creditFunc)
	if err == nil {
		t.Error("Second Settle() should have failed")
	}
	
	// Credit function should not be called again
	if callCount != 2 {
		t.Errorf("creditFunc called %d times after double settlement, want 2", callCount)
	}
}

// TestLedger_GetPendingCount tests counting pending transactions
func TestLedger_GetPendingCount(t *testing.T) {
	ledger := NewLedger()
	
	if ledger.GetPendingCount() != 0 {
		t.Error("Initial pending count should be 0")
	}
	
	// Add 3 pending (with all required fields initialized)
	for i := 0; i < 3; i++ {
		p := &Pending{
			PairID:    string(rune('a' + i)),
			ShardA:    0,
			ShardB:    1,
			FAB:       big.NewInt(100),
			R:         big.NewInt(50),
			EA:        big.NewInt(80),
			EB:        big.NewInt(70),
			UtilityA:  big.NewInt(75),
			UtilityB:  big.NewInt(75),
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}
	
	if ledger.GetPendingCount() != 3 {
		t.Errorf("Pending count = %d, want 3", ledger.GetPendingCount())
	}
	
	// Settle one
	creditFunc := func(shardID int, proposerID string, amount *big.Int) {}
	ledger.Settle("a", "block", creditFunc)
	
	if ledger.GetPendingCount() != 2 {
		t.Errorf("Pending count after settlement = %d, want 2", ledger.GetPendingCount())
	}
}

// TestLedger_GetStats tests statistics retrieval
func TestLedger_GetStats(t *testing.T) {
	ledger := NewLedger()
	
	// Add 2 pending with known fees and subsidies
	p1 := &Pending{
		PairID:    "tx1",
		ShardA:    0,
		ShardB:    1,
		FAB:       big.NewInt(100),
		R:         big.NewInt(50),
		EA:        big.NewInt(80),
		EB:        big.NewInt(70),
		UtilityA:  big.NewInt(75),
		UtilityB:  big.NewInt(75),
		CreatedAt: time.Now().Unix(),
	}
	p2 := &Pending{
		PairID:    "tx2",
		ShardA:    0,
		ShardB:    1,
		FAB:       big.NewInt(200),
		R:         big.NewInt(100),
		EA:        big.NewInt(80),
		EB:        big.NewInt(70),
		UtilityA:  big.NewInt(150),
		UtilityB:  big.NewInt(150),
		CreatedAt: time.Now().Unix(),
	}
	
	ledger.Add(p1)
	ledger.Add(p2)
	
	stats := ledger.GetStats()
	
	if stats.PendingCount != 2 {
		t.Errorf("PendingCount = %d, want 2", stats.PendingCount)
	}
	
	// TotalFees should be 100 + 200 = 300
	if stats.TotalFees.Cmp(big.NewInt(300)) != 0 {
		t.Errorf("TotalFees = %v, want 300", stats.TotalFees)
	}
	
	// TotalSubsidy should be 50 + 100 = 150
	if stats.TotalSubsidy.Cmp(big.NewInt(150)) != 0 {
		t.Errorf("TotalSubsidy = %v, want 150", stats.TotalSubsidy)
	}
}

// TestLedger_CleanupOld tests old transaction cleanup
func TestLedger_CleanupOld(t *testing.T) {
	ledger := NewLedger()
	
	now := time.Now().Unix()
	
	// Add old transaction
	old := &Pending{
		PairID:    "old",
		ShardA:    0,
		ShardB:    1,
		FAB:       big.NewInt(100),
		R:         big.NewInt(50),
		EA:        big.NewInt(80),
		EB:        big.NewInt(70),
		UtilityA:  big.NewInt(75),
		UtilityB:  big.NewInt(75),
		CreatedAt: now - 1000,
	}
	ledger.Add(old)
	
	// Add recent transaction
	recent := &Pending{
		PairID:    "recent",
		ShardA:    0,
		ShardB:    1,
		FAB:       big.NewInt(100),
		R:         big.NewInt(50),
		EA:        big.NewInt(80),
		EB:        big.NewInt(70),
		UtilityA:  big.NewInt(75),
		UtilityB:  big.NewInt(75),
		CreatedAt: now,
	}
	ledger.Add(recent)
	
	// Cleanup transactions older than (now - 500)
	cleaned := ledger.CleanupOld(now - 500)
	
	if cleaned != 1 {
		t.Errorf("CleanupOld() removed %d, want 1", cleaned)
	}
	
	// Old should be removed
	if ledger.IsPending("old") {
		t.Error("Old transaction should be removed")
	}
	
	// Recent should remain
	if !ledger.IsPending("recent") {
		t.Error("Recent transaction should remain")
	}
}

// TestLedger_GetAllPending tests retrieving all pending transactions
func TestLedger_GetAllPending(t *testing.T) {
	ledger := NewLedger()
	
	// Add 3 pending
	for i := 0; i < 3; i++ {
		p := &Pending{
			PairID:    string(rune('a' + i)),
			ShardA:    0,
			ShardB:    1,
			FAB:       big.NewInt(int64(100 * (i + 1))),
			R:         big.NewInt(50),
			EA:        big.NewInt(80),
			EB:        big.NewInt(70),
			UtilityA:  big.NewInt(75),
			UtilityB:  big.NewInt(75),
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}
	
	all := ledger.GetAllPending()
	
	if len(all) != 3 {
		t.Errorf("GetAllPending() returned %d, want 3", len(all))
	}
	
	// Verify it's a copy (modifying returned values shouldn't affect ledger)
	all[0].FAB = big.NewInt(999)
	
	retrieved, _ := ledger.Get(all[0].PairID)
	if retrieved.FAB.Cmp(big.NewInt(999)) == 0 {
		t.Error("Modification to returned pending affected ledger (not a copy)")
	}
}

// TestLedger_Reset tests resetting the ledger
func TestLedger_Reset(t *testing.T) {
	ledger := NewLedger()
	
	// Add some data
	p := &Pending{
		PairID:    "tx123",
		ShardA:    0,
		ShardB:    1,
		FAB:       big.NewInt(100),
		R:         big.NewInt(50),
		EA:        big.NewInt(80),
		EB:        big.NewInt(70),
		UtilityA:  big.NewInt(75),
		UtilityB:  big.NewInt(75),
		CreatedAt: time.Now().Unix(),
	}
	ledger.Add(p)
	
	creditFunc := func(shardID int, proposerID string, amount *big.Int) {}
	ledger.Settle("tx123", "block", creditFunc)
	
	// Reset
	ledger.Reset()
	
	// Verify all cleared
	if ledger.GetPendingCount() != 0 {
		t.Error("Pending count should be 0 after reset")
	}
	if ledger.GetSettledCount() != 0 {
		t.Error("Settled count should be 0 after reset")
	}
}

// BenchmarkLedger_Add benchmarks adding pending transactions
func BenchmarkLedger_Add(b *testing.B) {
	ledger := NewLedger()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		p := &Pending{
			PairID:    string(rune(i)),
			ShardA:    0,
			ShardB:    1,
			FAB:       big.NewInt(100),
			R:         big.NewInt(50),
			EA:        big.NewInt(80),
			EB:        big.NewInt(70),
			UtilityA:  big.NewInt(75),
			UtilityB:  big.NewInt(75),
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}
}

// BenchmarkLedger_Get benchmarks retrieving pending transactions
func BenchmarkLedger_Get(b *testing.B) {
	ledger := NewLedger()
	p := &Pending{
		PairID:    "tx123",
		ShardA:    0,
		ShardB:    1,
		FAB:       big.NewInt(100),
		R:         big.NewInt(50),
		EA:        big.NewInt(80),
		EB:        big.NewInt(70),
		UtilityA:  big.NewInt(75),
		UtilityB:  big.NewInt(75),
		CreatedAt: time.Now().Unix(),
	}
	ledger.Add(p)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = ledger.Get("tx123")
	}
}
