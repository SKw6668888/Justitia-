# Justitia 快速启动指南

## 🚀 5分钟快速开始

### 步骤1: 确认配置

检查 `paramsConfig.json` 文件是否包含以下配置：

```json
{
  "ConsensusMethod": 3,           // 必须使用Relay机制
  "EnableJustitia": 1,            // 启用Justitia
  "JustitiaRewardBase": 100.0     // 奖励值R
}
```

### 步骤2: 编译项目

```bash
go build
```

### 步骤3: 运行实验

```bash
# Windows
./blockEmulator.exe

# Linux/Mac
./blockEmulator
```

### 步骤4: 查看结果

实验完成后，查看以下文件：

1. **Justitia效果报告**：`expTest/result/Justitia_Effectiveness.csv`
2. **交易确认延迟**：`expTest/result/Transaction_Confirm_Latency.csv`
3. **系统日志**：`expTest/log/`

---

## 📊 结果解读

打开 `Justitia_Effectiveness.csv`，查看关键列：

| 指标 | 期望值 | 说明 |
|------|--------|------|
| **Latency Reduction (%)** | **负值** | 负值表示CTX比分片内交易快！ |
| CTX Avg Latency | < 3秒 | 跨分片交易平均延迟 |
| Inner-Shard Avg Latency | 3-4秒 | 分片内交易平均延迟 |
| Justitia Status | "Effective" | 系统判定Justitia有效 |

### 示例结果

```csv
EpochID,Inner-Shard Tx Count,Cross-Shard Tx Count,Inner-Shard Avg Latency,CTX Avg Latency,Latency Reduction (%),Justitia Status
0,320,680,3.2,2.8,-12.5,Effective (CTX faster)
1,340,660,3.3,2.9,-12.1,Effective (CTX faster)
```

**解读**：CTX延迟为2.8秒，分片内为3.2秒，CTX快了12.5%！✅

---

## 🔧 参数调优

### 场景1: CTX延迟仍然较高

**问题**：`Latency Reduction > 0`（CTX更慢）

**解决**：增加奖励值
```json
"JustitiaRewardBase": 200.0  // 从100增加到200
```

### 场景2: 分片内交易延迟过高

**问题**：分片内交易延迟 > 5秒

**解决**：降低奖励值或增加区块大小
```json
"JustitiaRewardBase": 50.0,   // 降低奖励
"BlockSize": 3000              // 增加区块大小
```

### 场景3: 系统吞吐量下降

**问题**：整体TPS降低

**解决**：缩短区块间隔
```json
"Block_Interval": 3000  // 从5000降到3000ms
```

---

## 🆚 对比测试

### 测试A: 禁用Justitia（基线）

```json
{
  "EnableJustitia": 0
}
```

运行并记录：
- CTX平均延迟
- 分片内平均延迟

### 测试B: 启用Justitia

```json
{
  "EnableJustitia": 1,
  "JustitiaRewardBase": 100.0
}
```

运行并对比：
- CTX延迟是否降低？
- 降低幅度多少？

### 预期对比

| 指标 | 无Justitia | 有Justitia | 改善 |
|------|------------|------------|------|
| CTX延迟 | ~6秒 | ~2.8秒 | -53% ✅ |
| 分片内延迟 | ~3秒 | ~3.3秒 | +10% |

---

## ❓ 常见问题

### Q: 如何确认Justitia已启用？

**A**: 查看启动日志，应该看到：
```
Config: {...EnableJustitia:1 JustitiaRewardBase:100...}
```

### Q: 为什么CSV文件是空的？

**A**: 确保：
1. `ConsensusMethod` 设置为3（Relay）
2. 实验运行完成（等待所有交易处理完）
3. `EnableJustitia` 设置为1

### Q: CTX延迟还是很高怎么办？

**A**: 逐步调整：
```json
// 步骤1: 增加奖励
"JustitiaRewardBase": 150.0

// 步骤2: 如果还不够，继续增加
"JustitiaRewardBase": 200.0

// 步骤3: 同时减小注入速度
"InjectSpeed": 1500
```

---

## 📖 详细文档

完整的技术文档请参阅：[justitia.md](./justitia.md)

---

## ✅ 验证清单

运行实验前检查：

- [ ] `ConsensusMethod` = 3
- [ ] `EnableJustitia` = 1
- [ ] `JustitiaRewardBase` > 0
- [ ] 编译成功，无错误
- [ ] `expTest/` 目录存在

实验完成后验证：

- [ ] `Justitia_Effectiveness.csv` 文件存在
- [ ] `Latency Reduction` 为负值
- [ ] CTX延迟 < 分片内延迟
- [ ] `Justitia Status` = "Effective"

---

**祝实验成功！** 🎉

如有问题，请查看详细文档 [justitia.md](./justitia.md) 或提交Issue。

