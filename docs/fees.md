# Justitia Fee Computation Guide

## Overview

This document explains how proposer fees are computed in the Justitia system, ensuring accurate incentive calculations for both intra-shard (ITX) and cross-shard (CTX) transactions.

## Core Principle

**The proposer fee is the amount actually paid to the block proposer, NOT the total amount paid by the user.**

This distinction is critical for:
- **Legacy transactions (EIP-2718 type 0/1)**: Proposer receives `gasUsed * gasPrice`
- **EIP-1559 transactions (type 2)**: Proposer receives only the **tip** (priority fee), NOT the base fee (which is burned)

## Fee Computation

### The Single Source of Truth

The **ONLY** function for computing proposer fees is:

```go
ingest/ethcsv.ComputeProposerFee(r TxRow) *big.Int
```

This function must be used for ALL fee calculations. No other code should compute fees from raw CSV data.

### Implementation Details

#### Legacy Transactions (Type 0, 1)

For pre-EIP-1559 transactions:

```
proposerFee = gasUsed * gasPrice
```

**Example:**
```
gasUsed    = 21,000
gasPrice   = 20 gwei
proposerFee = 21,000 * 20 gwei = 420,000 gwei = 0.00042 ETH
```

#### EIP-1559 Transactions (Type 2)

For EIP-1559 transactions, the proposer only receives the tip:

```
effectiveGasPrice = min(maxFeePerGas, baseFeePerGas + maxPriorityFeePerGas)
tip = max(effectiveGasPrice - baseFeePerGas, 0)
proposerFee = gasUsed * tip
```

**Example 1: Normal case**
```
gasUsed              = 21,000
baseFeePerGas        = 30 gwei
maxFeePerGas         = 100 gwei
maxPriorityFeePerGas = 2 gwei

effectiveGasPrice = min(100, 30 + 2) = 32 gwei
tip = 32 - 30 = 2 gwei
proposerFee = 21,000 * 2 gwei = 42,000 gwei
```

**Example 2: maxFeePerGas limits effective price**
```
gasUsed              = 21,000
baseFeePerGas        = 30 gwei
maxFeePerGas         = 31 gwei
maxPriorityFeePerGas = 2 gwei

effectiveGasPrice = min(31, 30 + 2) = 31 gwei
tip = 31 - 30 = 1 gwei
proposerFee = 21,000 * 1 gwei = 21,000 gwei
```

**Example 3: maxFeePerGas below baseFee**
```
gasUsed              = 21,000
baseFeePerGas        = 30 gwei
maxFeePerGas         = 29 gwei
maxPriorityFeePerGas = 2 gwei

effectiveGasPrice = min(29, 30 + 2) = 29 gwei
tip = 29 - 30 = -1 gwei → clamped to 0
proposerFee = 0
```

#### EIP-4844 Blob Transactions (Type 3)

Blob transactions contain two fee components:

**1. Regular execution gas fees (calculated per EIP-1559):**
```
effectiveGasPrice = min(maxFeePerGas, baseFeePerGas + maxPriorityFeePerGas)
tip = max(effectiveGasPrice - baseFeePerGas, 0)
proposerFee = gasUsed * tip
```

**2. Blob gas fees (if data available):**
- Blob base fee: burned (like EIP-1559 base fee)
- Blob tip: requires `maxFeePerBlobGas` and `maxPriorityFeePerBlobGas` fields
- Since these fields are typically not in the dataset, blob tips are not included

**Important:** Type 3 transactions' regular execution gas still follows EIP-1559 rules for proposer fees (tip). **Do NOT** simply return 0.

**Example:**
```
gasUsed              = 21,000
baseFeePerGas        = 30 gwei
maxFeePerGas         = 100 gwei
maxPriorityFeePerGas = 2 gwei
blobGasUsed          = 131,072 (blob portion, proposer tip not included)

Execution gas tip = 2 gwei
proposerFee = 21,000 * 2 gwei = 42,000 gwei
```

### Failed Transactions

**Important:** Failed transactions (where `isError = true`) still consume gas and pay fees to the proposer. The fee computation is **identical** whether the transaction succeeded or failed.

```go
// Failed tx still pays fee
if r.IsError {
    // Fee computation is unchanged
    fee = ComputeProposerFee(r)  // NOT zero!
}
```

## Integration with Justitia

### Transaction Structure

Each transaction stores its proposer fee as `*big.Int`:

```go
type Transaction struct {
    FeeToProposer *big.Int  // f_AB for CTX, f for ITX
    SubsidyR      *big.Int  // R_AB subsidy
    UtilityA      *big.Int  // uA for source shard
    UtilityB      *big.Int  // uB for destination shard
    // ...
}
```

### Fee Expectation Tracking

The `fees/expectation.Tracker` maintains rolling averages E(f_s) for each shard:

```go
type Tracker struct {
    itxWindows map[int][]*big.Int  // Per-shard ITX fee history
    avg        map[int]*big.Int    // Current E(f_s)
}
```

**Critical Rule:** Only **ITX** fees are tracked in E(f_s). Cross-shard transaction fees are **excluded** to avoid circular dependencies.

#### Updating E(f_s)

When a block is finalized:

```go
// Extract ONLY ITX fees from the block
itxFees := []*big.Int{}
for _, tx := range block.Transactions {
    if !tx.IsCrossShard {
        itxFees = append(itxFees, tx.FeeToProposer)
    }
}

// Update tracker (CTX fees NOT included)
feeTracker.OnBlockFinalized(shardID, itxFees)
```

The tracker:
1. Computes the average fee for this block
2. Adds it to a sliding window of size K (default 16)
3. Recomputes E(f_s) as the average of the window

### Subsidy Computation

The subsidy R_AB is computed using **ONLY** the shard averages, **NEVER** the transaction fee:

```go
func RAB(mode SubsidyMode, EA, EB *big.Int, customF func(*big.Int, *big.Int) *big.Int) *big.Int
```

**Modes:**
- `SubsidyNone`: R = 0
- `SubsidyDestAvg`: R = E(f_B) ← destination shard average
- `SubsidySumAvg`: R = E(f_A) + E(f_B)
- `SubsidyCustom`: R = customF(E(f_A), E(f_B))

**Critical:** Notice that `f_AB` (the transaction fee) is **NOT** a parameter. This is by design to prevent circular dependencies and manipulation.

### Shapley Value Split

Given a CTX from shard A to shard B:

```
uA = (f_AB + R + EA - EB) / 2
uB = (f_AB + R + EB - EA) / 2
```

Where:
- `f_AB` = proposer fee (from `ComputeProposerFee`)
- `R` = subsidy (from `RAB`)
- `EA` = E(f_A) (from tracker)
- `EB` = E(f_B) (from tracker)

**Invariant:** `uA + uB = f_AB + R` (total rewards are conserved)

If either utility would be negative, it's clamped to 0 and the remainder goes to the other shard, preserving the invariant.

### Transaction Selection

The scheduler uses fees to prioritize transactions:

**For ITX:**
```
score = FeeToProposer
```

**For CTX:**
```
score = u(local_shard)  // uA if source, uB if destination
```

**Two-phase selection:**

1. **Phase 1 (high priority):**
   - ITX with `fee >= E(f_s)`
   - CTX in Case1 (`uA >= EA`)

2. **Phase 2 (remaining space):**
   - ITX with `fee < E(f_s)`
   - CTX in Case3 (`EA - EB < uA < EA`)

**Excluded:**
- CTX in Case2 (`uA <= EA - EB`)

### Settlement

When a CTX completes both phases:

1. **Source shard (A)** includes CTX → create `Pending` entry
2. **Destination shard (B)** includes CTX' → settle

Settlement distributes:
- `uA` to source shard proposer
- `uB` to destination shard proposer

The subsidy `R` is minted from the issuance, NOT taken from the user's fee.

## Data Types

All fee-related values use `*big.Int` to handle Ethereum's wei-scale values without overflow:

```go
// Example: 1 ETH = 10^18 wei
oneETH := new(big.Int).Exp(big.NewInt(10), big.NewInt(18), nil)

// Example: 20 gwei gas price
gasPrice := big.NewInt(20_000_000_000)
```

## Testing

### Unit Tests

#### Fee Computation (`ingest/ethcsv/row_test.go`)

Tests verify:
- Legacy transaction fees: `gasUsed * gasPrice`
- EIP-1559 tip calculation with various edge cases
- Failed transactions still pay fees
- Blob transactions return 0 without tip data

#### Shapley Split (`incentive/justitia/justitia_test.go`)

Tests verify:
- Conservation: `uA + uB = f_AB + R`
- Symmetry: Swapping shards swaps utilities
- Non-negativity: No negative utilities after clamping

#### Fee Tracking (`fees/expectation/avg_test.go`)

Tests verify:
- Sliding window behavior
- ITX-only tracking (CTX excluded)
- Multi-shard independence
- Thread safety

### Integration Tests

`test/integration/justitia_fee_integration_test.go` verifies:

1. **End-to-end flow:**
   - CSV ingestion → fee computation → E(f_s) tracking → subsidy → split → settlement

2. **Subsidy modes:**
   - None vs DestAvg vs SumAvg produce different R values

3. **ITX-only averaging:**
   - CTX fees don't pollute E(f_s)

4. **R_AB independence:**
   - R_AB is the same regardless of f_AB value

## Common Pitfalls

### ❌ Wrong: Computing fees outside `ComputeProposerFee`

```go
// NEVER do this:
tx.FeeToProposer = csvRow.GasUsed * csvRow.GasPrice  // Wrong for EIP-1559!
```

### ✅ Correct: Always use `ComputeProposerFee`

```go
tx.FeeToProposer = ethcsv.ComputeProposerFee(csvRow)
```

### ❌ Wrong: Including baseFee in proposer revenue

```go
// NEVER include baseFee:
totalPaid := gasUsed * (baseFee + tip)
proposerFee := totalPaid  // Wrong! BaseFee is burned.
```

### ✅ Correct: Only the tip

```go
proposerFee := gasUsed * tip  // Correct!
```

### ❌ Wrong: Including CTX fees in E(f_s)

```go
// NEVER do this:
allFees := append(itxFees, ctxFees...)  // Wrong!
feeTracker.OnBlockFinalized(shard, allFees)
```

### ✅ Correct: ITX-only

```go
feeTracker.OnBlockFinalized(shard, itxFees)  // CTX excluded
```

### ❌ Wrong: Using f_AB in RAB

```go
// NEVER do this:
func RAB(mode SubsidyMode, fAB, EA, EB *big.Int) *big.Int {
    if mode == SubsidyCustom {
        return fAB  // Wrong! Creates circular dependency.
    }
    // ...
}
```

### ✅ Correct: RAB never sees f_AB

```go
func RAB(mode SubsidyMode, EA, EB *big.Int, customF ...) *big.Int {
    // No fAB parameter at all!
}
```

## Performance Considerations

### Big Integer Arithmetic

`*big.Int` operations are more expensive than native types but necessary for correctness:

- **Allocation:** Use `new(big.Int)` for new values, `.Set()` for copies
- **In-place operations:** Reuse existing big.Ints where possible
- **Comparisons:** Use `.Cmp()` not `==`

### Sliding Window

The fee tracker maintains O(K) history per shard:
- K = 16 blocks is recommended
- Memory: O(S * K) where S = number of shards

### Lock Contention

The fee tracker uses RWMutex for thread safety:
- Reads (`.GetAvgITXFee()`) can occur concurrently
- Writes (`.OnBlockFinalized()`) are serialized

## Configuration

### Justitia Parameters

```json
{
  "EnableJustitia": 1,
  "JustitiaSubsidyMode": 1,        // 0=None, 1=DestAvg, 2=SumAvg, 3=Custom, 4=ExtremeFixed
  "JustitiaWindowBlocks": 16,      // Sliding window size for E(f_s)
  "JustitiaGammaMin": 0,           // Min subsidy budget per block (0=unlimited)
  "JustitiaGammaMax": 0            // Max subsidy budget per block (0=unlimited)
}
```

### Recommended Settings

- **Production:** `JustitiaWindowBlocks = 16`, `JustitiaSubsidyMode = 1` (DestAvg)
- **Testing:** `JustitiaWindowBlocks = 4`, various modes for comparison
- **High volatility:** Increase window size to 32 for more stability
- **Low latency:** Decrease window size to 8 for faster adaptation

## Acceptance Criteria Checklist

Before merging any changes, verify:

- ✅ `ComputeProposerFee` is the **only** source of `Tx.FeeToProposer`
- ✅ EIP-1559 base fee is **never** counted as proposer revenue
- ✅ E(f_s) uses **ITX-only** fees from finalized blocks
- ✅ `R_AB` **never** reads `f_AB`
- ✅ Selection uses ITX fee and CTX utility scores
- ✅ Unit tests cover legacy, EIP-1559, and edge cases
- ✅ Integration tests verify end-to-end flow
- ✅ Conservation invariant: `uA + uB = f_AB + R`

## Further Reading

- **EIP-1559:** [ethereum.org/en/developers/docs/gas](https://ethereum.org/en/developers/docs/gas/)
- **EIP-4844:** [eips.ethereum.org/EIPS/eip-4844](https://eips.ethereum.org/EIPS/eip-4844)
- **Shapley Values:** Original Justitia paper
- **Go big.Int:** [pkg.go.dev/math/big](https://pkg.go.dev/math/big)

---

**Version:** 1.0  
**Last Updated:** 2025-11-03  
**Author:** Justitia Implementation Team

