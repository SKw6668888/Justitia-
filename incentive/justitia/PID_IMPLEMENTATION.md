# PID Control Mechanism Implementation

## Overview

The PID (Proportional-Integral-Derivative) control mechanism dynamically adjusts the subsidy `R_AB` to optimize cross-shard transaction processing by minimizing queue congestion in the destination shard.

## Architecture

### Key Components

1. **`PIDState`** - Holds the internal state of the PID controller:
   - `Integral`: Accumulated integral term
   - `PrevError`: Previous error for derivative calculation
   - `LastUpdate`: Timestamp of last update

2. **`PIDParams`** - Configuration parameters:
   - `Kp`: Proportional gain (default: 1.5)
   - `Ki`: Integral gain (default: 0.1)
   - `Kd`: Derivative gain (default: 0.05)
   - `TargetUtilization`: Target queue utilization (default: 0.7 = 70%)
   - `CapacityB`: Destination shard queue capacity
   - `MinSubsidy`: Minimum subsidy multiplier (default: 0.0)
   - `MaxSubsidy`: Maximum subsidy multiplier (default: 5.0)

3. **`Mechanism`** - Stateful wrapper that maintains PID state across calls:
   - Thread-safe with mutex protection
   - Holds configuration and PID state
   - Provides `CalculateRAB()` method

## PID Algorithm

### Error Signal
```
error(t) = currentUtilization - targetUtilization
where:
  currentUtilization = QueueLengthB / CapacityB
```

### PID Output
```
output(t) = Kp * error(t) + Ki * integral(t) + Kd * derivative(t)

where:
  integral(t) = integral(t-1) + error(t) * dt
  derivative(t) = (error(t) - error(t-1)) / dt
```

### Subsidy Calculation
```
multiplier = 1.0 + output(t)
multiplier = clamp(multiplier, MinSubsidy, MaxSubsidy)
R_AB = EB * multiplier
```

## Usage

### Basic Usage (Stateful)

```go
import "blockEmulator/incentive/justitia"

// Create configuration
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

// Create mechanism (maintains state)
mechanism := justitia.NewMechanism(config)

// Calculate subsidy for each block
for blockNum := 1; blockNum <= 100; blockNum++ {
    // Get current metrics from txpool
    metrics := txpool.GetMetrics()
    
    // Calculate subsidy
    R := mechanism.CalculateRAB(EA, EB, &metrics)
    
    // Use subsidy for Shapley split
    uA, uB := justitia.Split2(fAB, R, EA, EB)
}
```

### Backward Compatibility (Stateless)

```go
// Old stateless API still works for non-PID modes
R := justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil, nil)

// PID mode falls back to DestAvg in stateless mode
R := justitia.RAB(justitia.SubsidyPID, EA, EB, metrics, nil)
// WARNING: This does NOT maintain PID state!
```

## Behavior Analysis

### Low Queue Utilization (< 70%)
- **Error**: Negative
- **Effect**: Subsidy decreases (multiplier < 1.0)
- **Result**: Lower incentive for CTX, allowing queue to fill

### Target Utilization (≈ 70%)
- **Error**: Near zero
- **Effect**: Subsidy stable (multiplier ≈ 1.0)
- **Result**: Equilibrium maintained

### High Queue Utilization (> 70%)
- **Error**: Positive
- **Effect**: Subsidy increases (multiplier > 1.0)
- **Result**: Higher incentive for CTX, encouraging processing

### Extreme Congestion (> 90%)
- **Error**: Large positive
- **Effect**: Subsidy maximized (multiplier → MaxSubsidy)
- **Result**: Maximum incentive to clear backlog

## Anti-Windup Protection

The integral term is clamped to prevent windup:
```go
maxIntegral := 10.0
if state.Integral > maxIntegral {
    state.Integral = maxIntegral
} else if state.Integral < -maxIntegral {
    state.Integral = -maxIntegral
}
```

## Thread Safety

The `Mechanism` struct is thread-safe:
- Uses `sync.Mutex` to protect PID state
- Safe for concurrent calls from multiple goroutines
- Lock is held only during calculation

## Tuning Guidelines

### Proportional Gain (Kp)
- **Higher**: Faster response, may oscillate
- **Lower**: Slower response, more stable
- **Recommended**: 1.0 - 2.0

### Integral Gain (Ki)
- **Higher**: Eliminates steady-state error faster, may cause overshoot
- **Lower**: Slower convergence, more stable
- **Recommended**: 0.05 - 0.2

### Derivative Gain (Kd)
- **Higher**: Dampens oscillations, may amplify noise
- **Lower**: Less damping
- **Recommended**: 0.01 - 0.1

### Target Utilization
- **Higher (0.8-0.9)**: More aggressive queue filling
- **Lower (0.5-0.6)**: More conservative, lower latency
- **Recommended**: 0.6 - 0.8

## Migration Guide

### From Static Subsidy to PID

**Before:**
```go
R := justitia.RAB(justitia.SubsidyDestAvg, EA, EB, nil, nil)
```

**After:**
```go
// One-time setup
config := justitia.DefaultConfig()
config.Mode = justitia.SubsidyPID
mechanism := justitia.NewMechanism(config)

// Per-block calculation
metrics := txpool.GetMetrics()
R := mechanism.CalculateRAB(EA, EB, &metrics)
```

## Testing

Run the example:
```go
justitia.ExamplePIDUsage()
```

Expected output shows subsidy adapting to queue utilization:
- Low utilization → Lower subsidy
- Target utilization → Stable subsidy
- High utilization → Higher subsidy

## Future Enhancements

1. **Adaptive Tuning**: Auto-tune Kp, Ki, Kd based on system behavior
2. **Multi-Shard PID**: Coordinate subsidies across multiple shard pairs
3. **Inflation Limits**: Integrate with `MaxInflation` budget constraints
4. **Metrics Logging**: Track PID performance over time
