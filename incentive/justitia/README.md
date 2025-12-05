# Justitia Incentive Mechanism

A comprehensive implementation of dynamic incentive mechanisms for cross-shard blockchain transactions.

## Overview

Justitia provides multiple subsidy calculation strategies to optimize cross-shard transaction (CTX) processing:

- **Static modes:** DestAvg, SumAvg, ExtremeFixed
- **Dynamic modes:** PID, Lagrangian, RL (Reinforcement Learning)

All modes use **Shapley value** for fair reward allocation between source and destination shards.

## Features

✅ **Multiple Subsidy Modes** - Choose the right strategy for your use case  
✅ **Dynamic Adaptation** - PID, Lagrangian, and RL modes adapt to blockchain state  
✅ **Budget Enforcement** - Lagrangian mode enforces global inflation constraints  
✅ **Learned Policies** - RL mode uses trained Q-Tables for optimal decisions  
✅ **Thread-Safe** - All mechanisms are safe for concurrent access  
✅ **Backward Compatible** - Stateless API still works for simple use cases  
✅ **Well-Documented** - Comprehensive docs and examples for each mode  

## Quick Start

### Installation

```go
import "blockEmulator/incentive/justitia"
```

### Basic Usage (Static Mode)

```go
// Create configuration
config := justitia.DefaultConfig()
config.Mode = justitia.SubsidyDestAvg

// Create mechanism
mechanism := justitia.NewMechanism(config)

// Calculate subsidy
EA := big.NewInt(1000000000000000) // 0.001 ETH
EB := big.NewInt(2000000000000000) // 0.002 ETH
metrics := txpool.GetMetrics()

R := mechanism.CalculateRAB(EA, EB, &metrics)

// Split rewards using Shapley value
fAB := tx.FeeToProposer
uA, uB := justitia.Split2(fAB, R, EA, EB)
```

### Dynamic Modes

#### PID Controller

```go
config := &justitia.Config{
    Mode: justitia.SubsidyPID,
    PIDParams: justitia.PIDParams{
        Kp: 1.5, Ki: 0.1, Kd: 0.05,
        TargetUtilization: 0.7,
        CapacityB: 1000.0,
        MinSubsidy: 0.0, MaxSubsidy: 5.0,
    },
}
mechanism := justitia.NewMechanism(config)
```

#### Lagrangian Optimization

```go
config := &justitia.Config{
    Mode: justitia.SubsidyLagrangian,
    LagrangianParams: justitia.LagrangianParams{
        Alpha: 0.01, WindowSize: 1000.0,
        MinLambda: 1.0, MaxLambda: 10.0,
        CongestionExp: 2.0,
    },
    MaxInflation: big.NewInt(5000000000000000000), // 5 ETH
}
mechanism := justitia.NewMechanism(config)

// Update shadow price after each block
mechanism.UpdateShadowPrice(totalSubsidy, inflationLimit)

// Reset at epoch boundaries
mechanism.ResetEpoch()
```

#### Reinforcement Learning

```go
config := &justitia.Config{
    Mode: justitia.SubsidyRL,
    RLParams: justitia.RLParams{
        QueueThresholds: []float64{250.0, 500.0, 750.0},
        InflationThreshold: 0.7,
        DefaultBeta: 1.0,
        MinBeta: 0.0, MaxBeta: 3.0,
    },
}
mechanism := justitia.NewMechanism(config)

// Optional: Load trained policy
err := mechanism.LoadPolicy("trained_policy.json")
```

## Subsidy Modes

### Static Modes

| Mode | Formula | Use Case |
|------|---------|----------|
| **None** | R = 0 | No subsidies |
| **DestAvg** | R = E(f_B) | Simple destination-based |
| **SumAvg** | R = E(f_A) + E(f_B) | Generous subsidies |
| **ExtremeFixed** | R = 1 ETH | Testing/debugging |

### Dynamic Modes

| Mode | Objective | Constraint | Complexity |
|------|-----------|------------|------------|
| **PID** | Minimize queue error | Target utilization | Low |
| **Lagrangian** | Maximize throughput | Global inflation limit | Medium |
| **RL** | Learn optimal policy | Learned from data | High |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Mechanism (Stateful)                │
│  - Config: Mode, Parameters                     │
│  - State: PID, Lagrangian, Q-Table              │
│  - Methods: CalculateRAB(), UpdateShadowPrice() │
└────────────────┬────────────────────────────────┘
                 │
                 ├─► PID Controller
                 │   - Integral, Derivative, Error
                 │   - Target: Queue utilization
                 │
                 ├─► Lagrangian Optimizer
                 │   - Shadow price (Lambda)
                 │   - Constraint: Inflation limit
                 │
                 └─► RL Policy
                     - Q-Table: State → Action
                     - Learned from reward function
```

## Documentation

- **[PID_IMPLEMENTATION.md](PID_IMPLEMENTATION.md)** - PID controller details
- **[LAGRANGIAN_IMPLEMENTATION.md](LAGRANGIAN_IMPLEMENTATION.md)** - Lagrangian optimization
- **[RL_IMPLEMENTATION.md](RL_IMPLEMENTATION.md)** - Reinforcement learning
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Blockchain integration

## Examples

- **[example_pid_usage.go](example_pid_usage.go)** - PID examples
- **[example_lagrangian_usage.go](example_lagrangian_usage.go)** - Lagrangian examples
- **[example_rl_usage.go](example_rl_usage.go)** - RL examples
- **[example_policy.json](example_policy.json)** - Sample Q-Table

## API Reference

### Core Types

```go
type Mechanism struct {
    config          *Config
    pidState        *PIDState
    lagrangianState *LagrangianState
    qTable          map[RLState]float64
}

type DynamicMetrics struct {
    QueueLengthA     int64
    QueueLengthB     int64
    AvgWaitTimeA     float64
    AvgWaitTimeB     float64
    CurrentInflation *big.Int
}
```

### Key Methods

```go
// Create mechanism
func NewMechanism(config *Config) *Mechanism

// Calculate subsidy (thread-safe)
func (m *Mechanism) CalculateRAB(EA, EB *big.Int, metrics *DynamicMetrics) *big.Int

// Shapley value split
func Split2(fAB, R, EA, EB *big.Int) (uA, uB *big.Int)

// Transaction classification
func Classify(uA, EA, EB *big.Int) Case

// Lagrangian-specific
func (m *Mechanism) UpdateShadowPrice(totalSubsidy, limit *big.Int)
func (m *Mechanism) ResetEpoch()
func (m *Mechanism) GetShadowPrice() float64

// RL-specific
func (m *Mechanism) LoadPolicy(filepath string) error
func (m *Mechanism) SavePolicy(filepath string) error
func (m *Mechanism) GetQTableSize() int
```

## Performance

### Computational Cost

| Operation | Time Complexity | Notes |
|-----------|-----------------|-------|
| CalculateRAB (PID) | O(1) | ~10 float ops |
| CalculateRAB (Lagrangian) | O(1) | ~5 float ops + pow() |
| CalculateRAB (RL) | O(1) | Map lookup |
| UpdateShadowPrice | O(1) | Float arithmetic |
| Split2 | O(1) | BigInt arithmetic |

### Memory Usage

| Component | Size | Notes |
|-----------|------|-------|
| PIDState | ~40 bytes | 3 floats + timestamp |
| LagrangianState | ~56 bytes | 1 float + big.Int + timestamps |
| Q-Table (RL) | ~128 bytes | 8 entries × 16 bytes |
| **Total per Mechanism** | **< 300 bytes** | Negligible overhead |

## Testing

Run examples:

```go
// PID
justitia.ExamplePIDUsage()

// Lagrangian
justitia.ExampleLagrangianUsage()
justitia.ExampleLagrangianEpochManagement()

// RL
justitia.ExampleRLUsage()
justitia.ExampleLoadPolicy()
```

## Comparison Matrix

| Feature | PID | Lagrangian | RL |
|---------|-----|------------|-----|
| **Training Required** | No | No | Yes (offline) |
| **Budget Enforcement** | No | Yes (hard) | Yes (soft) |
| **Adaptability** | Medium | Medium | High |
| **Interpretability** | High | High | Low |
| **Multi-Objective** | No | Yes | Yes |
| **Computational Cost** | Low | Low | Low |
| **Setup Complexity** | Low | Medium | High |

## When to Use Each Mode

### Use PID when:
- You want simple, interpretable control
- Target queue utilization is the primary goal
- No budget constraints needed
- Quick deployment is important

### Use Lagrangian when:
- Global inflation budget must be enforced
- System-wide optimization is needed
- Economic guarantees are important
- You understand shadow price dynamics

### Use RL when:
- You have historical data for training
- Multi-objective optimization is needed
- You can invest in offline training
- Black-box decisions are acceptable

## Configuration Examples

### Conservative (Low Subsidies)

```go
config := &justitia.Config{
    Mode: justitia.SubsidyPID,
    PIDParams: justitia.PIDParams{
        Kp: 1.0, Ki: 0.05, Kd: 0.02,
        TargetUtilization: 0.5,  // Low target
        MaxSubsidy: 2.0,          // Limited subsidy
    },
}
```

### Aggressive (High Subsidies)

```go
config := &justitia.Config{
    Mode: justitia.SubsidyLagrangian,
    LagrangianParams: justitia.LagrangianParams{
        Alpha: 0.02,              // Fast adaptation
        CongestionExp: 3.0,       // Cubic preference
        MaxLambda: 5.0,           // Less reduction
    },
    MaxInflation: big.NewInt(10000000000000000000), // 10 ETH
}
```

### Balanced (Default)

```go
config := justitia.DefaultConfig()
config.Mode = justitia.SubsidyRL
// Uses heuristic Q-Table with balanced policy
```

## Troubleshooting

### Issue: Subsidies too high

**Solution:** 
- PID: Reduce `Kp`, increase `TargetUtilization`
- Lagrangian: Reduce `MaxInflation`, increase `Alpha`
- RL: Retrain with higher inflation penalty

### Issue: Subsidies too low

**Solution:**
- PID: Increase `Kp`, `MaxSubsidy`
- Lagrangian: Increase `MaxInflation`, reduce `Alpha`
- RL: Retrain with lower inflation penalty

### Issue: Subsidies oscillate

**Solution:**
- PID: Reduce `Kp`, increase `Kd`
- Lagrangian: Reduce `Alpha`
- RL: Check state discretization thresholds

## Contributing

When adding new subsidy modes:

1. Add constant to `SubsidyMode` enum
2. Update `String()` method
3. Add parameters to `Config` struct
4. Implement calculation function
5. Update `calculateRABInternal()` switch
6. Add tests and documentation

## License

[Your License Here]

## Citation

If you use Justitia in your research, please cite:

```bibtex
@article{justitia2024,
  title={Justitia: Fair Incentive Mechanisms for Cross-Shard Transactions},
  author={[Your Name]},
  journal={[Conference/Journal]},
  year={2024}
}
```

## Contact

For questions or issues, please contact [your email] or open an issue on GitHub.
