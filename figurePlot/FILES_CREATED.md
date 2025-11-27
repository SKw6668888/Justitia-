# Justitia 数据分析与绘图工具 - 文件清单

## 📁 已创建的文件

### 核心程序 (2个)

1. **justitia_data_analyzer.py** (主程序1)
   - 功能: 从实验结果中提取和分析数据
   - 输入: 5个实验文件夹的CSV文件
   - 输出: data/目录下的JSON数据文件
   - 行数: ~400行

2. **justitia_plot_all.py** (主程序2)
   - 功能: 根据分析数据生成7张图表
   - 输入: data/目录下的JSON文件
   - 输出: figures/目录下的PNG图表
   - 行数: ~450行

### 辅助工具 (3个)

3. **generate_configs.py**
   - 功能: 自动生成5种机制的配置文件
   - 输出: 5个paramsConfig_*.json文件
   - 行数: ~150行

4. **test_tools.py**
   - 功能: 测试工具是否正常工作
   - 包含: 5个测试用例
   - 行数: ~250行

5. **requirements.txt**
   - 功能: Python依赖包列表
   - 包含: numpy, pandas, matplotlib, seaborn, scipy

### 运行脚本 (2个)

6. **run_analysis.bat** (Windows)
   - 功能: 一键运行数据分析和绘图
   - 自动检查依赖、运行分析、生成图表

7. **run_analysis.sh** (Linux/Mac)
   - 功能: 同上，适用于Unix系统
   - 需要执行: chmod +x run_analysis.sh

### 文档 (3个)

8. **README_PLOTTING.md** (完整文档)
   - 内容: 详细的使用指南
   - 包含: 实验流程、图表说明、故障排除
   - 长度: ~500行

9. **QUICK_START.md** (快速入门)
   - 内容: 简化的快速上手指南
   - 包含: 核心步骤、检查清单
   - 长度: ~200行

10. **FILES_CREATED.md** (本文件)
    - 内容: 文件清单和说明

## 📊 生成的数据文件 (运行后)

### data/ 目录 (8个JSON文件)

1. `fig1_queueing_latency_boxplot.json` - 图1数据
2. `fig2_latency_ratio_bar.json` - 图2数据
3. `fig3_kde_distribution.json` - 图3数据
4. `fig4_cdf.json` - 图4数据
5. `fig5_ctx_ratio.json` - 图5数据
6. `fig6_cumulative_subsidy.json` - 图6数据
7. `fig7_proposer_profit_cdf.json` - 图7数据
8. `summary_report.json` - 数据摘要报告

### figures/ 目录 (7个PNG图表)

1. `fig1_ctx_latency_boxplot.png` - CTX排队延迟箱线图
2. `fig2_latency_ratio_bar.png` - CTX/ITX延迟比值柱状图
3. `fig3_latency_kde.png` - CTX延迟KDE分布
4. `fig4_latency_cdf.png` - CTX延迟CDF
5. `fig5_ctx_ratio.png` - 区块中CTX占比
6. `fig6_cumulative_subsidy.png` - 累计补贴发行量
7. `fig7_proposer_profit_cdf.png` - 提议者利润分布

## 🎯 7张图表详细说明

### 图1: Queueing latency of CTXs under various subsidy solutions
- **类型**: 箱线图 (Boxplot)
- **X轴**: 5种补贴机制
- **Y轴**: 排队延迟（秒）
- **目的**: 展示不同机制下CTX延迟的分布和离散程度

### 图2: Queueing latency declines as subsidy RAB increases
- **类型**: 柱状图 (Bar Chart)
- **X轴**: 5种补贴机制
- **Y轴**: CTX/ITX延迟比值
- **目的**: 对比CTX相对于ITX的延迟，1.0表示公平

### 图3: The queueing latency distribution of confirmed CTXs (KDE)
- **类型**: 核密度估计曲线 (KDE)
- **X轴**: 排队延迟（0-50秒）
- **Y轴**: 概率密度
- **目的**: 平滑展示延迟分布

### 图4: Cumulative Distribution Function (CDF) of the queueing latency
- **类型**: 累积分布函数 (CDF)
- **X轴**: 排队延迟（秒）
- **Y轴**: 累积概率（0-1）
- **目的**: 显示延迟的累积分布

### 图5: The ratio of CTXs out of all TXs in packaged blocks
- **类型**: 柱状图 (Bar Chart)
- **X轴**: 5种补贴机制
- **Y轴**: CTX占比（0-100%）
- **目的**: 展示CTX的优先级效果

### 图6: The cumulative tokens issued
- **类型**: 折线图（对数坐标）
- **X轴**: 区块高度
- **Y轴**: 累计补贴（ETH，对数刻度）
- **目的**: 展示补贴成本

### 图7: Proposer's profit with R_AB = E(f_B) (ensuring fairness)
- **类型**: CDF（对数坐标）
- **X轴**: 单笔交易利润（ETH，对数刻度）
- **Y轴**: 累积概率（0-1）
- **目的**: 验证公平性

## 🔄 工作流程

```
1. 生成配置
   generate_configs.py
   ↓
   生成5个配置文件

2. 运行实验 (5次)
   使用不同配置运行blockEmulator
   ↓
   生成5个expTest_*文件夹

3. 数据分析
   justitia_data_analyzer.py
   ↓
   生成data/目录下的JSON文件

4. 生成图表
   justitia_plot_all.py
   ↓
   生成figures/目录下的PNG图表
```

## 📦 文件大小估计

- Python脚本: ~1.5 MB (总计)
- 文档: ~50 KB
- 数据文件: ~1-5 MB (取决于实验规模)
- 图表文件: ~5-10 MB (7张高清图)

## 🔧 技术栈

- **语言**: Python 3.7+
- **数据处理**: NumPy, Pandas
- **可视化**: Matplotlib, Seaborn
- **统计分析**: SciPy
- **格式**: JSON (数据), PNG (图表)

## 📝 代码统计

- 总行数: ~1,500行
- 函数数: ~30个
- 类数: 2个
- 测试用例: 5个

## ✅ 功能特性

### 数据分析器
- ✓ 自动加载5种机制的数据
- ✓ 提取7种不同类型的指标
- ✓ 生成JSON格式的中间数据
- ✓ 输出详细的摘要报告
- ✓ 错误处理和警告提示

### 绘图程序
- ✓ 生成7张高质量图表
- ✓ 统一的配色方案
- ✓ 自动调整布局
- ✓ 300 DPI高分辨率
- ✓ 专业的学术风格

### 辅助工具
- ✓ 配置文件生成器
- ✓ 完整的测试套件
- ✓ 一键运行脚本
- ✓ 跨平台支持

## 🎓 使用场景

1. **论文实验**: 生成INFOCOM论文所需的7张图表
2. **性能对比**: 对比不同补贴机制的效果
3. **参数调优**: 快速测试不同参数配置
4. **教学演示**: 展示Justitia机制的工作原理

## 📚 相关文档

- `README_PLOTTING.md` - 完整使用指南
- `QUICK_START.md` - 快速入门
- `../justitia.md` - Justitia机制详细文档
- `../JUSTITIA_IMPLEMENTATION_SUMMARY.md` - 实现总结

## 🚀 下一步

1. 运行测试: `python test_tools.py`
2. 生成配置: `python generate_configs.py`
3. 运行实验: 使用5种不同配置
4. 分析数据: `python justitia_data_analyzer.py`
5. 生成图表: `python justitia_plot_all.py`

或直接运行: `run_analysis.bat` (Windows) / `./run_analysis.sh` (Linux/Mac)

---

**创建日期**: 2025-11-17
**版本**: 1.0
**作者**: Justitia Project Team
