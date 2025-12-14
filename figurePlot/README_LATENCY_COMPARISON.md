# 时延比较图生成器

## 功能说明

该脚本用于生成四种方法的时延对比图：
- **PID**: PID控制器方法
- **Lagrangian**: 拉格朗日优化方法
- **RB**: 基准方法 (R=E(f_B), 补贴等于预期费用)
- **Monoxide**: Monoxide基准方法

## 生成的图表

脚本会生成一个包含4个子图的综合对比图：

1. **CTX平均时延柱状图**: 直观对比各方法的CTX平均时延
2. **CTX/ITX时延比率**: 显示跨片交易相对片内交易的时延比率
3. **CTX时延分布箱线图**: 展示各方法时延的分布特征（中位数、四分位数、异常值）
4. **多指标分组对比**: 同时对比平均值、中位数和95分位数

## 使用方法

### 方法1: 使用批处理文件（推荐）

```bash
run_latency_comparison.bat
```

### 方法2: 直接运行Python脚本

```bash
python plot_latency_comparison.py
```

## 数据要求

脚本需要以下实验数据目录存在：

```
../expTest_PID/result/supervisor_measureOutput/Tx_Details.csv
../expTest_Lagrangian/result/supervisor_measureOutput/Tx_Details.csv
../expTest_R_EB/result/supervisor_measureOutput/Tx_Details.csv
../expTest_monoxide/result/supervisor_measureOutput/Tx_Details.csv
```

**注意**: 如果某些实验数据不存在，脚本会跳过该方法，使用现有数据生成图表。

## 输出文件

- **图表文件**: `figures/latency_comparison_4methods.png`
- **分辨率**: 300 DPI (高质量)
- **格式**: PNG

## 统计指标

脚本会计算并显示以下指标：

### 时延指标
- CTX平均时延 (ms)
- CTX中位数时延 (ms)
- CTX标准差 (ms)
- CTX 25分位数、75分位数、95分位数
- ITX平均时延 (ms)
- CTX/ITX时延比率

### 交易统计
- CTX数量
- ITX数量
- 总交易数
- CTX占比 (%)

## 评级标准

时延比率评级：
- 🟢 **优秀**: < 1.5x
- 🟡 **良好**: 1.5x - 2.0x
- 🟠 **一般**: 2.0x - 3.0x
- 🔴 **较差**: > 3.0x

## 依赖包

```
pandas
matplotlib
numpy
scipy
```

安装依赖：
```bash
pip install -r requirements.txt
```

## 配色方案

- **PID**: 蓝色 (#3498DB)
- **Lagrangian**: 红色 (#E74C3C)
- **RB**: 橙色 (#F39C12)
- **Monoxide**: 绿色 (#27AE60)

## 故障排除

### 问题1: 找不到数据文件

**解决方案**: 
1. 确保已运行相应的实验生成数据
2. 检查实验数据目录路径是否正确
3. 验证 `Tx_Details.csv` 文件是否存在

### 问题2: 图表显示异常

**解决方案**:
1. 检查数据文件是否完整
2. 确认CSV文件格式正确
3. 查看控制台输出的错误信息

### 问题3: 中文显示乱码

**解决方案**:
- Windows系统会自动使用SimHei字体
- 如果仍有问题，可以修改脚本中的字体设置

## 示例输出

```
============================================================
Justitia 时延比较图生成器
PID vs Lagrangian vs RB vs Monoxide
============================================================

正在加载 PID 数据...
✓ 成功加载 PID 数据: 25000 条记录

正在加载 Lagrangian 数据...
✓ 成功加载 Lagrangian 数据: 25000 条记录

正在加载 RB 数据...
✓ 成功加载 RB 数据: 25000 条记录

正在加载 Monoxide 数据...
✓ 成功加载 Monoxide 数据: 25000 条记录

====================================================================================================
时延统计对比表
====================================================================================================

方法              CTX平均(ms)     CTX中位数(ms)   CTX标准差(ms)   时延比率         评级           
----------------------------------------------------------------------------------------------------
PID             15234.56        14500.00        3245.67         1.45            🟢 优秀        
Lagrangian      18567.89        17800.00        4123.45         1.78            🟡 良好        
RB              25678.90        24500.00        5678.90         2.45            🟠 一般        
Monoxide        32456.78        31200.00        6789.01         3.12            🔴 较差        

============================================================
生成时延比较图
============================================================
✓ 图表已保存: figures\latency_comparison_4methods.png

============================================================
✓ 时延比较图生成成功！
============================================================
```

## 扩展功能

如需添加更多对比方法，可以修改脚本中的 `EXPERIMENT_PATHS` 字典：

```python
EXPERIMENT_PATHS = {
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian/result/supervisor_measureOutput',
    'RB': '../expTest_R0/result/supervisor_measureOutput',
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    # 添加新方法
    'NewMethod': '../expTest_NewMethod/result/supervisor_measureOutput'
}
```

同时在 `COLORS` 字典中添加对应的颜色配置。
