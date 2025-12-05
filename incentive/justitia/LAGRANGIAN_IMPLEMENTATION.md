# Lagrangian Optimization Mechanism Implementation

## Overview

The Lagrangian optimization mechanism dynamically adjusts subsidies `R_AB` to maximize cross-shard transaction throughput while enforcing a global inflation constraint `Σ R_AB ≤ Γ_max`. It uses a shadow price (Lagrange multiplier) that increases when approaching the budget limit.

## Theoretical Foundation

### Optimization Problem

```
Maximize:   Σ Throughput(R_AB)
Subject to: Σ R_AB ≤ Γ_max
```

### Lagrangian Formulation

```
L(R, λ) = Σ Throughput(R_AB) - λ(Σ R_AB - Γ_max)
```

Where:
- `λ` (lambda) is the shadow price (Lagrange multiplier)
- Higher `λ` indicates tighter budget constraint

### Optimal Subsidy

```
R_AB = (EB * CongestionFactor) / λ

where:
  CongestionFactor = (QueueLengthB / WindowSize)^CongestionExp
  λ = shadow price (updated based on budget violation)
```

## Architecture

### Key Components

1. **`LagrangianState`** - Holds optimization state:
   - `Lambda`: Shadow price (Lagrange multiplier)
   - `TotalSubsidy`: Cumulative subsidy in current epoch
   - `LastUpdate`: Timestamp of last update
   - `EpochStartTime`: Start of current epoch

2. **`LagrangianParams`** - Configuration parameters:
   - `Alpha`: Learning rate for shadow price update (default: 0.01)
   - `WindowSize`: Reference queue capacity (default: 1000.0)
   - `MinLambda`: Minimum shadow price (default: 1.0)
   - `MaxLambda`: Maximum shadow price (default: 10.0)
   - `CongestionExp`: Congestion exponent (default: 2.0 for quadratic)

3. **`Mechanism`** - Stateful wrapper:
   - Maintains `LagrangianState` across calls
   - Thread-safe with mutex protection
   - Provides `UpdateShadowPrice()` method

## Algorithm Details

### Subsidy Calculation

```go
// Step 1: Calculate congestion factor (quadratic preference)
utilization = QueueLengthB / WindowSize
congestionFactor = utilization^CongestionExp

// Step 2: Apply shadow price
multiplier = congestionFactor / Lambda

// Step 3: Calculate subsidy
R_AB = EB * multiplier
```

**Intuition:**
- High congestion → High `congestionFactor` → Higher subsidy
- High `Lambda` → Lower subsidy (budget constraint active)
- Quadratic exponent gives strong preference to congested shards

### Shadow Price Update

```go
// Step 1: Calculate constraint violation
violation = TotalSubsidy - InflationLimit

// Step 2: Normalize by limit (scale-independent)
normalizedViolation = violation / InflationLimit

// Step 3: Update shadow price
Lambda_new = Lambda_old + Alpha * normalizedViolation

// Step 4: Clamp to bounds
Lambda_new = clamp(Lambda_new, MinLambda, MaxLambda)
```

**Behavior:**
- `TotalSubsidy > Limit` → `Lambda` increases → Future subsidies decrease
- `TotalSubsidy < Limit` → `Lambda` decreases → Future subsidies increase
- `Lambda ≥ 1.0` always (prevents negative subsidies)

## Usage

### Basic Setup

```go
import "blockEmulator/incentive/justitia"

// Create configuration
config := &justitia.Config{
    Mode: justitia.SubsidyLagrangian,
    LagrangianParams: justitia.LagrangianParams{
        Alpha:         0.01,   // Learning rate
        WindowSize:    1000.0, // Queue capacity
        MinLambda:     1.0,
        MaxLambda:     10.0,
        CongestionExp: 2.0,    // Quadratic
    },
    MaxInflation: big.NewInt(5000000000000000000), // 5 ETH per epoch
}

// Create mechanism
mechanism := justitia.NewMechanism(config)
```

### Per-Block Subsidy Calculation

```go
// Get current metrics
metrics := txpool.GetMetrics()

// Calculate subsidy for this transaction
R := mechanism.CalculateRAB(EA, EB, &metrics)

// Use subsidy in Shapley split
uA, uB := justitia.Split2(fAB, R, EA, EB)
```

### Epoch Management

```go
// At end of each block: Update shadow price
totalSubsidyIssued := blockchain.GetTotalSubsidyInEpoch()
inflationLimit := config.MaxInflation
mechanism.UpdateShadowPrice(totalSubsidyIssued, inflationLimit)

// At start of new epoch: Reset counters
mechanism.ResetEpoch()
```

### Integration with Blockchain

**In `chain/blockchain.go` (or equivalent):**

```go
type BlockChain struct {
    // ... existing fields ...
    justitiaMechanism *justitia.Mechanism
    epochSubsidyTotal *big.Int
}

// When processing a cross-shard transaction
func (bc *BlockChain) ProcessCTX(tx *Transaction) {
    // Get metrics
    metrics := bc.txPool.GetMetrics()
    
    // Calculate subsidy
    R := bc.justitiaMechanism.CalculateRAB(EA, EB, &metrics)
    
    // Track total subsidy
    bc.epochSubsidyTotal.Add(bc.epochSubsidyTotal, R)
    
    // Use subsidy for reward allocation
    uA, uB := justitia.Split2(tx.Fee, R, EA, EB)
    bc.RewardProposer(shardA, uA)
    bc.RewardProposer(shardB, uB)
}

// At end of each block
func (bc *BlockChain) FinalizeBlock() {
    // Update shadow price
    bc.justitiaMechanism.UpdateShadowPrice(
        bc.epochSubsidyTotal,
        bc.config.MaxInflation,
    )
}

// At start of new epoch
func (bc *BlockChain) StartNewEpoch() {
    bc.justitiaMechanism.ResetEpoch()
    bc.epochSubsidyTotal = big.NewInt(0)
}
```

## Behavior Analysis

### Scenario 1: Under Budget

```
TotalSubsidy = 2 ETH
Limit = 5 ETH
Violation = -3 ETH (under budget)

Lambda_new = 1.0 + 0.01 * (-3/5) = 1.0 - 0.006 = 0.994
Lambda_new = max(0.994, 1.0) = 1.0 (clamped to MinLambda)

Result: Subsidies remain at normal levels
```

### Scenario 2: At Budget

```
TotalSubsidy = 5 ETH
Limit = 5 ETH
Violation = 0 ETH

Lambda_new = 1.0 + 0.01 * 0 = 1.0

Result: Subsidies stable
```

### Scenario 3: Over Budget

```
TotalSubsidy = 6 ETH
Limit = 5 ETH
Violation = 1 ETH (20% over)

Lambda_new = 1.0 + 0.01 * (1/5) = 1.0 + 0.002 = 1.002

Result: Subsidies slightly reduced for next block
```

### Scenario 4: Significantly Over Budget

```
TotalSubsidy = 10 ETH
Limit = 5 ETH
Violation = 5 ETH (100% over)

Lambda_new = 1.0 + 0.01 * (5/5) = 1.0 + 0.01 = 1.01

After multiple blocks of overspending:
Lambda → 2.0, 3.0, ... up to MaxLambda (10.0)

Result: Subsidies reduced by up to 10x
```

## Congestion Factor Examples

With `CongestionExp = 2.0` (quadratic):

| Queue Length | Utilization | Congestion Factor | Effect |
|--------------|-------------|-------------------|--------|
| 100/1000     | 0.1         | 0.01              | Very low subsidy |
| 300/1000     | 0.3         | 0.09              | Low subsidy |
| 500/1000     | 0.5         | 0.25              | Moderate subsidy |
| 700/1000     | 0.7         | 0.49              | High subsidy |
| 900/1000     | 0.9         | 0.81              | Very high subsidy |

**Quadratic preference** means congested shards get disproportionately higher subsidies.

## Tuning Guidelines

### Learning Rate (Alpha)

- **Higher (0.05-0.1)**: Fast adaptation, may oscillate
- **Lower (0.001-0.01)**: Slow adaptation, more stable
- **Recommended**: 0.01 for typical workloads

### Window Size

- Should match actual queue capacity
- **Too small**: Overestimates congestion
- **Too large**: Underestimates congestion
- **Recommended**: Set to actual `TxPool` capacity

### Congestion Exponent

- **1.0**: Linear preference (proportional)
- **2.0**: Quadratic preference (strong bias to congested)
- **3.0**: Cubic preference (very strong bias)
- **Recommended**: 2.0 for balanced behavior

### Lambda Bounds

- **MinLambda**: Should be ≥ 1.0 (prevents negative subsidies)
- **MaxLambda**: Controls maximum reduction (10.0 = 10x reduction)
- **Recommended**: MinLambda=1.0, MaxLambda=10.0

## Comparison with PID

| Feature | Lagrangian | PID |
|---------|-----------|-----|
| **Objective** | Maximize throughput | Minimize queue error |
| **Constraint** | Global inflation limit | Target utilization |
| **Scope** | System-wide optimization | Per-shard control |
| **State** | Shadow price (λ) | Integral, derivative |
| **Update** | Per block/epoch | Continuous |
| **Budget** | Enforced via λ | Not enforced |

**When to use Lagrangian:**
- Need strict budget control
- Multi-shard coordination
- Economic constraints important

**When to use PID:**
- Focus on queue stability
- Per-shard optimization
- No budget constraints

## Monitoring

### Key Metrics to Track

```go
// Shadow price evolution
lambda := mechanism.GetShadowPrice()
fmt.Printf("Current Lambda: %.4f\n", lambda)

// Budget utilization
utilization := float64(totalSubsidy) / float64(inflationLimit)
fmt.Printf("Budget Utilization: %.2f%%\n", utilization * 100)

// Average subsidy per transaction
avgSubsidy := totalSubsidy / numTransactions
fmt.Printf("Avg Subsidy: %s wei\n", avgSubsidy)
```

### Warning Signs

- **Lambda → MaxLambda**: Consistently over budget, increase limit or reduce demand
- **Lambda → MinLambda**: Under-utilizing budget, can increase subsidies
- **Rapid Lambda oscillation**: Alpha too high, reduce learning rate

## Advanced Features

### Adaptive Window Size

```go
// Dynamically adjust based on actual capacity
params.WindowSize = float64(txpool.GetCapacity())
```

### Multi-Shard Coordination

```go
// Track subsidies across all shard pairs
totalSubsidy := big.NewInt(0)
for _, shardPair := range allPairs {
    R := mechanism.CalculateRAB(EA, EB, metrics)
    totalSubsidy.Add(totalSubsidy, R)
}
mechanism.UpdateShadowPrice(totalSubsidy, globalLimit)
```

### Epoch-Based Budgets

```go
// Different limits for different epochs
epochLimit := getEpochBudget(currentEpoch)
mechanism.UpdateShadowPrice(totalSubsidy, epochLimit)
```

## Testing

Run the examples:

```go
justitia.ExampleLagrangianUsage()
justitia.ExampleLagrangianEpochManagement()
justitia.ExampleLagrangianVsPID()
```

Expected behavior:
- Shadow price increases when over budget
- Subsidies decrease as Lambda increases
- Budget constraint is enforced over time

## Future Enhancements

1. **Adaptive Alpha**: Auto-tune learning rate based on volatility
2. **Multi-Objective**: Balance throughput and latency
3. **Predictive Lambda**: Use historical data to anticipate congestion
4. **Hierarchical Budgets**: Per-shard and global constraints
