# Justitia 跨分片激励机制实现文档

## 概述

Justitia 是一个为跨分片交易（Cross-Shard Transactions, CTX）设计的激励机制，旨在通过动态补贴和公平的奖励分配，提高跨分片交易的处理优先级，从而减少其确认延迟。本文档详细介绍了 Justitia 在 BlockEmulator 中的完整实现。

## 核心思想

### 问题背景

在分片区块链系统中，跨分片交易（CTX）需要在两个分片中执行：
- **源分片（Shard A）**：发送者所在分片，执行第一阶段（Relay1）
- **目标分片（Shard B）**：接收者所在分片，执行第二阶段（Relay2）

传统的 FIFO（先进先出）机制下，CTX 往往因为优先级较低而面临较长的队列延迟。

### Justitia 解决方案

Justitia 通过以下三个核心机制解决这一问题：

1. **动态补贴（Dynamic Subsidy）**：为 CTX 提供补贴 R_AB，使其在交易池中更具竞争力
2. **Shapley 值分配**：公平地将总奖励（费用 + 补贴）分配给源分片和目标分片的提议者
3. **三阶段分类决策**：源分片根据自身效用对 CTX 进行优先级分类

## 架构设计

### 模块结构

```
blockEmulator/
├── fees/expectation/          # 费用期望追踪模块
│   ├── avg.go                 # 滚动平均费用追踪器
│   └── avg_test.go           # 单元测试
├── incentive/justitia/        # Justitia 激励机制核心
│   ├── justitia.go           # 补贴模式、Shapley 分配、分类决策
│   └── justitia_test.go      # 单元测试
├── crossshard/pending/        # 待结算账本
│   ├── ledger.go             # 跨分片奖励结算管理
│   └── ledger_test.go        # 单元测试
├── txpool/scheduler/          # 交易调度器
│   └── select.go             # 基于 Justitia 的交易选择算法
├── economics/subsidy_budget/  # 补贴预算控制（可选）
│   ├── budget.go             # 每区块补贴上下限
│   └── budget_test.go        # 单元测试
├── utils/                     # 工具函数
│   ├── utils_shard.go        # 分片映射（确定性哈希）
│   └── utils_shard_test.go   # 单元测试
├── core/
│   └── transaction.go        # 扩展的交易结构
└── test/integration/          # 集成测试
    └── justitia_integration_test.go
```

## 详细实现

### 1. 费用期望追踪（fees/expectation）

#### 功能
追踪每个分片的滚动平均 ITX（分片内交易）费用 E(f_s)。

#### 核心数据结构
```go
type Tracker struct {
    WindowSize int                        // 滑动窗口大小（区块数）
    mu         sync.RWMutex              // 并发保护
    itxWindows map[int][]uint64          // 每个分片的历史区块平均费用
    blockCount map[int]int               // 每个分片处理的区块数
    avg        map[int]uint64            // 每个分片的当前平均费用 E(f_s)
}
```

#### 关键方法

**OnBlockFinalized(shardID int, itxFeesInBlock []uint64)**
- 当一个区块最终确认时调用
- 仅接收该区块中 ITX 的提议者费用
- 计算该区块的平均费用并添加到滑动窗口
- 维护窗口大小（默认 16 个区块）
- 重新计算 E(f_s)

**GetAvgITXFee(shardID int) uint64**
- 返回指定分片的当前滚动平均费用
- 线程安全

#### 重要特性
- **仅追踪 ITX**：跨分片交易的费用不计入平均值，避免循环依赖
- **滑动窗口**：保持最近 K 个区块（默认 K=16），自动丢弃旧数据
- **线程安全**：使用读写锁保护并发访问
- **启动阶段**：在收集到足够数据前，返回 0 或使用全局中位数初始化

### 2. Justitia 激励核心（incentive/justitia）

#### 补贴模式（SubsidyMode）

定义了四种补贴计算模式：

```go
const (
    SubsidyNone           // R = 0（无补贴）
    SubsidyDestAvg        // R = E(f_B)（目标分片平均费用，默认）
    SubsidySumAvg         // R = E(f_A) + E(f_B)（两分片平均之和）
    SubsidyCustom         // R = F(E(f_A), E(f_B))（自定义函数）
    SubsidyExtremeFixed   // R = 1 ETH/CTX（极端固定补贴）
)
```

**RAB 函数**
```go
func RAB(mode SubsidyMode, EA, EB uint64, customF func(uint64, uint64) uint64) uint64
```
- 计算补贴 R_AB
- **关键约束**：从不使用交易费用 f_AB，仅依赖分片平均费用
- 返回补贴金额

#### Shapley 值分配

**Split2 函数**
```go
func Split2(fAB, R, EA, EB uint64) (uA, uB uint64)
```

基于 Shapley 值的二方分配公式：
```
uA = (fAB + R + EA - EB) / 2
uB = (fAB + R + EB - EA) / 2
```

**核心性质**：
- **守恒不变量**：`uA + uB = fAB + R`（总奖励守恒）
- **公平性**：根据各分片的机会成本（EA, EB）调整分配
- **非负性**：使用有符号运算后向下取整到 0

#### 三阶段分类决策

**Classify 函数**
```go
func Classify(uA, EA, EB uint64) Case
```

源分片根据自身效用 uA 将 CTX 分为三类：

| 分类 | 条件 | 决策 | 优先级 |
|------|------|------|--------|
| Case1 | uA >= EA | 总是包含 | 高（阶段1） |
| Case2 | uA <= EA - EB | 延迟处理 | 极低（阶段3） |
| Case3 | EA - EB < uA < EA | 有空间时包含 | 中（阶段2） |

**Case1**：CTX 的效用至少等于平均 ITX 费用，值得优先处理  
**Case2**：CTX 的效用过低，作为最低优先级延迟处理，但**不会被永久丢弃**  
**Case3**：CTX 效用适中，在满足高优先级交易后有剩余空间时处理

**重要说明**：
- **分类仅在源分片进行**：只有源分片根据 uA 对 CTX 进行分类
- **目标分片不分类**：目标分片将所有接收到的 CTX 视为高优先级（Case1），因为：
  1. CTX 已在源分片经过筛选
  2. 目标分片应尽快完成第二阶段，避免二次延迟
  3. 目标分片的效用 uB 已经在源分片决策时被考虑

### 3. 交易结构扩展（core/transaction）

为 `Transaction` 结构添加了以下 Justitia 相关字段：

```go
type Transaction struct {
    // ... 原有字段 ...
    
    // 分片信息
    FromShard        int       // 源分片 ID
    ToShard          int       // 目标分片 ID
    IsCrossShard     bool      // 是否跨分片交易
    PairID           string    // 唯一配对标识符（通常为 TxHash）
    
    // 费用和指标
    FeeToProposer    uint64    // 提议者费用
    ArrivalTime      time.Time // 到达交易池时间
    TxSize           int       // 交易大小（默认 1）
    
    // Justitia 奖励追踪
    SubsidyR         uint64    // 补贴 R_AB
    UtilityA         uint64    // 源分片提议者效用 uA
    UtilityB         uint64    // 目标分片提议者效用 uB
    JustitiaCase     int       // 分类（1/2/3）
    
    // Relay 追踪
    IsRelay2         bool      // 是否为 Relay 第二阶段
    OriginalPropTime time.Time // 原始提议时间
    IncludedInBlockA uint64    // 源分片区块号
    IncludedInBlockB uint64    // 目标分片区块号
}
```

### 4. 分片映射（utils/utils_shard）

#### 确定性地址哈希

**ShardForAddress 函数**
```go
func ShardForAddress(address Address, numShards int) int
```

- 使用 SHA-256 对地址进行哈希
- 取哈希值的前 8 字节转换为 uint64
- 对分片数取模得到分片 ID
- **确定性**：相同地址在所有节点上映射到相同分片
- **分布均匀**：密码学哈希保证地址在分片间均匀分布

**IsCrossShard 函数**
```go
func IsCrossShard(sender, recipient Address, numShards int) bool
```
- 判断发送者和接收者是否在不同分片
- 单分片系统总是返回 false

### 5. 交易调度器（txpool/scheduler）

#### 核心选择算法

**SelectForBlock 函数**
```go
func (s *Scheduler) SelectForBlock(capacity int, txPool []*core.Transaction) []*core.Transaction
```

实现两阶段选择策略：

**阶段 1（高优先级）**：
- ITX：`fee >= EA`
- CTX：`Case1`（`uA >= EA`）
- 按分数降序排列

**阶段 2（剩余空间）**：
- ITX：`fee < EA`
- CTX：`Case3`（`EA - EB < uA < EA`）
- 按分数降序排列

**阶段 3（最低优先级）**：
- CTX：`Case2`（`uA <= EA - EB`）
- 按分数降序排列
- 仅在阶段1和阶段2未填满区块时考虑

**评分规则**：
- ITX 分数 = `FeeToProposer`
- CTX 分数（在分片 s）= `u(s)`（来自 Shapley 分配）

**平局处理**：
- 分数相同时，按到达时间（FIFO）排序

#### scoreCTX 方法

为 CTX 计算分数和分类：
- 判断本地分片是源分片还是目标分片
- 获取两分片的平均费用 EA 和 EB
- 计算补贴 R_AB
- 执行 Shapley 分配
- 返回本地分片的效用作为分数

### 6. 待结算账本（crossshard/pending）

#### 数据结构

```go
type Pending struct {
    PairID        string // 唯一标识符
    ShardA        int    // 源分片
    ShardB        int    // 目标分片
    FAB           uint64 // 交易费用
    R             uint64 // 补贴
    EA            uint64 // CTX 包含时的 E(f_A)
    EB            uint64 // CTX 包含时的 E(f_B)
    UtilityA      uint64 // uA
    UtilityB      uint64 // uB
    SourceBlockID string // 源分片区块 ID
    CreatedAt     int64  // 创建时间戳
}

type Ledger struct {
    pending  map[string]*Pending // 待结算交易
    settled  map[string]bool     // 已结算交易
}
```

#### 结算流程

1. **添加待结算（Add）**：
   - 源分片包含 CTX 时调用
   - 记录所有必要信息（费用、补贴、效用）
   - 防止重复添加

2. **结算（Settle）**：
   - 目标分片包含 CTX' 时调用
   - 通过 `creditFunc` 回调向两个提议者发放奖励
   - 源分片提议者获得 `uA`
   - 目标分片提议者获得 `uB`
   - 从待结算中移除，标记为已结算
   - 防止双重结算

3. **清理（CleanupOld）**：
   - 定期清理超时的待结算条目
   - 处理可能丢失的交易

### 7. 补贴预算控制（economics/subsidy_budget）

#### 功能

可选的每区块补贴总量控制，防止补贴过度通胀。

#### 数据结构

```go
type Budget struct {
    Bmin uint64 // 每区块最小总补贴
    Bmax uint64 // 每区块最大总补贴
}
```

#### Apply 方法

```go
func (b *Budget) Apply(sumR uint64) ScalingFactor
```

根据当前区块的总补贴 sumR 返回缩放因子：

| 条件 | 缩放因子 | 说明 |
|------|----------|------|
| sumR > Bmax | Bmax / sumR | 按比例缩减 |
| sumR < Bmin | Bmin / sumR | 按比例放大 |
| Bmin <= sumR <= Bmax | 1 / 1 | 不缩放 |

#### 年度预算转换

```go
func (cfg *BudgetConfig) ToBudget() (*Budget, error)
```

- 根据区块间隔计算每年区块数
- 将年度预算转换为每区块预算
- 支持 `GammaMin` 和 `GammaMax` 配置

## 配置参数

### paramsConfig.json

```json
{
  "EnableJustitia": 1,           // 启用 Justitia（1=启用，0=禁用）
  "JustitiaSubsidyMode": 1,      // 补贴模式（0=None, 1=DestAvg, 2=SumAvg, 3=Custom, 4=ExtremeFixed）
  "JustitiaWindowBlocks": 16,    // 滚动平均窗口大小（区块数）
  "JustitiaGammaMin": 0,         // 每区块最小补贴（0=无限制）
  "JustitiaGammaMax": 0,         // 每区块最大补贴（0=无限制）
  "JustitiaRewardBase": 1000.0   // 遗留字段，已弃用
}
```

### 全局配置变量（params/global_config.go）

```go
var (
    EnableJustitia       int
    JustitiaSubsidyMode  int
    JustitiaWindowBlocks int
    JustitiaGammaMin     uint64
    JustitiaGammaMax     uint64
)
```

## 完整工作流程

### 1. 系统初始化

```go
// 创建费用追踪器
feeTracker := expectation.NewTracker(params.JustitiaWindowBlocks)

// 创建待结算账本
pendingLedger := pending.NewLedger()

// 创建调度器（每个分片一个）
scheduler := scheduler.NewScheduler(
    shardID,
    params.ShardNum,
    feeTracker,
    justitia.SubsidyMode(params.JustitiaSubsidyMode),
)

// 可选：创建预算控制
budget, _ := subsidy_budget.NewBudget(
    params.JustitiaGammaMin,
    params.JustitiaGammaMax,
)
```

### 2. 交易注入

当交易从数据集读取并注入时：

```go
tx := core.NewTransaction(sender, recipient, value, nonce, time.Now())

// 计算分片映射
tx.FromShard = utils.ShardForAddress(tx.Sender, params.ShardNum)
tx.ToShard = utils.ShardForAddress(tx.Recipient, params.ShardNum)
tx.IsCrossShard = (tx.FromShard != tx.ToShard)
tx.PairID = string(tx.TxHash)

// 计算提议者费用（从数据集中的 gas 信息）
tx.FeeToProposer = calculateFeeToProposer(tx)

// 设置到达时间
tx.ArrivalTime = time.Now()
```

### 3. 区块提议（源分片）

```go
// 获取当前平均费用
EA := feeTracker.GetAvgITXFee(shardA)

// 从交易池选择交易
selectedTxs := scheduler.SelectForBlock(blockCapacity, txPool)

// 对于被选中的 CTX
for _, tx := range selectedTxs {
    if tx.IsCrossShard {
        // 计算补贴
        EB := feeTracker.GetAvgITXFee(tx.ToShard)
        R := justitia.RAB(mode, EA, EB, customFunc)
        tx.SubsidyR = R
        
        // Shapley 分配
        uA, uB := justitia.Split2(tx.FeeToProposer, R, EA, EB)
        tx.UtilityA = uA
        tx.UtilityB = uB
        
        // 分类
        txCase := justitia.Classify(uA, EA, EB)
        tx.JustitiaCase = int(txCase)
        
        // 添加到待结算账本
        p := &pending.Pending{
            PairID:        tx.PairID,
            ShardA:        tx.FromShard,
            ShardB:        tx.ToShard,
            FAB:           tx.FeeToProposer,
            R:             R,
            EA:            EA,
            EB:            EB,
            UtilityA:      uA,
            UtilityB:      uB,
            SourceBlockID: currentBlockID,
            CreatedAt:     time.Now().Unix(),
        }
        pendingLedger.Add(p)
    }
}

// 创建并广播区块
block := createBlock(selectedTxs)
```

### 4. 区块最终化（源分片）

```go
// 提取 ITX 费用（不包括 CTX）
itxFees := make([]uint64, 0)
for _, tx := range block.Body {
    if !tx.IsCrossShard {
        itxFees = append(itxFees, tx.FeeToProposer)
    }
}

// 更新费用追踪器
feeTracker.OnBlockFinalized(shardA, itxFees)
```

### 5. 区块提议（目标分片）

目标分片接收到 CTX' 的 relay 消息后：

```go
// 从 relay 池选择交易
selectedTxs := scheduler.SelectForBlock(blockCapacity, relayPool)

// CTX' 在目标分片的评分使用 uB
// scheduler 会自动处理
```

### 6. 区块最终化（目标分片）

```go
// 更新费用追踪器（仅 ITX）
itxFees := extractITXFees(block)
feeTracker.OnBlockFinalized(shardB, itxFees)

// 结算跨分片交易奖励
for _, tx := range block.Body {
    if tx.IsCrossShard && pendingLedger.IsPending(tx.PairID) {
        // 定义奖励发放函数
        creditFunc := func(shardID int, proposerID string, amount uint64) {
            // 实际铸币或从补贴池转账
            creditReward(proposerID, amount)
        }
        
        // 结算
        pendingLedger.Settle(tx.PairID, currentBlockID, creditFunc)
    }
}
```

### 7. 可选：应用预算约束

如果启用了补贴预算：

```go
// 收集本区块所有待结算的补贴
subsidies := make([]uint64, 0)
for _, tx := range block.Body {
    if tx.IsCrossShard && pendingLedger.IsPending(tx.PairID) {
        p, _ := pendingLedger.Get(tx.PairID)
        subsidies = append(subsidies, p.R)
    }
}

// 应用预算缩放
scaledSubsidies, sf := subsidy_budget.ApplyBudgetToBlock(budget, subsidies)

// 使用缩放后的补贴进行结算
for i, tx := range ctxList {
    p, _ := pendingLedger.Get(tx.PairID)
    p.R = scaledSubsidies[i]
    // 重新计算 uA 和 uB
    uA, uB := justitia.Split2(p.FAB, p.R, p.EA, p.EB)
    p.UtilityA = uA
    p.UtilityB = uB
}
```

## 费用计算

### 从以太坊数据集计算提议者费用

假设数据集包含以下字段：
- `gasUsed`
- `gasPrice`（Legacy/EIP-1559 type 0/1）
- `baseFeePerGas`（EIP-1559 type 2）
- `maxFeePerGas`（EIP-1559 type 2）
- `maxPriorityFeePerGas`（EIP-1559 type 2）
- `eip2718type`

```go
func calculateFeeToProposer(tx *EthTx) uint64 {
    if tx.Eip2718type == 0 || tx.Eip2718type == 1 {
        // Legacy: f = gasUsed * gasPrice
        return tx.GasUsed * tx.GasPrice
    } else if tx.Eip2718type == 2 {
        // EIP-1559
        effectiveGasPrice := min(tx.MaxFeePerGas, tx.BaseFeePerGas + tx.MaxPriorityFeePerGas)
        priorityTip := max(effectiveGasPrice - tx.BaseFeePerGas, 0)
        return tx.GasUsed * priorityTip
    }
    return 0
}
```

**注意**：忽略被销毁的 `baseFee`，仅计算提议者实际获得的小费。

## 测试

### 单元测试

已为所有核心模块编写了完整的单元测试：

1. **incentive/justitia/justitia_test.go**
   - Split2 守恒不变量
   - Split2 对称性
   - RAB 模式验证
   - Classify 阈值正确性
   - 边界情况处理

2. **fees/expectation/avg_test.go**
   - 滑动窗口正确性
   - 多分片独立性
   - ITX 专用性
   - 并发安全性

3. **economics/subsidy_budget/budget_test.go**
   - 缩放逻辑
   - 年度预算转换
   - 边界情况

4. **crossshard/pending/ledger_test.go**
   - 添加、获取、结算流程
   - 防止双重结算
   - 统计和清理

5. **utils/utils_shard_test.go**
   - 确定性哈希
   - 分布均匀性
   - 跨分片检测

### 集成测试

**test/integration/justitia_integration_test.go** 包含：

1. **端到端流程测试**
   - 完整的 CTX 生命周期
   - 从创建到结算的全流程
   - 守恒不变量验证

2. **交易选择测试**
   - Case1/Case2/Case3 分类
   - 阶段 1 和阶段 2 选择
   - 容量限制

3. **补贴模式比较**
   - None vs DestAvg vs SumAvg
   - 自定义补贴函数

4. **预算约束测试**
   - 缩放机制
   - 上下限执行

### 运行测试

```bash
# 运行所有测试
go test ./...

# 运行特定模块测试
go test ./incentive/justitia
go test ./fees/expectation
go test ./crossshard/pending

# 运行集成测试
go test ./test/integration

# 运行基准测试
go test -bench=. ./incentive/justitia
go test -bench=. ./fees/expectation
```

## 性能考虑

### 计算复杂度

- **ShardForAddress**: O(1) - SHA-256 哈希
- **Split2**: O(1) - 简单算术
- **RAB**: O(1) - 模式查找
- **Classify**: O(1) - 阈值比较
- **OnBlockFinalized**: O(K) - K 为窗口大小
- **SelectForBlock**: O(N log N) - N 为交易池大小（排序主导）

### 内存使用

- **Tracker**: O(S * K) - S 个分片，每个 K 个区块历史
- **Ledger**: O(P) - P 为待结算交易数
- **Scheduler**: O(N) - N 为交易池大小（临时）

### 优化建议

1. **批量处理**：在区块最终化时批量更新费用追踪器
2. **延迟清理**：定期（而非每次）清理过期的待结算条目
3. **缓存**：缓存常用的平均费用值，减少锁竞争
4. **预分配**：为已知大小的切片预分配内存

## 指标和日志

### 推荐的 CSV 日志格式

每笔交易记录：
```csv
txHash,fromShard,toShard,isCross,feeToProposer,subsidyR,utilityA,utilityB,justitiaCase,enqueueTime,includedAtA,includedAtB,queueDelayA,queueDelayB,blockNumberA,blockNumberB
```

每个区块记录：
```csv
blockNumber,shardID,avgITXFee,ctxCount,itxCount,totalSubsidy,blockReward,timestamp
```

每个分片汇总：
```csv
shardID,epoch,avgITXFee,ctxRatio,avgCTXDelay,avgITXDelay,tps
```

## 边界情况和错误处理

### 已处理的边界情况

1. **EB >= EA（下溢保护）**
   - `Classify` 中检查避免 `EA - EB` 下溢
   - 当 EB 很大时，Case2 阈值为 0

2. **负效用（向下取整）**
   - `Split2` 使用有符号算术
   - 负值取 0

3. **空滑动窗口（启动阶段）**
   - `GetAvgITXFee` 返回 0
   - 可考虑全局中位数预热

4. **双重结算**
   - `Ledger` 追踪已结算交易
   - `Settle` 检查防止重复

5. **丢失的 CTX'**
   - `CleanupOld` 定期清理超时条目
   - 可配置超时阈值

6. **零分片数**
   - `ShardForAddress` 返回 0
   - `IsCrossShard` 返回 false

7. **整数溢出**
   - 当前使用 `uint64`
   - 超大值可能需要 `uint128` 或 `big.Int`

## 与现有系统集成

### 替换 FIFO

原有的 FIFO 交易选择应替换为 Justitia 调度器：

```go
// 旧代码
txs := txPool.PackTxs(maxBlockSize)

// 新代码
txs := scheduler.SelectForBlock(maxBlockSize, txPool.TxQueue)
```

### 替换固定补贴

原有的固定 `JustitiaReward = 300` 应替换为动态补贴：

```go
// 旧代码
if tx.IsCrossShard {
    tx.JustitiaReward = 300
}

// 新代码
if tx.IsCrossShard {
    EA := feeTracker.GetAvgITXFee(tx.FromShard)
    EB := feeTracker.GetAvgITXFee(tx.ToShard)
    R := justitia.RAB(mode, EA, EB, customFunc)
    tx.SubsidyR = R
}
```

### 集成到 PBFT 共识

在 `pbft.go` 或相应的共识模块中：

```go
// 区块提议阶段
func (p *PbftInsideNode) proposeBlock() {
    selectedTxs := p.scheduler.SelectForBlock(p.maxBlockSize, p.txPool.TxQueue)
    block := p.createBlock(selectedTxs)
    // ... PBFT 流程
}

// 区块最终化阶段
func (p *PbftInsideNode) finalizeBlock(block *Block) {
    // 更新费用追踪器
    itxFees := extractITXFees(block)
    p.feeTracker.OnBlockFinalized(p.shardID, itxFees)
    
    // 结算跨分片奖励
    for _, tx := range block.Body {
        if tx.IsCrossShard && p.pendingLedger.IsPending(tx.PairID) {
            p.pendingLedger.Settle(tx.PairID, block.Hash, p.creditReward)
        }
    }
}
```

## 未来扩展

### 可能的改进方向

1. **自适应窗口大小**
   - 根据网络波动性动态调整 K
   - 高波动时使用更大窗口

2. **多层补贴**
   - 不同优先级的 CTX 使用不同补贴公式
   - 紧急交易获得更高补贴

3. **跨分片费用市场**
   - 分片间协商补贴
   - 供需平衡机制

4. **机器学习优化**
   - 预测最优补贴水平
   - 学习历史模式

5. **更复杂的分类**
   - 超过 3 个 case
   - 考虑网络拥塞状态

## 常见问题

### Q: 为什么 RAB 不使用交易费用 f_AB？

**A**: 为了避免循环依赖。如果补贴依赖于费用，用户可能操纵费用来影响补贴，导致不稳定。使用分片平均费用 E(f_s) 提供了稳定的参考点。

### Q: 为什么使用 Shapley 值而不是简单的 50/50 分配？

**A**: Shapley 值考虑了各分片的机会成本（EA 和 EB）。如果一个分片的平均费用很高，其提议者放弃本地 ITX 来处理 CTX 的成本更高，应获得更多奖励。

### Q: Case2 的交易会永远被排除吗？

**A**: 不一定。Case2 交易可以：
1. 等待费用环境改善（EA 下降或 EB 上升）
2. 用户提高交易费用
3. 系统管理员手动调整
4. 实现超时后强制包含机制

### Q: 补贴从哪里来？

**A**: 补贴可以来自：
1. 铸币（区块奖励的一部分）
2. 预留的激励池
3. 系统手续费的一部分
4. 治理决定的其他来源

### Q: 滑动窗口大小如何选择？

**A**: 
- 太小（如 K=4）：对短期波动过于敏感
- 太大（如 K=100）：反应迟钝，不能及时适应变化
- 推荐 K=16：在稳定性和响应性间平衡
- 可根据实际区块时间调整（如 5 秒区块用 K=12，10 秒区块用 K=6）

### Q: 如何处理单分片系统？

**A**: 所有检查函数都处理了 `numShards = 1` 的情况，此时没有跨分片交易，Justitia 机制自动退化为普通的 FIFO。

## 总结

Justitia 激励机制通过以下方式改善跨分片交易的处理：

1. **动态补贴**：根据分片费用环境自动调整，无需人工干预
2. **公平分配**：Shapley 值确保提议者获得与其贡献相称的奖励
3. **智能优先级**：三阶段分类在不牺牲整体吞吐量的前提下优先处理有价值的 CTX
4. **可配置性**：支持多种补贴模式和可选的预算控制
5. **可扩展性**：模块化设计便于未来扩展和定制

通过完整的单元测试和集成测试，我们确保了实现的正确性和鲁棒性。系统已准备好进行实验评估，以验证其在减少 CTX 延迟和提高跨分片吞吐量方面的有效性。

---

**实现版本**: 1.0  
**最后更新**: 2025-11-03  
**作者**: BlockEmulator Justitia 实现团队
