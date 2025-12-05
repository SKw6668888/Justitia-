# 实验配置建议与检查清单

## 📋 当前配置分析

### 基础配置（paramsConfig.json）
```json
{
  "BlockSize": 1500,              // 每个区块最多1500个交易
  "Block_Interval": 2000,         // 2秒出一个块
  "InjectSpeed": 5000,            // 每5秒注入一批交易
  "TotalDataSize": 250000,        // 总共250,000个交易
  "TxBatchSize": 25000,           // 每批25,000个交易
  
  "EnableJustitia": 1,            // ✓ 已启用Justitia
  "JustitiaSubsidyMode": 2,       // 当前是R=E(f_A)+E(f_B)
  "JustitiaWindowBlocks": 16,     // 滑动窗口16个区块
  "JustitiaRewardBase": 1000.0    // ⚠️ 这个参数已废弃，不影响实验
}
```

## ⚠️ 关键问题与建议

### 1. **实验可重复性问题** 🔴 重要

**问题**：不同补贴方案的实验数据差异太大
- R=E(f_B): 65,421个CTX
- R=E(f_A)+E(f_B): 35,605个CTX（只有54%）

**可能原因**：
- 交易注入速度不稳定
- 实验运行时长不同
- 随机种子不同

**建议修改**：

```json
{
  "TotalDataSize": 250000,        // 保持不变
  "TxBatchSize": 25000,           // 保持不变
  "InjectSpeed": 5000,            // ✓ 固定注入速度
  
  // 新增：确保实验时长一致
  "MaxEpochs": 100,               // 建议：运行固定的epoch数
  "FixedRandomSeed": 42           // 建议：使用固定随机种子
}
```

### 2. **补贴模式配置** ✅ 正确

需要运行5个实验，每次只改变 `JustitiaSubsidyMode`：

| 实验名称 | EnableJustitia | JustitiaSubsidyMode | JustitiaRewardBase | 说明 |
|---------|----------------|---------------------|-------------------|------|
| Monoxide | 0 | - | - | 基准：无Justitia |
| R=0 | 1 | 0 | - | 无补贴 |
| R=E(f_B) | 1 | 1 | - | 目标分片平均费用 |
| R=E(f_A)+E(f_B) | 1 | 2 | - | 两个分片平均费用之和 |
| R=1 ETH/CTX | 1 | 4 | 1000000000000000000 | 固定1 ETH补贴 |

**⚠️ 注意**：`JustitiaRewardBase` 只在 `SubsidyMode=4` 时需要设置为 `1e18`（1 ETH = 10^18 Wei）

### 3. **数据收集配置** ✅ 应该已有

确保以下文件都会生成：
- ✓ `Justitia_Effectiveness.csv` - 包含CTX优先率等关键指标
- ✓ `Tx_Details.csv` - 包含所有交易的详细信息（包括ITX和CTX）
- ✓ `CTX_Fee_Latency.csv` - 包含CTX的费用和延迟信息

### 4. **网络参数** ⚠️ 需要注意

```json
{
  "Delay": -1,           // -1表示无延迟
  "JitterRange": -1,     // -1表示无抖动
  "Bandwidth": 10000000  // 10MB/s带宽
}
```

**建议**：
- 如果要模拟真实网络，设置 `"Delay": 50`（50ms延迟）
- 如果要测试理想情况，保持 `-1`（当前配置）

## 📝 推荐的实验流程

### 步骤1：准备配置文件

创建5个配置文件（或使用脚本自动生成）：

```bash
paramsConfig_monoxide.json    # EnableJustitia=0
paramsConfig_R0.json          # SubsidyMode=0
paramsConfig_R_EB.json        # SubsidyMode=1
paramsConfig_R_EA_EB.json     # SubsidyMode=2
paramsConfig_R_1ETH.json      # SubsidyMode=4, RewardBase=1e18
```

### 步骤2：运行实验

**关键要求**：
1. ✅ **使用相同的数据集文件**
2. ✅ **使用相同的TotalDataSize和TxBatchSize**
3. ✅ **运行相同的时长或epoch数**
4. ⚠️ **建议：使用固定的随机种子**

### 步骤3：数据验证

运行每个实验后，立即检查：

```bash
# 检查数据文件是否生成
ls expTest_*/result/supervisor_measureOutput/

# 应该看到：
# - Justitia_Effectiveness.csv
# - Tx_Details.csv
# - CTX_Fee_Latency.csv
# - Average_TPS.csv
# - Transaction_Confirm_Latency.csv
```

## 🔧 建议的配置修改

### 修改1：增加实验时长（可选）

如果想要更稳定的数据：

```json
{
  "TotalDataSize": 500000,    // 从250K增加到500K
  "TxBatchSize": 50000        // 相应增加批次大小
}
```

### 修改2：调整区块大小（可选）

如果发现CTX积压严重：

```json
{
  "BlockSize": 2000,          // 从1500增加到2000
  "Block_Interval": 2000      // 保持2秒不变
}
```

### 修改3：调整注入速度（可选）

如果想测试高负载场景：

```json
{
  "InjectSpeed": 3000,        // 从5秒减少到3秒（更快）
}
```

## 📊 数据一致性检查

运行完所有实验后，检查以下指标是否合理：

### 1. 总交易数应该接近
```python
# 所有实验的总交易数应该接近TotalDataSize
total_tx = ctx_count + itx_count
assert 240000 < total_tx < 260000  # 允许±10K误差
```

### 2. ITX数量应该相似
```python
# 不同实验的ITX数量应该相近（因为ITX生成不受补贴影响）
itx_counts = [29671, 30584, ...]  # 各实验的ITX数量
std_dev = np.std(itx_counts)
assert std_dev < 5000  # 标准差应该小于5000
```

### 3. CTX优先率应该递增
```python
# 理论上：R=0 < R=E(f_B) < R=E(f_A)+E(f_B) < R=1ETH
priority_rates = {
    'R=0': rate0,
    'R=E(f_B)': rate_eb,
    'R=E(f_A)+E(f_B)': rate_ea_eb,
    'R=1 ETH/CTX': rate_1eth
}
# 应该满足递增关系（但可能有例外）
```

## 🎯 最终建议

### 当前配置是否需要修改？

**基本配置：✅ 可以使用**
- 区块大小、出块间隔、注入速度都是合理的

**需要改进的地方：**

1. **⚠️ 确保实验时长一致**
   - 建议：添加固定的epoch数限制
   - 或者：确保所有实验都处理完全部250K交易

2. **⚠️ 使用固定随机种子**
   - 这样可以确保交易生成模式一致

3. **⚠️ R=1 ETH/CTX 的配置**
   - 确认 `JustitiaRewardBase` 设置为 `1000000000000000000`（1e18）
   - 而不是当前的 `1000.0`

### 建议的修改后配置

```json
{
  "ConsensusMethod": 3,
  "PbftViewChangeTimeOut": 20000,
  "ExpDataRootDir": "expTest",
  "Block_Interval": 2000,
  "BlockSize": 1500,
  "BlocksizeInBytes": 300000,
  "UseBlocksizeInBytes": 0,
  "InjectSpeed": 5000,
  "TotalDataSize": 250000,
  "TxBatchSize": 25000,
  "BrokerNum": 10,
  "RelayWithMerkleProof": 0,
  "DatasetFile": "./23000000to23249999_BlockTransaction.csv",
  "ReconfigTimeGap": 50,
  "Delay": -1,
  "JitterRange": -1,
  "Bandwidth": 10000000,
  
  // Justitia配置（根据实验修改这些值）
  "EnableJustitia": 1,
  "JustitiaSubsidyMode": 2,
  "JustitiaWindowBlocks": 16,
  "JustitiaGammaMin": 0,
  "JustitiaGammaMax": 0,
  "JustitiaRewardBase": 1000000000000000000  // ⚠️ 修改：用于SubsidyMode=4
}
```

## 🚀 执行计划

1. **备份当前配置和数据**
2. **修改配置文件**（特别是JustitiaRewardBase）
3. **按顺序运行5个实验**
4. **每个实验后立即验证数据完整性**
5. **运行数据分析脚本**
6. **生成图表**

## ⏱️ 预计时间

- 每个实验运行时间：约10-20分钟（取决于TotalDataSize）
- 总实验时间：约1-2小时
- 数据分析时间：约5-10分钟
