package pending

import (
	"testing"
	"time"
)

// TestLedger_AddAndGet tests adding and retrieving pending entries
func TestLedger_AddAndGet(t *testing.T) {
	ledger := NewLedger()

	p := &Pending{
		PairID:        "tx001",
		ShardA:        0,
		ShardB:        1,
		FAB:           1000,
		R:             500,
		EA:            200,
		EB:            100,
		UtilityA:      800,
		UtilityB:      700,
		SourceBlockID: "block_A_123",
		CreatedAt:     time.Now().Unix(),
	}

	// Add pending
	err := ledger.Add(p)
	if err != nil {
		t.Errorf("Add should succeed: %v", err)
	}

	// Get pending
	retrieved, exists := ledger.Get("tx001")
	if !exists {
		t.Error("Pending entry should exist")
	}
	if retrieved.PairID != "tx001" {
		t.Errorf("Retrieved wrong entry: %s", retrieved.PairID)
	}
	if retrieved.FAB != 1000 {
		t.Errorf("FAB should be 1000, got %d", retrieved.FAB)
	}
}

// TestLedger_AddDuplicate tests adding duplicate entries
func TestLedger_AddDuplicate(t *testing.T) {
	ledger := NewLedger()

	p1 := &Pending{
		PairID:    "tx001",
		ShardA:    0,
		ShardB:    1,
		CreatedAt: time.Now().Unix(),
	}

	// First add should succeed
	err := ledger.Add(p1)
	if err != nil {
		t.Errorf("First add should succeed: %v", err)
	}

	// Second add should fail
	err = ledger.Add(p1)
	if err == nil {
		t.Error("Adding duplicate should fail")
	}
}

// TestLedger_Settle tests settling a transaction
func TestLedger_Settle(t *testing.T) {
	ledger := NewLedger()

	p := &Pending{
		PairID:        "tx001",
		ShardA:        0,
		ShardB:        1,
		FAB:           1000,
		R:             500,
		UtilityA:      800,
		UtilityB:      700,
		SourceBlockID: "block_A_123",
		CreatedAt:     time.Now().Unix(),
	}

	ledger.Add(p)

	// Track credited amounts
	credited := make(map[string]uint64)
	creditFunc := func(shardID int, proposerID string, amount uint64) {
		credited[proposerID] = amount
	}

	// Settle
	err := ledger.Settle("tx001", "block_B_456", creditFunc)
	if err != nil {
		t.Errorf("Settle should succeed: %v", err)
	}

	// Check that both proposers were credited
	if len(credited) != 2 {
		t.Errorf("Should credit 2 proposers, got %d", len(credited))
	}

	// Verify amounts (can't check exact keys as they're generated, but check values)
	foundA := false
	foundB := false
	for _, amount := range credited {
		if amount == 800 {
			foundA = true
		}
		if amount == 700 {
			foundB = true
		}
	}
	if !foundA || !foundB {
		t.Error("Should credit uA=800 and uB=700")
	}

	// Verify removed from pending
	if ledger.IsPending("tx001") {
		t.Error("Should not be pending after settlement")
	}

	// Verify marked as settled
	if !ledger.IsSettled("tx001") {
		t.Error("Should be marked as settled")
	}
}

// TestLedger_SettleNonExistent tests settling a non-existent transaction
func TestLedger_SettleNonExistent(t *testing.T) {
	ledger := NewLedger()

	creditFunc := func(shardID int, proposerID string, amount uint64) {}

	err := ledger.Settle("nonexistent", "block", creditFunc)
	if err == nil {
		t.Error("Should error when settling non-existent transaction")
	}
}

// TestLedger_SettleTwice tests double settlement
func TestLedger_SettleTwice(t *testing.T) {
	ledger := NewLedger()

	p := &Pending{
		PairID:        "tx001",
		ShardA:        0,
		ShardB:        1,
		UtilityA:      800,
		UtilityB:      700,
		SourceBlockID: "block_A_123",
		CreatedAt:     time.Now().Unix(),
	}

	ledger.Add(p)

	creditFunc := func(shardID int, proposerID string, amount uint64) {}

	// First settlement
	err := ledger.Settle("tx001", "block_B_456", creditFunc)
	if err != nil {
		t.Errorf("First settle should succeed: %v", err)
	}

	// Second settlement should fail
	err = ledger.Settle("tx001", "block_B_789", creditFunc)
	if err == nil {
		t.Error("Double settlement should fail")
	}
}

// TestLedger_GetPendingCount tests counting pending transactions
func TestLedger_GetPendingCount(t *testing.T) {
	ledger := NewLedger()

	if ledger.GetPendingCount() != 0 {
		t.Error("Initial count should be 0")
	}

	// Add 3 pending
	for i := 1; i <= 3; i++ {
		p := &Pending{
			PairID:    string(rune('0' + i)),
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}

	if ledger.GetPendingCount() != 3 {
		t.Errorf("Count should be 3, got %d", ledger.GetPendingCount())
	}

	// Settle one
	creditFunc := func(shardID int, proposerID string, amount uint64) {}
	ledger.Settle("1", "block", creditFunc)

	if ledger.GetPendingCount() != 2 {
		t.Errorf("Count should be 2 after settlement, got %d", ledger.GetPendingCount())
	}
}

// TestLedger_GetAllPending tests retrieving all pending transactions
func TestLedger_GetAllPending(t *testing.T) {
	ledger := NewLedger()

	// Add multiple pending
	for i := 1; i <= 5; i++ {
		p := &Pending{
			PairID:    string(rune('A' + i - 1)),
			ShardA:    i,
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}

	all := ledger.GetAllPending()
	if len(all) != 5 {
		t.Errorf("Should get 5 pending, got %d", len(all))
	}

	// Verify it's a copy (modifying shouldn't affect ledger)
	all[0].FAB = 999999
	retrieved, _ := ledger.Get(all[0].PairID)
	if retrieved.FAB == 999999 {
		t.Error("GetAllPending should return copies, not references")
	}
}

// TestLedger_CleanupOld tests cleanup of old pending entries
func TestLedger_CleanupOld(t *testing.T) {
	ledger := NewLedger()

	now := time.Now().Unix()

	// Add old and new entries
	old1 := &Pending{PairID: "old1", CreatedAt: now - 3600}
	old2 := &Pending{PairID: "old2", CreatedAt: now - 7200}
	new1 := &Pending{PairID: "new1", CreatedAt: now - 60}

	ledger.Add(old1)
	ledger.Add(old2)
	ledger.Add(new1)

	// Cleanup entries older than 1800 seconds
	count := ledger.CleanupOld(now - 1800)

	if count != 2 {
		t.Errorf("Should cleanup 2 old entries, got %d", count)
	}

	if ledger.GetPendingCount() != 1 {
		t.Errorf("Should have 1 pending left, got %d", ledger.GetPendingCount())
	}

	if !ledger.IsPending("new1") {
		t.Error("new1 should still be pending")
	}
}

// TestLedger_GetStats tests statistics
func TestLedger_GetStats(t *testing.T) {
	ledger := NewLedger()

	stats := ledger.GetStats()
	if stats.PendingCount != 0 || stats.SettledCount != 0 {
		t.Error("Initial stats should be all zeros")
	}

	// Add pending with subsidies and fees
	p1 := &Pending{PairID: "tx1", R: 100, FAB: 200, CreatedAt: time.Now().Unix()}
	p2 := &Pending{PairID: "tx2", R: 150, FAB: 300, CreatedAt: time.Now().Unix()}
	ledger.Add(p1)
	ledger.Add(p2)

	stats = ledger.GetStats()
	if stats.PendingCount != 2 {
		t.Errorf("PendingCount should be 2, got %d", stats.PendingCount)
	}
	if stats.TotalSubsidy != 250 {
		t.Errorf("TotalSubsidy should be 250, got %d", stats.TotalSubsidy)
	}
	if stats.TotalFees != 500 {
		t.Errorf("TotalFees should be 500, got %d", stats.TotalFees)
	}

	// Settle one
	creditFunc := func(shardID int, proposerID string, amount uint64) {}
	ledger.Settle("tx1", "block", creditFunc)

	stats = ledger.GetStats()
	if stats.PendingCount != 1 {
		t.Errorf("PendingCount should be 1, got %d", stats.PendingCount)
	}
	if stats.SettledCount != 1 {
		t.Errorf("SettledCount should be 1, got %d", stats.SettledCount)
	}
	if stats.TotalSubsidy != 150 {
		t.Errorf("TotalSubsidy should be 150, got %d", stats.TotalSubsidy)
	}
}

// TestLedger_Reset tests resetting the ledger
func TestLedger_Reset(t *testing.T) {
	ledger := NewLedger()

	// Add some entries
	p1 := &Pending{PairID: "tx1", CreatedAt: time.Now().Unix()}
	ledger.Add(p1)

	creditFunc := func(shardID int, proposerID string, amount uint64) {}
	ledger.Settle("tx1", "block", creditFunc)

	// Reset
	ledger.Reset()

	if ledger.GetPendingCount() != 0 {
		t.Error("After reset, pending count should be 0")
	}
	if ledger.GetSettledCount() != 0 {
		t.Error("After reset, settled count should be 0")
	}
	if ledger.IsPending("tx1") || ledger.IsSettled("tx1") {
		t.Error("After reset, no entries should exist")
	}
}

// TestLedger_AddAfterSettled tests adding after already settled
func TestLedger_AddAfterSettled(t *testing.T) {
	ledger := NewLedger()

	p := &Pending{PairID: "tx1", CreatedAt: time.Now().Unix()}
	ledger.Add(p)

	creditFunc := func(shardID int, proposerID string, amount uint64) {}
	ledger.Settle("tx1", "block", creditFunc)

	// Try to add again with same PairID
	p2 := &Pending{PairID: "tx1", CreatedAt: time.Now().Unix()}
	err := ledger.Add(p2)
	if err == nil {
		t.Error("Should not allow adding already settled transaction")
	}
}

// Benchmark Add
func BenchmarkLedger_Add(b *testing.B) {
	ledger := NewLedger()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		p := &Pending{
			PairID:    string(rune(i)),
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}
}

// Benchmark Settle
func BenchmarkLedger_Settle(b *testing.B) {
	ledger := NewLedger()
	creditFunc := func(shardID int, proposerID string, amount uint64) {}

	// Pre-populate
	for i := 0; i < b.N; i++ {
		p := &Pending{
			PairID:    string(rune(i)),
			CreatedAt: time.Now().Unix(),
		}
		ledger.Add(p)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ledger.Settle(string(rune(i)), "block", creditFunc)
	}
}

