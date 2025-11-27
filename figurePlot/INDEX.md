# Justitia 数据分析与绘图工具 - 索引

## 🎯 快速导航

### 新手入门
👉 **[QUICK_START.md](QUICK_START.md)** - 5分钟快速上手指南

### 完整文档
📖 **[README_PLOTTING.md](README_PLOTTING.md)** - 详细使用手册

### 文件清单
📋 **[FILES_CREATED.md](FILES_CREATED.md)** - 所有文件说明

---

## 🚀 三步快速开始

### 第1步: 测试工具
```bash
python test_tools.py
```

### 第2步: 生成配置并运行实验
```bash
python generate_configs.py
# 然后使用生成的5个配置文件分别运行实验
```

### 第3步: 分析数据并生成图表
```bash
# Windows
run_analysis.bat

# Linux/Mac
./run_analysis.sh
```

---

## 📊 生成的7张图表

| # | 图表名称 | 文件名 | 类型 |
|---|---------|--------|------|
| 1 | CTX排队延迟箱线图 | fig1_ctx_latency_boxplot.png | Boxplot |
| 2 | CTX/ITX延迟比值 | fig2_latency_ratio_bar.png | Bar Chart |
| 3 | CTX延迟KDE分布 | fig3_latency_kde.png | KDE Curve |
| 4 | CTX延迟CDF | fig4_latency_cdf.png | CDF |
| 5 | 区块中CTX占比 | fig5_ctx_ratio.png | Bar Chart |
| 6 | 累计补贴发行量 | fig6_cumulative_subsidy.png | Line Chart (Log) |
| 7 | 提议者利润分布 | fig7_proposer_profit_cdf.png | CDF (Log) |

---

## 🔧 核心工具

### 主程序
- **justitia_data_analyzer.py** - 数据分析器
- **justitia_plot_all.py** - 绘图程序

### 辅助工具
- **generate_configs.py** - 配置生成器
- **test_tools.py** - 测试工具
- **run_analysis.bat/sh** - 一键运行脚本

---

## 📁 目录结构

```
figurePlot/
├── 📄 核心程序
│   ├── justitia_data_analyzer.py    # 数据分析器
│   └── justitia_plot_all.py         # 绘图程序
│
├── 🔧 辅助工具
│   ├── generate_configs.py          # 配置生成器
│   ├── test_tools.py                # 测试工具
│   ├── run_analysis.bat             # Windows脚本
│   └── run_analysis.sh              # Linux/Mac脚本
│
├── 📖 文档
│   ├── INDEX.md                     # 本文件
│   ├── QUICK_START.md               # 快速入门
│   ├── README_PLOTTING.md           # 完整手册
│   └── FILES_CREATED.md             # 文件清单
│
├── 📦 配置
│   └── requirements.txt             # Python依赖
│
├── 📊 输出目录（运行后生成）
│   ├── data/                        # JSON数据文件
│   └── figures/                     # PNG图表文件
│
└── 🗂️ 旧版工具（保留）
    ├── ctx_fee_latency_analysis.py
    ├── justitia_effectiveness_analysis.py
    ├── tx_distribution_relayMethod.py
    └── tx_pool_vary.py
```

---

## 🎓 5种补贴机制

| 机制 | 配置 | 说明 |
|------|------|------|
| **Monoxide** | EnableJustitia=0 | 基线方案（无Justitia） |
| **R=0** | SubsidyMode=0 | 无补贴 |
| **R=E(f_B)** | SubsidyMode=1 | 推荐方案 ✅ |
| **R=E(f_A)+E(f_B)** | SubsidyMode=2 | 激进方案 |
| **R=1 ETH/CTX** | SubsidyMode=4 | 固定补贴 |

---

## 📝 工作流程

```mermaid
graph LR
    A[生成配置] --> B[运行实验x5]
    B --> C[数据分析]
    C --> D[生成图表]
    D --> E[论文图表]
```

### 详细步骤

1. **准备阶段**
   - 安装依赖: `pip install -r requirements.txt`
   - 测试工具: `python test_tools.py`

2. **配置阶段**
   - 生成配置: `python generate_configs.py`
   - 获得5个配置文件

3. **实验阶段** (重复5次)
   - 复制配置到根目录
   - 运行实验: `./blockEmulator.exe`
   - 重命名结果文件夹

4. **分析阶段**
   - 数据分析: `python justitia_data_analyzer.py`
   - 生成图表: `python justitia_plot_all.py`

5. **完成**
   - 查看 `figures/` 目录
   - 获得7张高质量图表

---

## 🔍 常见问题速查

### Q: 如何开始？
**A:** 阅读 [QUICK_START.md](QUICK_START.md)

### Q: 工具是否正常？
**A:** 运行 `python test_tools.py`

### Q: 如何生成配置？
**A:** 运行 `python generate_configs.py`

### Q: 找不到数据文件？
**A:** 检查实验文件夹命名是否正确（expTest_monoxide等）

### Q: 图表显示异常？
**A:** 确保实验运行足够长（建议100+ epochs）

### Q: 需要什么Python版本？
**A:** Python 3.7 或更高版本

---

## 📊 预期结果

### 延迟改善
- Monoxide: CTX延迟 > ITX延迟 (基线)
- R=0: 轻微改善
- R=E(f_B): 显著改善 ✅
- R=E(f_A)+E(f_B): 更大改善
- R=1 ETH/CTX: 最大改善（但成本高）

### CTX占比
- Monoxide: ~20-30%
- R=E(f_B): ~40-50% ✅
- R=1 ETH/CTX: ~60-70%

### 补贴成本
- R=0: 0 ETH
- R=E(f_B): 适中 ✅
- R=1 ETH/CTX: 很高

---

## 🎨 图表特点

- ✅ 高分辨率 (300 DPI)
- ✅ 统一配色方案
- ✅ 专业学术风格
- ✅ 清晰的标签和图例
- ✅ 适合论文发表

---

## 📚 相关文档

### 项目文档
- `../justitia.md` - Justitia机制详细说明
- `../JUSTITIA_IMPLEMENTATION_SUMMARY.md` - 实现总结
- `../JUSTITIA_QUICKSTART.md` - Justitia快速指南

### 本目录文档
- `QUICK_START.md` - 快速入门
- `README_PLOTTING.md` - 完整手册
- `FILES_CREATED.md` - 文件清单

---

## 🛠️ 技术支持

### 依赖问题
```bash
pip install -r requirements.txt
```

### 测试问题
```bash
python test_tools.py
```

### 数据问题
检查 `data/summary_report.json`

### 图表问题
查看 `figures/` 目录

---

## ✅ 完成检查清单

### 准备工作
- [ ] Python 3.7+ 已安装
- [ ] 依赖包已安装
- [ ] 测试工具通过

### 实验阶段
- [ ] 生成5个配置文件
- [ ] 完成5次实验
- [ ] 正确命名结果文件夹
- [ ] 验证CSV文件存在

### 分析阶段
- [ ] 数据分析成功
- [ ] 生成7张图表
- [ ] 检查图表质量
- [ ] 查看摘要报告

---

## 🎉 成功标志

当你看到以下内容时，表示成功：

```
figures/
├── fig1_ctx_latency_boxplot.png     ✓
├── fig2_latency_ratio_bar.png       ✓
├── fig3_latency_kde.png             ✓
├── fig4_latency_cdf.png             ✓
├── fig5_ctx_ratio.png               ✓
├── fig6_cumulative_subsidy.png      ✓
└── fig7_proposer_profit_cdf.png     ✓
```

---

## 📞 获取帮助

1. 查看文档: [README_PLOTTING.md](README_PLOTTING.md)
2. 运行测试: `python test_tools.py`
3. 查看示例: `data/summary_report.json`
4. 提交Issue: GitHub Issues

---

**最后更新**: 2025-11-17  
**版本**: 1.0  
**状态**: ✅ 生产就绪

---

## 🚀 立即开始

```bash
# 1. 测试工具
python test_tools.py

# 2. 生成配置
python generate_configs.py

# 3. 运行实验（5次）
# ... 使用不同配置运行 blockEmulator

# 4. 分析和绘图
run_analysis.bat  # Windows
# 或
./run_analysis.sh  # Linux/Mac
```

**祝实验顺利！** 🎊
