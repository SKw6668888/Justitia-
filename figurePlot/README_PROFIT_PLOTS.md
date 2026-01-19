# 矿工利润可视化脚本使用说明

## 📊 新增的三个可视化脚本

基于 `8.py` 的结构，新增了三个专门用于展示 **proposer profit** 分布特征的可视化脚本：

---

### 1️⃣ **`9_boxplot_profit.py`** - 箱线图（展示离群值）

**功能**: 
- 绘制所有方案的 proposer profit 箱线图
- 清晰展示中位数、四分位数、离群点分布

**突出特点**:
- 箱体：25%-75%分位数范围（IQR）
- 胡须：1.5×IQR范围
- **红色离群点**：超出胡须范围的极端值
- P99值标注在箱体上方

**运行**:
```bash
cd figurePlot
python 9_boxplot_profit.py
```

**输出**: `figures/9_proposer_profit_boxplot.png`

**预期结果**:
- **Lagrangian**: 箱体紧凑，离群点少且数值低
- **Monoxide/其他方案**: 箱体宽，大量高值离群点（长尾现象）

---

### 2️⃣ **`10_kde_profit.py`** - KDE概率密度图（展示长尾形态）

**功能**:
- 使用高斯核密度估计（KDE）绘制概率密度函数（PDF）
- 直观展示分布的"峰值"和"尾部"形态

**突出特点**:
- **高峰 + 短尾** = 理想分布（Lagrangian目标）
- **低峰 + 长尾** = 不公平分布（需改进）
- Lagrangian曲线有阴影填充，便于识别

**运行**:
```bash
cd figurePlot
python 10_kde_profit.py
```

**输出**: `figures/10_proposer_profit_kde.png`

**预期结果**:
- **Lagrangian**: 
  - 峰值高且陡（利润集中）
  - 右侧尾部迅速归零（无长尾）
  - "胖头短尾"形态
- **其他方案**: 
  - 峰值低且平缓
  - 右侧拖着长长的尾巴
  - "瘦头长尾"形态

---

### 3️⃣ **`11_tail_latency_bar.py`** - P95/P99柱状图（尾部延迟对比）

**功能**:
- 并排显示所有方案的 P95 和 P99 值
- 量化展示尾部延迟的具体改进

**突出特点**:
- 左图：P95对比
- 右图：P99对比
- 柱顶标注具体数值（Gwei）
- 底部显示 Lagrangian 相对于 Monoxide 的改进百分比

**运行**:
```bash
cd figurePlot
python 11_tail_latency_bar.py
```

**输出**: `figures/11_tail_latency_p95_p99.png`

**预期结果**:
- **Lagrangian**: 柱子最矮（P95/P99值最低）
- **改进说明**: 例如 "P95: 35.2% reduction, P99: 42.8% reduction"

---

## 🚀 一键运行所有脚本

**使用统一脚本**:
```bash
cd figurePlot
python run_all_profit_plots.py
```

这会依次运行三个脚本，并在最后给出执行总结。

---

## 📁 数据来源

所有脚本读取相同的数据源：
```
expTest_monoxide/result/supervisor_measureOutput/Tx_Details.csv
expTest_R_EB/result/supervisor_measureOutput/Tx_Details.csv
expTest_PID/result/supervisor_measureOutput/Tx_Details.csv
expTest_Lagrangian/result/supervisor_measureOutput/Tx_Details.csv  ← 重点
expTest_R_EA_EB/result/supervisor_measureOutput/Tx_Details.csv
```

**确保运行实验后这些文件存在！**

---

## 🎨 配色方案（与 8.py 一致）

| 方案 | 颜色 | 十六进制 |
|------|------|---------|
| Monoxide | 橙色 | #F39C12 |
| R_EB | 红色 | #E74C3C |
| PID | 紫色 | #9B59B6 |
| **Lagrangian** | **绿色** | **#27AE60** |
| R_EA_EB | 棕色 | #8B4513 |

---

## 📊 学术论文使用建议

### 图表组合策略：

1. **主图（CDF）** - 展示整体分布 → 使用 `8.py`
2. **辅助图1（Box Plot）** - 展示离群值 → 使用 `9_boxplot_profit.py`
3. **辅助图2（KDE）** - 展示长尾形态 → 使用 `10_kde_profit.py`
4. **数值图（P95/P99 Bar）** - 量化改进 → 使用 `11_tail_latency_bar.py`

### 论文中的论述顺序：

1. 先用 **CDF** 说明"尾部延迟"问题存在
2. 再用 **Box Plot** 指出"离群点数量"的差异
3. 接着用 **KDE** 解释"分布形态"的本质区别
4. 最后用 **P95/P99 Bar** 给出"具体改进数值"

---

## 🔍 故障排查

### 常见问题：

**Q: 提示"文件不存在"**
A: 确保已运行对应实验，生成 `Tx_Details.csv` 文件

**Q: 图表显示不全**
A: 调整脚本中的 `figsize` 参数，例如 `figsize=(16, 9)`

**Q: KDE 曲线异常**
A: 可能数据量太少或分布极端，检查数据有效性

---

## 📝 修改建议

### 自定义标题：
修改脚本中的 `ax.set_title()` 部分

### 调整Y轴范围：
修改 `ax.set_ylim()` 或 `y_max` 计算逻辑

### 更改颜色：
修改 `COLORS` 字典

---

**Happy Plotting! 🎉**
