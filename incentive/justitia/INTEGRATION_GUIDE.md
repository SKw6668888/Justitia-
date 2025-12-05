# Justitia Integration Guide

## Overview

This guide shows how to integrate the Justitia incentive mechanism (with PID and Lagrangian support) into your blockchain implementation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Blockchain Layer                      │
│  (chain/blockchain.go or equivalent)                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Creates & Manages
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Justitia Mechanism                          │
│  - Mode: PID / Lagrangian / DestAvg / etc.              │
│  - State: PIDState, LagrangianState                     │
│  - Methods: CalculateRAB(), UpdateShadowPrice()         │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Reads Metrics
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Transaction Pool                            │
│  (core/txpool_justitia.go)                              │
│  - Method: GetMetrics() → DynamicMetrics                │
└─────────────────────────────────────────────────────────┘
```

## Step-by-Step Integration

### Step 1: Initialize Mechanism in Blockchain

Add to your blockchain struct:

```go
// In chain/blockchain.go or equivalent
type BlockChain struct {
    // ... existing fields ...
    
    // Justitia mechanism
    justitiaMechanism *justitia.Mechanism
    
    // Tracking for Lagrangian mode
    epochSubsidyTotal *big.Int
    epochStartBlock   uint64
}

// Initialize in constructor
func NewBlockChain(config *Config) *BlockChain {
    // Create Justitia configuration
    justitiaConfig := &justitia.Config{
        Mode: justitia.SubsidyLagrangian, // or SubsidyPID
        LagrangianParams: justitia.LagrangianParams{
            Alpha:         0.01,
            WindowSize:    1000.0,
            MinLambda:     1.0,
            MaxLambda:     10.0,
            CongestionExp: 2.0,
        },
        MaxInflation: big.NewInt(5000000000000000000), // 5 ETH per epoch
    }
    
    return &BlockChain{
        // ... existing initialization ...
        justitiaMechanism: justitia.NewMechanism(justitiaConfig),
        epochSubsidyTotal: big.NewInt(0),
        epochStartBlock:   0,
    }
}
```

### Step 2: Calculate Subsidy for Cross-Shard Transactions

When processing a CTX:

```go
func (bc *BlockChain) ProcessCrossShard(tx *Transaction, shardA, shardB int) error {
    // Get average fees for both shards
    EA := bc.GetAverageFee(shardA) // E(f_A)
    EB := bc.GetAverageFee(shardB) // E(f_B)
    
    // Get current metrics from destination shard's txpool
    metrics := bc.GetTxPool(shardB).GetMetrics()
    
    // Add current inflation to metrics
    metrics.CurrentInflation = bc.epochSubsidyTotal
    
    // Calculate subsidy using Justitia mechanism
    R := bc.justitiaMechanism.CalculateRAB(EA, EB, &metrics)
    
    // Track total subsidy issued
    bc.epochSubsidyTotal.Add(bc.epochSubsidyTotal, R)
    
    // Calculate utilities using Shapley value split
    fAB := tx.FeeToProposer
    uA, uB := justitia.Split2(fAB, R, EA, EB)
    
    // Classify transaction for scheduling
    txCase := justitia.Classify(uA, EA, EB)
    
    // Reward proposers
    bc.RewardProposer(shardA, uA)
    bc.RewardProposer(shardB, uB)
    
    // Log for monitoring
    log.Printf("CTX %s: R=%s, uA=%s, uB=%s, Case=%s", 
        tx.Hash, R, uA, uB, txCase)
    
    return nil
}
```

### Step 3: Update Shadow Price (Lagrangian Mode Only)

At the end of each block:

```go
func (bc *BlockChain) FinalizeBlock(block *Block) error {
    // ... existing finalization logic ...
    
    // Update Lagrangian shadow price
    if bc.justitiaMechanism != nil {
        inflationLimit := bc.config.MaxInflation
        bc.justitiaMechanism.UpdateShadowPrice(
            bc.epochSubsidyTotal,
            inflationLimit,
        )
    }
    
    return nil
}
```

### Step 4: Epoch Management (Lagrangian Mode)

At epoch boundaries:

```go
func (bc *BlockChain) StartNewEpoch(epochNum uint64) {
    log.Printf("Starting Epoch %d", epochNum)
    
    // Log previous epoch stats
    log.Printf("Previous Epoch Total Subsidy: %s wei", 
        bc.epochSubsidyTotal.String())
    log.Printf("Shadow Price: %.4f", 
        bc.justitiaMechanism.GetShadowPrice())
    
    // Reset Lagrangian state for new epoch
    bc.justitiaMechanism.ResetEpoch()
    bc.epochSubsidyTotal = big.NewInt(0)
    bc.epochStartBlock = bc.CurrentBlock().Number
}
```

### Step 5: Monitoring and Metrics

Add monitoring endpoints:

```go
// Get current Justitia stats
func (bc *BlockChain) GetJustitiaStats() map[string]interface{} {
    return map[string]interface{}{
        "mode":              bc.justitiaMechanism.config.Mode.String(),
        "shadow_price":      bc.justitiaMechanism.GetShadowPrice(),
        "epoch_subsidy":     bc.epochSubsidyTotal.String(),
        "inflation_limit":   bc.config.MaxInflation.String(),
        "budget_utilization": float64(bc.epochSubsidyTotal.Int64()) / 
                              float64(bc.config.MaxInflation.Int64()),
    }
}
```

## Mode-Specific Considerations

### PID Mode

**Advantages:**
- No epoch management needed
- Continuous adaptation
- Good for queue stability

**Integration:**
```go
config := &justitia.Config{
    Mode: justitia.SubsidyPID,
    PIDParams: justitia.PIDParams{
        Kp:                1.5,
        Ki:                0.1,
        Kd:                0.05,
        TargetUtilization: 0.7,
        CapacityB:         1000.0,
        MinSubsidy:        0.0,
        MaxSubsidy:        5.0,
    },
}
```

**No need for:**
- `UpdateShadowPrice()` calls
- Epoch management
- Budget tracking

### Lagrangian Mode

**Advantages:**
- Enforces global budget
- System-wide optimization
- Economic guarantees

**Integration:**
```go
config := &justitia.Config{
    Mode: justitia.SubsidyLagrangian,
    LagrangianParams: justitia.LagrangianParams{
        Alpha:         0.01,
        WindowSize:    1000.0,
        MinLambda:     1.0,
        MaxLambda:     10.0,
        CongestionExp: 2.0,
    },
    MaxInflation: big.NewInt(5000000000000000000),
}
```

**Required:**
- `UpdateShadowPrice()` after each block
- `ResetEpoch()` at epoch boundaries
- Track `epochSubsidyTotal`

## Testing Integration

### Unit Test Example

```go
func TestJustitiaIntegration(t *testing.T) {
    // Create blockchain with Justitia
    bc := NewBlockChain(testConfig)
    
    // Create test transaction
    tx := &Transaction{
        From:          shardA,
        To:            shardB,
        FeeToProposer: big.NewInt(3000000000000000),
    }
    
    // Process CTX
    err := bc.ProcessCrossShard(tx, 0, 1)
    assert.NoError(t, err)
    
    // Verify subsidy was calculated
    assert.True(t, bc.epochSubsidyTotal.Sign() > 0)
    
    // Verify shadow price updated (Lagrangian mode)
    lambda := bc.justitiaMechanism.GetShadowPrice()
    assert.True(t, lambda >= 1.0)
}
```

### Integration Test Example

```go
func TestMultiBlockScenario(t *testing.T) {
    bc := NewBlockChain(testConfig)
    
    // Simulate 100 blocks with varying congestion
    for i := 0; i < 100; i++ {
        // Create block with CTXs
        block := createTestBlock(i)
        
        // Process all CTXs
        for _, tx := range block.CrossShardTxs {
            bc.ProcessCrossShard(tx, tx.From, tx.To)
        }
        
        // Finalize block
        bc.FinalizeBlock(block)
        
        // Check budget constraint (Lagrangian)
        if i > 0 && i % 10 == 0 {
            utilization := float64(bc.epochSubsidyTotal.Int64()) / 
                          float64(bc.config.MaxInflation.Int64())
            t.Logf("Block %d: Budget utilization: %.2f%%", i, utilization*100)
        }
    }
    
    // Verify budget was respected
    assert.True(t, bc.epochSubsidyTotal.Cmp(bc.config.MaxInflation) <= 0)
}
```

## Performance Considerations

### Thread Safety

The `Mechanism` struct is thread-safe:
- All methods use mutex locks
- Safe for concurrent calls from multiple goroutines

### Memory Usage

- **PID State**: ~40 bytes (3 floats + timestamp)
- **Lagrangian State**: ~56 bytes (1 float + big.Int + 2 timestamps)
- **Total per Mechanism**: < 100 bytes

### Computational Cost

Per `CalculateRAB()` call:
- **PID**: ~10 floating-point operations
- **Lagrangian**: ~5 floating-point operations + 1 pow()
- **Negligible** compared to transaction processing

## Migration from Static Subsidy

### Before (Static)

```go
// Old code
R := justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil, nil)
uA, uB := justitia.Split2(fAB, R, EA, EB)
```

### After (Dynamic)

```go
// New code
metrics := txpool.GetMetrics()
R := mechanism.CalculateRAB(EA, EB, &metrics)
uA, uB := justitia.Split2(fAB, R, EA, EB)
```

**Backward compatibility:** Old static modes still work!

## Troubleshooting

### Issue: Shadow price always at MinLambda

**Cause:** Under-utilizing budget  
**Solution:** Increase `MaxInflation` or reduce `Alpha`

### Issue: Shadow price always at MaxLambda

**Cause:** Consistently over budget  
**Solution:** Increase `MaxInflation` or reduce transaction load

### Issue: Subsidies too volatile

**Cause:** `Alpha` too high (Lagrangian) or `Kp` too high (PID)  
**Solution:** Reduce learning rate / gains

### Issue: Subsidies not adapting

**Cause:** `Alpha` too low or metrics not updating  
**Solution:** Increase `Alpha` or verify `GetMetrics()` returns current data

## Best Practices

1. **Start with defaults:** Use `DefaultConfig()` and tune incrementally
2. **Monitor shadow price:** Track λ evolution to understand system behavior
3. **Log subsidy stats:** Record R, uA, uB for each CTX for analysis
4. **Test under load:** Verify behavior with high transaction volume
5. **Epoch length:** Choose epoch length that balances responsiveness and stability
6. **Budget setting:** Set `MaxInflation` based on economic model and security requirements

## Example Configuration Files

### config.json (Lagrangian)

```json
{
  "justitia": {
    "mode": "Lagrangian",
    "max_inflation_wei": "5000000000000000000",
    "lagrangian": {
      "alpha": 0.01,
      "window_size": 1000.0,
      "min_lambda": 1.0,
      "max_lambda": 10.0,
      "congestion_exp": 2.0
    }
  }
}
```

### config.json (PID)

```json
{
  "justitia": {
    "mode": "PID",
    "pid": {
      "kp": 1.5,
      "ki": 0.1,
      "kd": 0.05,
      "target_utilization": 0.7,
      "capacity_b": 1000.0,
      "min_subsidy": 0.0,
      "max_subsidy": 5.0
    }
  }
}
```

## Next Steps

1. Implement the integration in your blockchain
2. Run unit tests to verify correctness
3. Run integration tests with realistic workloads
4. Monitor metrics in production
5. Tune parameters based on observed behavior
6. Consider implementing RL mode for advanced optimization
