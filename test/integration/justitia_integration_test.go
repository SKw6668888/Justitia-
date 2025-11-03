// Integration tests for Justitia incentive mechanism
package integration

import (
	"blockEmulator/core"
	"blockEmulator/crossshard/pending"
	"blockEmulator/economics/subsidy_budget"
	"blockEmulator/fees/expectation"
	"blockEmulator/incentive/justitia"
	"blockEmulator/txpool/scheduler"
	"blockEmulator/utils"
	"math/big"
	"testing"
	"time"
)

// TestJustitia_EndToEndFlow tests the complete Justitia workflow
func TestJustitia_EndToEndFlow(t *testing.T) {
	// Setup
	numShards := 4
	feeTracker := expectation.NewTracker(16)
	ledger := pending.NewLedger()

	// Initialize some baseline ITX fees for each shard
	// Shard 0: high fees (EA = 1000)
	// Shard 1: low fees (EB = 500)
	for i := 0; i < 20; i++ {
		feeTracker.OnBlockFinalized(0, []uint64{900, 1000, 1100})
		feeTracker.OnBlockFinalized(1, []uint64{400, 500, 600})
	}

	EA := feeTracker.GetAvgITXFee(0)
	EB := feeTracker.GetAvgITXFee(1)

	t.Logf("EA (shard 0) = %d, EB (shard 1) = %d", EA, EB)

	// Create a cross-shard transaction from shard 0 to shard 1
	ctx := core.NewTransaction(
		"0x1111111111111111", // sender in shard 0
		"0xaaaaaaaaaaaaaaaa", // recipient in shard 1
		big.NewInt(100),
		1,
		time.Now(),
	)

	// Set up transaction fields
	ctx.FromShard = utils.ShardForAddress(ctx.Sender, numShards)
	ctx.ToShard = utils.ShardForAddress(ctx.Recipient, numShards)
	ctx.IsCrossShard = (ctx.FromShard != ctx.ToShard)
	ctx.PairID = string(ctx.TxHash)
	ctx.FeeToProposer = 800 // User pays 800 as fee

	if !ctx.IsCrossShard {
		t.Fatal("Transaction should be cross-shard")
	}

	t.Logf("CTX: from shard %d to shard %d, fee = %d", ctx.FromShard, ctx.ToShard, ctx.FeeToProposer)

	// Compute subsidy using DestAvg mode
	R := justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil)
	ctx.SubsidyR = R

	t.Logf("Subsidy R = %d (mode: DestAvg = EB)", R)

	// Compute Shapley split
	uA, uB := justitia.Split2(ctx.FeeToProposer, R, EA, EB)
	ctx.UtilityA = uA
	ctx.UtilityB = uB

	t.Logf("Utilities: uA = %d, uB = %d (sum = %d)", uA, uB, uA+uB)

	// Verify invariant
	if uA+uB != ctx.FeeToProposer+R {
		t.Errorf("Invariant violated: uA+uB=%d, fee+R=%d", uA+uB, ctx.FeeToProposer+R)
	}

	// Classify transaction at source shard
	txCase := justitia.Classify(uA, EA, EB)
	ctx.JustitiaCase = int(txCase)

	t.Logf("Classification: %v", txCase)

	// Step 1: Source shard A includes CTX in block
	ctx.IncludedInBlockA = 100

	// Add to pending ledger
	p := &pending.Pending{
		PairID:        ctx.PairID,
		ShardA:        ctx.FromShard,
		ShardB:        ctx.ToShard,
		FAB:           ctx.FeeToProposer,
		R:             ctx.SubsidyR,
		EA:            EA,
		EB:            EB,
		UtilityA:      ctx.UtilityA,
		UtilityB:      ctx.UtilityB,
		SourceBlockID: "block_A_100",
		CreatedAt:     time.Now().Unix(),
	}

	err := ledger.Add(p)
	if err != nil {
		t.Fatalf("Failed to add to ledger: %v", err)
	}

	t.Logf("Added to pending ledger, pending count = %d", ledger.GetPendingCount())

	// Step 2: Destination shard B includes CTX' in block
	ctx.IncludedInBlockB = 105
	ctx.IsRelay2 = true

	// Track rewards
	rewards := make(map[string]uint64)
	creditFunc := func(shardID int, proposerID string, amount uint64) {
		rewards[proposerID] = amount
		t.Logf("Credited %d to %s (shard %d)", amount, proposerID, shardID)
	}

	// Settle
	err = ledger.Settle(ctx.PairID, "block_B_105", creditFunc)
	if err != nil {
		t.Fatalf("Failed to settle: %v", err)
	}

	t.Logf("Settlement complete, pending count = %d", ledger.GetPendingCount())

	// Verify rewards were credited
	if len(rewards) != 2 {
		t.Errorf("Should credit 2 proposers, got %d", len(rewards))
	}

	// Verify total rewards = fee + subsidy
	var totalRewarded uint64
	for _, amt := range rewards {
		totalRewarded += amt
	}
	expected := ctx.FeeToProposer + ctx.SubsidyR
	if totalRewarded != expected {
		t.Errorf("Total rewarded = %d, expected %d", totalRewarded, expected)
	}

	// Verify transaction is no longer pending
	if ledger.IsPending(ctx.PairID) {
		t.Error("Transaction should not be pending after settlement")
	}
	if !ledger.IsSettled(ctx.PairID) {
		t.Error("Transaction should be marked as settled")
	}
}

// TestJustitia_TransactionSelection tests transaction selection with different cases
func TestJustitia_TransactionSelection(t *testing.T) {
	numShards := 4
	feeTracker := expectation.NewTracker(16)

	// Initialize shard 0 with EA = 1000
	for i := 0; i < 20; i++ {
		feeTracker.OnBlockFinalized(0, []uint64{1000})
	}

	// Create scheduler for shard 0
	sched := scheduler.NewScheduler(0, numShards, feeTracker, justitia.SubsidyDestAvg)

	// Create transaction pool with mixed ITX and CTX
	txPool := make([]*core.Transaction, 0)

	// ITX with high fee (should be selected in phase 1)
	itxHigh := core.NewTransaction("0x1111", "0x2222", big.NewInt(100), 1, time.Now())
	itxHigh.IsCrossShard = false
	itxHigh.FeeToProposer = 1200 // > EA
	txPool = append(txPool, itxHigh)

	// ITX with low fee (should be in phase 2)
	itxLow := core.NewTransaction("0x1111", "0x2223", big.NewInt(100), 2, time.Now())
	itxLow.IsCrossShard = false
	itxLow.FeeToProposer = 500 // < EA
	txPool = append(txPool, itxLow)

	// CTX Case1: high utility (should be selected in phase 1)
	ctxCase1 := core.NewTransaction("0x1111", "0xaaaa", big.NewInt(100), 3, time.Now())
	ctxCase1.IsCrossShard = true
	ctxCase1.FromShard = 0
	ctxCase1.ToShard = 1
	ctxCase1.FeeToProposer = 1500 // Will result in high uA
	feeTracker.OnBlockFinalized(1, []uint64{500}) // EB = 500
	txPool = append(txPool, ctxCase1)

	// CTX Case2: very low utility (should be excluded)
	// To make it Case2: uA <= EA - EB
	// With fAB=10, R=EB, we need EA - 2*EB >= 10
	// If EA=1000, EB=100: EA - 2*EB = 800 >= 10 ✓
	ctxCase2 := core.NewTransaction("0x1111", "0xbbbb", big.NewInt(100), 4, time.Now())
	ctxCase2.IsCrossShard = true
	ctxCase2.FromShard = 0
	ctxCase2.ToShard = 2
	ctxCase2.FeeToProposer = 10 // Very low fee
	feeTracker.OnBlockFinalized(2, []uint64{100}) // EB = 100 (low to ensure Case2)
	txPool = append(txPool, ctxCase2)

	// Select transactions for a block with capacity 3
	selected := sched.SelectForBlock(3, txPool)

	t.Logf("Selected %d transactions out of %d", len(selected), len(txPool))

	// Verify selection
	if len(selected) > 3 {
		t.Errorf("Should not exceed capacity of 3, got %d", len(selected))
	}

	// Verify high-priority transactions are included
	foundITXHigh := false
	foundCTXCase1 := false
	foundCTXCase2 := false

	for _, tx := range selected {
		if tx == itxHigh {
			foundITXHigh = true
		}
		if tx == ctxCase1 {
			foundCTXCase1 = true
		}
		if tx == ctxCase2 {
			foundCTXCase2 = true
		}
	}

	if !foundITXHigh {
		t.Error("High-fee ITX should be selected")
	}
	if !foundCTXCase1 {
		t.Error("Case1 CTX should be selected")
	}
	if foundCTXCase2 {
		t.Error("Case2 CTX should be excluded")
	}
}

// TestJustitia_SubsidyModes tests different subsidy modes
func TestJustitia_SubsidyModes(t *testing.T) {
	EA := uint64(1000)
	EB := uint64(500)

	// Mode: None
	R := justitia.RAB(justitia.SubsidyNone, EA, EB, nil)
	if R != 0 {
		t.Errorf("SubsidyNone: expected 0, got %d", R)
	}

	// Mode: DestAvg
	R = justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil)
	if R != EB {
		t.Errorf("SubsidyDestAvg: expected %d, got %d", EB, R)
	}

	// Mode: SumAvg
	R = justitia.RAB(justitia.SubsidySumAvg, EA, EB, nil)
	expected := EA + EB
	if R != expected {
		t.Errorf("SubsidySumAvg: expected %d, got %d", expected, R)
	}

	// Mode: Custom
	customFunc := func(ea, eb uint64) uint64 {
		return ea * 2 // Custom: 2x source average
	}
	R = justitia.RAB(justitia.SubsidyCustom, EA, EB, customFunc)
	expected = EA * 2
	if R != expected {
		t.Errorf("SubsidyCustom: expected %d, got %d", expected, R)
	}
}

// TestJustitia_BudgetConstraints tests subsidy budget enforcement
func TestJustitia_BudgetConstraints(t *testing.T) {
	budget, err := subsidy_budget.NewBudget(1000, 5000)
	if err != nil {
		t.Fatalf("Failed to create budget: %v", err)
	}

	// Test case 1: Within bounds (no scaling)
	subsidies := []uint64{1000, 1500, 1000}
	scaled, sf := subsidy_budget.ApplyBudgetToBlock(budget, subsidies)

	if sf.IsScalingNeeded() {
		t.Error("Should not need scaling when within bounds")
	}
	for i, s := range scaled {
		if s != subsidies[i] {
			t.Errorf("No scaling: index %d expected %d, got %d", i, subsidies[i], s)
		}
	}

	// Test case 2: Exceeds max (scale down)
	subsidies = []uint64{3000, 3000, 2000} // sum = 8000 > 5000
	scaled, sf = subsidy_budget.ApplyBudgetToBlock(budget, subsidies)

	if !sf.IsScalingNeeded() {
		t.Error("Should need scaling when exceeding max")
	}

	var sumScaled uint64
	for _, s := range scaled {
		sumScaled += s
	}

	// Sum should be close to Bmax (within rounding error)
	if sumScaled > budget.Bmax || sumScaled < budget.Bmax-uint64(len(subsidies)) {
		t.Errorf("Scaled sum should be ~%d, got %d", budget.Bmax, sumScaled)
	}

	t.Logf("Scaling factor: %s", sf.String())
	t.Logf("Original sum: 8000, scaled sum: %d", sumScaled)
}

// TestJustitia_CTXvsITXDelayComparison tests that Justitia improves CTX delays
func TestJustitia_CTXvsITXDelayComparison(t *testing.T) {
	// This is a simplified test demonstrating the concept
	// In a real system, we'd measure actual queue delays

	feeTracker := expectation.NewTracker(16)

	// Set up shards with different fee levels
	for i := 0; i < 20; i++ {
		feeTracker.OnBlockFinalized(0, []uint64{1000, 1100, 900})
		feeTracker.OnBlockFinalized(1, []uint64{500, 600, 400})
	}

	// Create a CTX with moderate fee
	ctx := core.NewTransaction("0x1111", "0xaaaa", big.NewInt(100), 1, time.Now())
	ctx.IsCrossShard = true
	ctx.FromShard = 0
	ctx.ToShard = 1
	ctx.FeeToProposer = 700 // Less than EA (1000), but will get subsidy

	// Compute its score with Justitia
	EA := feeTracker.GetAvgITXFee(0)
	EB := feeTracker.GetAvgITXFee(1)
	R := justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil)
	uA, _ := justitia.Split2(ctx.FeeToProposer, R, EA, EB)

	t.Logf("CTX fee = %d, subsidy R = %d, utility uA = %d", ctx.FeeToProposer, R, uA)

	// With subsidy, uA should be competitive with ITX fees
	if uA < EA {
		t.Logf("uA < EA, CTX would be in Case2 or Case3")
	} else {
		t.Logf("uA >= EA, CTX is in Case1 (high priority)")
	}

	// Compare to no subsidy case
	uA_noSubsidy, _ := justitia.Split2(ctx.FeeToProposer, 0, EA, EB)
	t.Logf("Without subsidy: uA would be %d (much lower)", uA_noSubsidy)

	if uA <= uA_noSubsidy {
		t.Error("Subsidy should increase utility")
	}
}

// Benchmark full workflow
func BenchmarkJustitia_EndToEndFlow(b *testing.B) {
	feeTracker := expectation.NewTracker(16)
	ledger := pending.NewLedger()

	// Initialize fees
	for i := 0; i < 20; i++ {
		feeTracker.OnBlockFinalized(0, []uint64{1000})
		feeTracker.OnBlockFinalized(1, []uint64{500})
	}

	EA := feeTracker.GetAvgITXFee(0)
	EB := feeTracker.GetAvgITXFee(1)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		// Create CTX
		ctx := core.NewTransaction("0x1111", "0xaaaa", big.NewInt(100), uint64(i), time.Now())
		ctx.FromShard = 0
		ctx.ToShard = 1
		ctx.IsCrossShard = true
		ctx.PairID = string(ctx.TxHash)
		ctx.FeeToProposer = 800

		// Compute subsidy and split
		R := justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil)
		uA, uB := justitia.Split2(ctx.FeeToProposer, R, EA, EB)

		// Add to ledger
		p := &pending.Pending{
			PairID:        ctx.PairID,
			ShardA:        0,
			ShardB:        1,
			FAB:           ctx.FeeToProposer,
			R:             R,
			EA:            EA,
			EB:            EB,
			UtilityA:      uA,
			UtilityB:      uB,
			SourceBlockID: "block",
			CreatedAt:     time.Now().Unix(),
		}
		ledger.Add(p)

		// Settle
		creditFunc := func(shardID int, proposerID string, amount uint64) {}
		ledger.Settle(ctx.PairID, "block", creditFunc)
	}
}

