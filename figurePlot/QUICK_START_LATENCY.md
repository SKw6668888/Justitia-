# 🚀 时延比较图 - 快速开始指南

## 一分钟快速使用

### Windows用户
```bash
cd figurePlot
run_latency_comparison.bat
```

### Linux/Mac用户
```bash
cd figurePlot
python plot_latency_comparison.py
```

## 生成的图表

**输出文件**: `figures/latency_comparison_4methods.png`

**包含内容**:
- ✅ CTX平均时延柱状图
- ✅ CTX/ITX时延比率对比
- ✅ CTX时延分布箱线图
- ✅ 多指标分组对比（平均值、中位数、95分位数）

## 对比的方法

| 方法 | 说明 | 颜色 |
|------|------|------|
| PID | PID控制器 | 🔵 蓝色 |
| Lagrangian | 拉格朗日优化 | 🔴 红色 |
| RB | 基准方法(R=E(f_B)) | 🟠 橙色 |
| Monoxide | Monoxide基准 | 🟢 绿色 |

## 前置条件

### 1. 数据文件
确保以下目录存在数据文件 `Tx_Details.csv`:
```
expTest_PID/result/supervisor_measureOutput/
expTest_Lagrangian/result/supervisor_measureOutput/
expTest_R_EB/result/supervisor_measureOutput/
expTest_monoxide/result/supervisor_measureOutput/
```

### 2. Python依赖
```bash
pip install pandas matplotlib numpy scipy
```

或使用：
```bash
pip install -r requirements.txt
```

## 输出示例

### 控制台输出
```
============================================================
Justitia 时延比较图生成器
PID vs Lagrangian vs RB vs Monoxide
============================================================

正在加载 PID 数据...
✓ 成功加载 PID 数据: 25000 条记录

====================================================================================================
时延统计对比表
====================================================================================================

方法              CTX平均(ms)     CTX中位数(ms)   CTX标准差(ms)   时延比率         评级           
----------------------------------------------------------------------------------------------------
PID             15234.56        14500.00        3245.67         1.45            🟢 优秀        
Lagrangian      18567.89        17800.00        4123.45         1.78            🟡 良好        

✓ 图表已保存: figures\latency_comparison_4methods.png
```

## 评级标准

- 🟢 **优秀**: 时延比率 < 1.5x
- 🟡 **良好**: 时延比率 1.5x - 2.0x
- 🟠 **一般**: 时延比率 2.0x - 3.0x
- 🔴 **较差**: 时延比率 > 3.0x

## 常见问题

### Q: 找不到数据文件怎么办？
**A**: 先运行相应的实验生成数据，或者脚本会自动跳过缺失的方法。

### Q: 只有部分方法的数据可以运行吗？
**A**: 可以！脚本会使用现有数据生成图表。

### Q: 如何修改图表样式？
**A**: 编辑 `plot_latency_comparison.py` 中的配色方案和绘图参数。

## 详细文档

- 📖 **完整说明**: `README_LATENCY_COMPARISON.md`
- 📊 **功能总结**: `LATENCY_COMPARISON_SUMMARY.md`

## 技术支持

如遇问题，请检查：
1. ✅ Python版本 (建议 3.7+)
2. ✅ 依赖包已安装
3. ✅ 数据文件路径正确
4. ✅ CSV文件格式正确

---

**提示**: 该工具参考了 `figurePlot` 目录下现有的绘图代码风格，与项目其他图表保持一致。
