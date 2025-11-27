# ✅ 五种机制图表生成完成

## 修复总结

已成功修复数据分析和绘图系统，现在**所有7个图表都包含完整的5种机制**：

### 五种机制
1. **Monoxide** - 基准方案（无 Justitia）
2. **R=0** - Justitia 启用但无补贴
3. **R=E(f_B)** - 补贴 = E(f_B)
4. **R=E(f_A)+E(f_B)** - 补贴 = E(f_A) + E(f_B)
5. **R=1 ETH/CTX** - 固定补贴 1 ETH/CTX

---

## 修复内容

### 1. 数据分析器 (`justitia_data_analyzer.py`)

#### 问题
- Monoxide 实验没有 `Justitia_Effectiveness.csv` 文件
- 导致数据加载失败，所有图表缺少 Monoxide 数据

#### 解决方案
- 为 Monoxide 添加特殊处理逻辑
- 从 `Tx_Details.csv` 构建等效的数据结构
- 分离 CTX 和 ITX，计算延迟统计信息

#### 修改的函数
- `load_all_data()` - 添加 Monoxide 特殊加载逻辑
- `extract_queueing_latency_data()` - 支持 Monoxide 的 ctx_latencies
- `extract_latency_ratio_data()` - 简化输出格式为纯比值
- `extract_kde_distribution_data()` - 支持 Monoxide
- `extract_cdf_data()` - 支持 Monoxide
- `extract_ctx_ratio_data()` - 支持 Monoxide，简化输出格式
- `extract_cumulative_subsidy_data()` - 跳过 Monoxide 和 R=0

### 2. 绘图脚本 (`plot_fig6_subsidy.py`)

#### 问题
- 数据字段名不匹配（`epochs` vs `block_heights`）
- 补贴字段名不匹配（`cumulative_subsidy_eth` vs `cumulative_subsidy`）

#### 解决方案
- 添加字段名兼容性检查
- 支持多种数据格式

---

## 生成的图表

### ✅ 图1: CTX 排队延迟箱线图
- **文件**: `figures/fig1_ctx_latency_boxplot.png`
- **包含**: 5种机制
- **统计信息**:
  - Monoxide: 中位数 294.01s
  - R=0: 中位数 20.77s
  - R=E(f_B): 中位数 19.93s
  - R=E(f_A)+E(f_B): 中位数 120.89s
  - R=1 ETH/CTX: 中位数 156.11s

### ✅ 图2: CTX/ITX 延迟比值柱状图
- **文件**: `figures/fig2_latency_ratio_bar.png`
- **包含**: 5种机制
- **比值**:
  - Monoxide: 2.214x
  - R=0: 1.408x
  - R=E(f_B): 1.559x
  - R=E(f_A)+E(f_B): 1.362x
  - R=1 ETH/CTX: 1.097x ✨ 最接近公平

### ✅ 图3: CTX 延迟 KDE 分布
- **文件**: `figures/fig3_latency_kde.png`
- **包含**: 5种机制
- **数据点**:
  - Monoxide: 4224 点
  - R=0: 25 点
  - R=E(f_B): 25 点
  - R=E(f_A)+E(f_B): 36 点
  - R=1 ETH/CTX: 28 点

### ✅ 图4: CTX 延迟 CDF
- **文件**: `figures/fig4_latency_cdf.png`
- **包含**: 5种机制
- **数据点**:
  - Monoxide: 94160 点
  - R=0: 36 点
  - R=E(f_B): 36 点
  - R=E(f_A)+E(f_B): 39 点
  - R=1 ETH/CTX: 32 点

### ✅ 图5: 区块中 CTX 占比
- **文件**: `figures/fig5_ctx_ratio.png`
- **包含**: 5种机制
- **占比**:
  - Monoxide: 68.1%
  - R=0: 31.3%
  - R=E(f_B): 31.0%
  - R=E(f_A)+E(f_B): 69.2%
  - R=1 ETH/CTX: 68.1%

### ✅ 图6: 累计补贴发行量
- **文件**: `figures/fig6_cumulative_subsidy.png`
- **包含**: 3种有补贴的机制（Monoxide 和 R=0 无补贴）
- **最终累计补贴**:
  - R=E(f_B): 19.82 ETH
  - R=E(f_A)+E(f_B): 210.65 ETH
  - R=1 ETH/CTX: 94160.00 ETH

### ✅ 图7: 提议者利润分布 CDF
- **文件**: `figures/fig7_proposer_profit_cdf.png`
- **说明**: 展示在 R=E(f_B) 机制下，CTX 和 ITX 的利润分布对比
- **目的**: 证明提议者公平性

---

## 如何重新生成图表

### 方法1: 生成所有图表
```bash
cd figurePlot
python justitia_data_analyzer.py  # 生成数据文件
python plot_fig1_boxplot.py       # 生成图1
python plot_fig2_ratio.py         # 生成图2
python plot_fig3_kde.py           # 生成图3
python plot_fig4_cdf.py           # 生成图4
python plot_fig5_ctx_ratio.py     # 生成图5
python plot_fig6_subsidy.py       # 生成图6
python plot_fig7_profit.py        # 生成图7
```

### 方法2: 使用批处理脚本
```bash
cd figurePlot
plot_all_figures.bat
```

---

## 数据文件位置

所有生成的数据文件位于 `figurePlot/data/`:
- `fig1_queueing_latency_boxplot.json` - 5种机制 ✅
- `fig2_latency_ratio_bar.json` - 5种机制 ✅
- `fig3_kde_distribution.json` - 5种机制 ✅
- `fig4_cdf.json` - 5种机制 ✅
- `fig5_ctx_ratio.json` - 5种机制 ✅
- `fig6_cumulative_subsidy.json` - 3种有补贴机制 ✅
- `fig7_proposer_profit_cdf.json` - CTX vs ITX ✅

---

## 验证

运行以下命令验证所有数据文件包含5种机制：

```bash
cd figurePlot/data
python -c "import json; files = ['fig1_queueing_latency_boxplot.json', 'fig2_latency_ratio_bar.json', 'fig5_ctx_ratio.json']; [print(f'\n{f}:', list(json.load(open(f, encoding='utf-8')).keys())) for f in files]"
```

预期输出：
```
fig1_queueing_latency_boxplot.json: ['Monoxide', 'R=0', 'R=E(f_B)', 'R=E(f_A)+E(f_B)', 'R=1 ETH/CTX']
fig2_latency_ratio_bar.json: ['Monoxide', 'R=0', 'R=E(f_B)', 'R=E(f_A)+E(f_B)', 'R=1 ETH/CTX']
fig5_ctx_ratio.json: ['Monoxide', 'R=0', 'R=E(f_B)', 'R=E(f_A)+E(f_B)', 'R=1 ETH/CTX']
```

---

## 完成时间
2025-11-20 00:30 UTC+08:00
