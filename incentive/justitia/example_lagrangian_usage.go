package justitia

import (
	"fmt"
	"math/big"
)

// ExampleLagrangianUsage demonstrates how to use the Lagrangian optimization mechanism
func ExampleLagrangianUsage() {
	fmt.Println("=== Lagrangian Optimization Example ===")

	// 1. Create a configuration with Lagrangian mode
	config := &Config{
		Mode:         SubsidyLagrangian,
		WindowBlocks: 16,
		LagrangianParams: LagrangianParams{
			Alpha:         0.01,   // Learning rate for shadow price
			WindowSize:    1000.0, // Queue capacity reference
			MinLambda:     1.0,    // Minimum shadow price
			MaxLambda:     10.0,   // Maximum shadow price
			CongestionExp: 2.0,    // Quadratic congestion preference
		},
		MaxInflation: big.NewInt(5000000000000000000), // 5 ETH max per epoch
	}

	// 2. Create a Mechanism instance
	mechanism := NewMechanism(config)

	EA := big.NewInt(1000000000000000) // 0.001 ETH
	EB := big.NewInt(2000000000000000) // 0.002 ETH

	inflationLimit := config.MaxInflation
	totalSubsidyIssued := big.NewInt(0)

	fmt.Printf("Initial Shadow Price (Lambda): %.4f\n\n", mechanism.GetShadowPrice())

	// 3. Simulate multiple blocks with varying congestion
	scenarios := []struct {
		blockNum   int
		queueLen   int64
		description string
	}{
		{1, 200, "Low congestion (20%)"},
		{2, 500, "Medium congestion (50%)"},
		{3, 800, "High congestion (80%)"},
		{4, 900, "Very high congestion (90%)"},
		{5, 950, "Extreme congestion (95%)"},
	}

	for _, scenario := range scenarios {
		metrics := &DynamicMetrics{
			QueueLengthA:     100,
			QueueLengthB:     scenario.queueLen,
			AvgWaitTimeA:     100.0,
			AvgWaitTimeB:     float64(scenario.queueLen) * 0.5,
			CurrentInflation: totalSubsidyIssued,
		}

		// Calculate subsidy
		R := mechanism.CalculateRAB(EA, EB, metrics)

		// Accumulate total subsidy
		totalSubsidyIssued = new(big.Int).Add(totalSubsidyIssued, R)

		// Update shadow price based on inflation constraint
		mechanism.UpdateShadowPrice(totalSubsidyIssued, inflationLimit)

		lambda := mechanism.GetShadowPrice()
		congestionFactor := float64(scenario.queueLen) / 1000.0
		congestionFactorSq := congestionFactor * congestionFactor

		fmt.Printf("Block %d: %s\n", scenario.blockNum, scenario.description)
		fmt.Printf("  Queue: %d/1000 (%.0f%%)\n", scenario.queueLen, congestionFactor*100)
		fmt.Printf("  Congestion Factor²: %.4f\n", congestionFactorSq)
		fmt.Printf("  Shadow Price (λ): %.4f\n", lambda)
		fmt.Printf("  Subsidy R_AB: %s wei (%.6f ETH)\n", R.String(), weiToEth(R))
		fmt.Printf("  Total Subsidy: %s wei (%.6f ETH)\n", totalSubsidyIssued.String(), weiToEth(totalSubsidyIssued))
		fmt.Printf("  Inflation Limit: %.6f ETH\n", weiToEth(inflationLimit))
		fmt.Printf("  Utilization: %.2f%%\n\n", float64(totalSubsidyIssued.Int64())/float64(inflationLimit.Int64())*100)
	}

	// 4. Demonstrate shadow price enforcement
	fmt.Println("=== Shadow Price Enforcement ===")
	fmt.Println("As total subsidy approaches the inflation limit:")
	fmt.Println("- Lambda increases (shadow price rises)")
	fmt.Println("- Subsidy per transaction decreases")
	fmt.Println("- System automatically enforces budget constraint")
}

// ExampleLagrangianEpochManagement demonstrates epoch management
func ExampleLagrangianEpochManagement() {
	fmt.Println("\n=== Lagrangian Epoch Management ===")

	config := DefaultConfig()
	config.Mode = SubsidyLagrangian
	mechanism := NewMechanism(config)

	EA := big.NewInt(1000000000000000)
	EB := big.NewInt(2000000000000000)

	// Simulate end of epoch 1
	fmt.Println("Epoch 1:")
	totalSubsidy1 := big.NewInt(3000000000000000000) // 3 ETH issued
	inflationLimit := big.NewInt(1000000000000000000) // 1 ETH limit

	mechanism.UpdateShadowPrice(totalSubsidy1, inflationLimit)
	lambda1 := mechanism.GetShadowPrice()
	fmt.Printf("  Total Subsidy: %.2f ETH\n", weiToEth(totalSubsidy1))
	fmt.Printf("  Limit: %.2f ETH\n", weiToEth(inflationLimit))
	fmt.Printf("  Lambda after epoch: %.4f (increased due to overspending)\n\n", lambda1)

	// Reset for new epoch
	mechanism.ResetEpoch()
	fmt.Println("Epoch 2 (after reset):")
	fmt.Printf("  Lambda: %.4f (carried over from previous epoch)\n", mechanism.GetShadowPrice())
	fmt.Println("  Total Subsidy: 0 ETH (reset)")
	fmt.Println("  Higher lambda will reduce subsidies in this epoch")

	// Calculate subsidy in new epoch
	metrics := &DynamicMetrics{
		QueueLengthA:     100,
		QueueLengthB:     800,
		AvgWaitTimeA:     100.0,
		AvgWaitTimeB:     400.0,
		CurrentInflation: big.NewInt(0),
	}

	R := mechanism.CalculateRAB(EA, EB, metrics)
	fmt.Printf("  First subsidy in Epoch 2: %.6f ETH\n", weiToEth(R))
	fmt.Println("  (Lower than it would be with Lambda=1.0 due to previous overspending)")
}

// ExampleLagrangianVsPID compares Lagrangian and PID approaches
func ExampleLagrangianVsPID() {
	fmt.Println("\n=== Lagrangian vs PID Comparison ===")

	// Lagrangian mechanism
	lagrangianConfig := DefaultConfig()
	lagrangianConfig.Mode = SubsidyLagrangian
	lagrangianMech := NewMechanism(lagrangianConfig)

	// PID mechanism
	pidConfig := DefaultConfig()
	pidConfig.Mode = SubsidyPID
	pidMech := NewMechanism(pidConfig)

	EA := big.NewInt(1000000000000000)
	EB := big.NewInt(2000000000000000)

	metrics := &DynamicMetrics{
		QueueLengthA:     100,
		QueueLengthB:     800,
		AvgWaitTimeA:     100.0,
		AvgWaitTimeB:     400.0,
		CurrentInflation: big.NewInt(0),
	}

	R_lagrangian := lagrangianMech.CalculateRAB(EA, EB, metrics)
	R_pid := pidMech.CalculateRAB(EA, EB, metrics)

	fmt.Printf("Queue: 800/1000 (80%% congestion)\n\n")
	fmt.Printf("Lagrangian Subsidy: %.6f ETH\n", weiToEth(R_lagrangian))
	fmt.Printf("  - Based on: Congestion² / Lambda\n")
	fmt.Printf("  - Enforces: Global inflation constraint\n")
	fmt.Printf("  - Lambda: %.4f\n\n", lagrangianMech.GetShadowPrice())

	fmt.Printf("PID Subsidy: %.6f ETH\n", weiToEth(R_pid))
	fmt.Printf("  - Based on: Error from target utilization\n")
	fmt.Printf("  - Enforces: Target queue length\n")
	fmt.Printf("  - No global budget constraint\n\n")

	fmt.Println("Key Differences:")
	fmt.Println("- Lagrangian: Global optimization with budget constraint")
	fmt.Println("- PID: Local optimization per shard pair")
}

// Helper function to convert wei to ETH
func weiToEth(wei *big.Int) float64 {
	if wei == nil {
		return 0.0
	}
	weiFloat := new(big.Float).SetInt(wei)
	ethFloat := new(big.Float).Quo(weiFloat, big.NewFloat(1e18))
	result, _ := ethFloat.Float64()
	return result
}
