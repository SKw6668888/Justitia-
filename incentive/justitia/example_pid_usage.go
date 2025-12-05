package justitia

import (
	"fmt"
	"math/big"
)

// ExamplePIDUsage demonstrates how to use the PID-controlled subsidy mechanism
func ExamplePIDUsage() {
	// 1. Create a configuration with PID mode
	config := &Config{
		Mode:         SubsidyPID,
		WindowBlocks: 16,
		PIDParams: PIDParams{
			Kp:                1.5,   // Proportional gain
			Ki:                0.1,   // Integral gain
			Kd:                0.05,  // Derivative gain
			TargetUtilization: 0.7,   // Target 70% queue utilization
			CapacityB:         1000.0, // Destination shard queue capacity
			MinSubsidy:        0.0,   // Minimum subsidy (0x EB)
			MaxSubsidy:        5.0,   // Maximum subsidy (5x EB)
		},
		MaxInflation: big.NewInt(1000000000000000000), // 1 ETH max per epoch
	}

	// 2. Create a Mechanism instance (holds PID state)
	mechanism := NewMechanism(config)

	// 3. Simulate multiple blocks with varying queue lengths
	EA := big.NewInt(1000000000000000) // 0.001 ETH average fee in shard A
	EB := big.NewInt(2000000000000000) // 0.002 ETH average fee in shard B

	// Block 1: Low queue utilization (30%)
	metrics1 := &DynamicMetrics{
		QueueLengthA:     50,
		QueueLengthB:     300, // 30% of capacity (1000)
		AvgWaitTimeA:     100.0,
		AvgWaitTimeB:     200.0,
		CurrentInflation: big.NewInt(0),
	}
	R1 := mechanism.CalculateRAB(EA, EB, metrics1)
	fmt.Printf("Block 1 - Queue: 300/1000 (30%%), Subsidy: %s wei\n", R1.String())

	// Block 2: Target utilization (70%)
	metrics2 := &DynamicMetrics{
		QueueLengthA:     100,
		QueueLengthB:     700, // 70% of capacity (target)
		AvgWaitTimeA:     150.0,
		AvgWaitTimeB:     300.0,
		CurrentInflation: big.NewInt(0),
	}
	R2 := mechanism.CalculateRAB(EA, EB, metrics2)
	fmt.Printf("Block 2 - Queue: 700/1000 (70%%), Subsidy: %s wei\n", R2.String())

	// Block 3: High queue utilization (90%)
	metrics3 := &DynamicMetrics{
		QueueLengthA:     80,
		QueueLengthB:     900, // 90% of capacity (congested!)
		AvgWaitTimeA:     120.0,
		AvgWaitTimeB:     500.0,
		CurrentInflation: big.NewInt(0),
	}
	R3 := mechanism.CalculateRAB(EA, EB, metrics3)
	fmt.Printf("Block 3 - Queue: 900/1000 (90%%), Subsidy: %s wei\n", R3.String())

	// 4. Compute utilities using Shapley value split
	fAB := big.NewInt(3000000000000000) // 0.003 ETH transaction fee
	uA, uB := Split2(fAB, R3, EA, EB)
	fmt.Printf("\nShapley Split:\n")
	fmt.Printf("  Source Shard A utility: %s wei\n", uA.String())
	fmt.Printf("  Dest Shard B utility:   %s wei\n", uB.String())
	fmt.Printf("  Total (fAB + R):        %s wei\n", new(big.Int).Add(uA, uB).String())

	// 5. Classify the transaction
	txCase := Classify(uA, EA, EB)
	fmt.Printf("  Transaction Case: %s\n", txCase.String())
}

// ExampleBackwardCompatibility shows that old stateless RAB still works
func ExampleBackwardCompatibility() {
	EA := big.NewInt(1000000000000000)
	EB := big.NewInt(2000000000000000)

	// Old stateless API still works for non-PID modes
	R_destAvg := RAB(SubsidyDestAvg, EA, EB, nil, nil)
	fmt.Printf("DestAvg mode (stateless): %s wei\n", R_destAvg.String())

	R_sumAvg := RAB(SubsidySumAvg, EA, EB, nil, nil)
	fmt.Printf("SumAvg mode (stateless):  %s wei\n", R_sumAvg.String())

	// PID mode falls back to DestAvg when using stateless API
	R_pid := RAB(SubsidyPID, EA, EB, nil, nil)
	fmt.Printf("PID mode (stateless fallback): %s wei\n", R_pid.String())
}
