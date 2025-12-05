"""
PID Controller Mode Analysis Script
分析 PID 控制器模式的实验结果
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import warnings
import os
import json
warnings.filterwarnings('ignore')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配置
RESULT_DIR = '../expTest_PID/result/supervisor_measureOutput'
OUTPUT_DIR = '../expTest_PID/analysis'
MODE_NAME = 'PID Controller'

def ensure_output_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"创建输出目录: {OUTPUT_DIR}")

def load_pid_config():
    """从配置文件读取 PID 参数"""
    config_path = '../paramsConfig_PID.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        pid_params = {
            'Kp': config.get('JustitiaPID_Kp', 1.5),
            'Ki': config.get('JustitiaPID_Ki', 0.1),
            'Kd': config.get('JustitiaPID_Kd', 0.05),
            'TargetUtilization': config.get('JustitiaPID_TargetUtilization', 0.7),
            'CapacityB': config.get('JustitiaPID_CapacityB', 1000.0),
            'MinSubsidy': config.get('JustitiaPID_MinSubsidy', 0.0),
            'MaxSubsidy': config.get('JustitiaPID_MaxSubsidy', 5.0)
        }
        
        return pid_params
    except FileNotFoundError:
        print(f"⚠️  警告: 找不到配置文件 {config_path}，使用默认参数")
        return {
            'Kp': 1.5,
            'Ki': 0.1,
            'Kd': 0.05,
            'TargetUtilization': 0.7,
            'CapacityB': 1000.0,
            'MinSubsidy': 0.0,
            'MaxSubsidy': 5.0
        }
    except Exception as e:
        print(f"⚠️  警告: 读取配置文件出错 ({e})，使用默认参数")
        return {
            'Kp': 1.5,
            'Ki': 0.1,
            'Kd': 0.05,
            'TargetUtilization': 0.7,
            'CapacityB': 1000.0,
            'MinSubsidy': 0.0,
            'MaxSubsidy': 5.0
        }

def load_data():
    """加载实验数据"""
    print(f"\n{'='*80}")
    print(f"加载 {MODE_NAME} 模式实验数据")
    print(f"{'='*80}")
    
    tx_details_path = os.path.join(RESULT_DIR, 'Tx_Details.csv')
    latency_summary_path = os.path.join(RESULT_DIR, 'Transaction_Confirm_Latency.csv')
    
    if not os.path.exists(tx_details_path):
        print(f"❌ 错误: 找不到数据文件 {tx_details_path}")
        print("请先运行 run_PID_simple.bat 生成实验数据")
        return None, None
    
    df = pd.read_csv(tx_details_path)
    latency_df = pd.read_csv(latency_summary_path) if os.path.exists(latency_summary_path) else None
    
    print(f"✓ 成功加载交易数据: {len(df)} 条记录")
    if latency_df is not None:
        print(f"✓ 成功加载时延数据")
    
    return df, latency_df

def classify_transactions(df):
    """分类交易类型"""
    cross_shard_mask = (df['Relay1 Tx commit timestamp (not a relay tx -> nil)'].notna()) | \
                      (df['Relay2 Tx commit timestamp (not a relay tx -> nil)'].notna())
    inner_shard_mask = ~cross_shard_mask
    return cross_shard_mask, inner_shard_mask

def analyze_ctx_percentage(df, cross_shard_mask, inner_shard_mask):
    """分析CTX占比"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - CTX交易占比分析")
    print(f"{'='*80}")
    
    total_txs = len(df)
    ctx_count = cross_shard_mask.sum()
    itx_count = inner_shard_mask.sum()
    ctx_percentage = (ctx_count / total_txs * 100) if total_txs > 0 else 0
    
    print(f"\n成功打包进区块的交易统计:")
    print(f"{'类型':<20} {'数量':<15} {'占比':<15}")
    print("-" * 50)
    print(f"{'总交易数':<20} {total_txs:<15,} {100.0:<15.2f}%")
    print(f"{'跨片交易 (CTX)':<20} {ctx_count:<15,} {ctx_percentage:<15.2f}%")
    print(f"{'片内交易 (ITX)':<20} {itx_count:<15,} {(100-ctx_percentage):<15.2f}%")
    
    return ctx_percentage, ctx_count, itx_count

def analyze_profit(df, cross_shard_mask, inner_shard_mask):
    """分析矿工利润"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 矿工利润分析")
    print(f"{'='*80}")
    
    # 查找费用和补贴列
    fee_columns = [col for col in df.columns if 'fee' in col.lower() and 'proposer' in col.lower()]
    subsidy_columns = [col for col in df.columns if 'subsidy' in col.lower() and 'r' in col.lower()]
    
    if not fee_columns or not subsidy_columns:
        print("\n⚠️  未找到费用或补贴数据列")
        return None
    
    fee_col = fee_columns[0]
    subsidy_col = subsidy_columns[0]
    
    # 转换为数值
    df[fee_col] = pd.to_numeric(df[fee_col], errors='coerce')
    df[subsidy_col] = pd.to_numeric(df[subsidy_col], errors='coerce')
    
    # CTX 利润 = 费用 + 补贴
    ctx_fees = df[cross_shard_mask][fee_col].fillna(0)
    ctx_subsidies = df[cross_shard_mask][subsidy_col].fillna(0)
    ctx_total_profit = ctx_fees + ctx_subsidies
    
    # ITX 利润 = 仅费用
    itx_fees = df[inner_shard_mask][fee_col].fillna(0)
    
    wei_to_eth = 1e18
    
    print(f"\n矿工利润统计 (单位: ETH):")
    print(f"{'指标':<20} {'CTX':<20} {'ITX':<20} {'比率':<15}")
    print("-" * 75)
    print(f"{'平均费用':<20} {ctx_fees.mean()/wei_to_eth:<20.10f} {itx_fees.mean()/wei_to_eth:<20.10f} "
          f"{(ctx_fees.mean()/itx_fees.mean() if itx_fees.mean() > 0 else 0):<15.2f}x")
    print(f"{'平均补贴':<20} {ctx_subsidies.mean()/wei_to_eth:<20.10f} {'N/A':<20} {'-':<15}")
    print(f"{'平均总利润':<20} {ctx_total_profit.mean()/wei_to_eth:<20.10f} {itx_fees.mean()/wei_to_eth:<20.10f} "
          f"{(ctx_total_profit.mean()/itx_fees.mean() if itx_fees.mean() > 0 else 0):<15.2f}x")
    
    print(f"\n补贴统计:")
    print(f"  总补贴发放:          {ctx_subsidies.sum()/wei_to_eth:.6f} ETH")
    print(f"  补贴/费用比:         {(ctx_subsidies.mean()/ctx_fees.mean() if ctx_fees.mean() > 0 else 0):.2f}x")
    print(f"  补贴占总利润:        {(ctx_subsidies.mean()/ctx_total_profit.mean()*100 if ctx_total_profit.mean() > 0 else 0):.2f}%")
    
    profit_ratio = ctx_total_profit.mean() / itx_fees.mean() if itx_fees.mean() > 0 else 0
    print(f"\n利润激励评估:")
    if profit_ratio > 1.2:
        print(f"  🟢 CTX利润显著高于ITX ({profit_ratio:.2f}x)，激励充足")
    elif profit_ratio > 0.8:
        print(f"  🟡 CTX与ITX利润接近 ({profit_ratio:.2f}x)，激励适中")
    else:
        print(f"  🔴 CTX利润低于ITX ({profit_ratio:.2f}x)，激励不足")
    
    return {
        'ctx_fees': ctx_fees,
        'ctx_subsidies': ctx_subsidies,
        'ctx_total_profit': ctx_total_profit,
        'itx_fees': itx_fees,
        'profit_ratio': profit_ratio
    }

def analyze_queue_control(df):
    """分析PID控制器对队列的控制效果"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 队列控制效果分析")
    print(f"{'='*80}")
    
    # 这里需要根据实际数据结构调整
    # 假设有队列长度相关的数据
    print("\n⚠️  注意: 队列控制分析需要额外的队列长度数据")
    print("建议在实验中记录每个区块的队列长度变化")

def analyze_latency(df, cross_shard_mask, inner_shard_mask):
    """分析时延"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 交易时延分析")
    print(f"{'='*80}")
    
    latency_column = 'Confirmed latency of this tx (ms)'
    cross_shard_latency = df[cross_shard_mask][latency_column].dropna()
    inner_shard_latency = df[inner_shard_mask][latency_column].dropna()
    
    print(f"\n时延统计:")
    print(f"{'交易类型':<15} {'平均(ms)':<12} {'中位数(ms)':<12} {'标准差(ms)':<12} {'95%分位(ms)':<12}")
    print("-" * 70)
    
    if len(inner_shard_latency) > 0:
        print(f"{'片内交易':<15} {inner_shard_latency.mean():<12.2f} {inner_shard_latency.median():<12.2f} "
              f"{inner_shard_latency.std():<12.2f} {inner_shard_latency.quantile(0.95):<12.2f}")
    
    if len(cross_shard_latency) > 0:
        print(f"{'跨片交易':<15} {cross_shard_latency.mean():<12.2f} {cross_shard_latency.median():<12.2f} "
              f"{cross_shard_latency.std():<12.2f} {cross_shard_latency.quantile(0.95):<12.2f}")
    
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        ratio = cross_shard_latency.mean() / inner_shard_latency.mean()
        print(f"\n时延比率: CTX是ITX的 {ratio:.2f} 倍")
        
        # 统计检验
        statistic, p_value = stats.mannwhitneyu(cross_shard_latency, inner_shard_latency, alternative='two-sided')
        print(f"Mann-Whitney U检验 p值: {p_value:.6f}")
        if p_value < 0.05:
            print("✓ CTX和ITX的时延分布存在显著差异 (p < 0.05)")
        else:
            print("✓ CTX和ITX的时延分布无显著差异 (p >= 0.05)")
    
    return cross_shard_latency, inner_shard_latency

def plot_latency_distribution(cross_shard_latency, inner_shard_latency):
    """绘制时延分布图"""
    print(f"\n生成时延分布图...")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 直方图
    axes[0].hist(inner_shard_latency, bins=50, alpha=0.6, label='ITX', color='blue', density=True)
    axes[0].hist(cross_shard_latency, bins=50, alpha=0.6, label='CTX', color='red', density=True)
    axes[0].set_xlabel('Latency (ms)')
    axes[0].set_ylabel('Density')
    axes[0].set_title(f'{MODE_NAME} - Latency Distribution')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 箱线图
    data_to_plot = [inner_shard_latency, cross_shard_latency]
    axes[1].boxplot(data_to_plot, labels=['ITX', 'CTX'])
    axes[1].set_ylabel('Latency (ms)')
    axes[1].set_title(f'{MODE_NAME} - Latency Boxplot')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(OUTPUT_DIR, 'PID_latency_distribution.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ 保存图表: {output_path}")
    plt.close()

def analyze_pid_parameters():
    """分析PID参数设置"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 参数配置")
    print(f"{'='*80}")
    
    # 从配置文件读取参数
    params = load_pid_config()
    
    print("\nPID控制器参数:")
    print(f"  Kp (比例增益):        {params['Kp']}")
    print(f"  Ki (积分增益):        {params['Ki']}")
    print(f"  Kd (微分增益):        {params['Kd']}")
    print(f"  目标利用率:           {params['TargetUtilization']*100:.0f}%")
    print(f"  队列容量:             {params['CapacityB']:.0f}")
    print(f"  最小补贴倍数:         {params['MinSubsidy']}")
    print(f"  最大补贴倍数:         {params['MaxSubsidy']}")
    
    # 智能分析参数特点
    print("\n参数特点分析:")
    
    # Kp 分析
    if params['Kp'] >= 2.0:
        print(f"  • Kp={params['Kp']}: 强比例控制，快速响应误差")
    elif params['Kp'] >= 1.0:
        print(f"  • Kp={params['Kp']}: 标准比例控制")
    else:
        print(f"  • Kp={params['Kp']}: 弱比例控制，响应温和")
    
    # Ki 分析
    if params['Ki'] >= 0.2:
        print(f"  • Ki={params['Ki']}: 强积分作用，快速消除稳态误差")
    elif params['Ki'] >= 0.05:
        print(f"  • Ki={params['Ki']}: 标准积分作用")
    else:
        print(f"  • Ki={params['Ki']}: 弱积分作用")
    
    # Kd 分析
    if params['Kd'] >= 0.1:
        print(f"  • Kd={params['Kd']}: 强微分作用，抑制震荡")
    elif params['Kd'] >= 0.01:
        print(f"  • Kd={params['Kd']}: 标准微分作用")
    else:
        print(f"  • Kd={params['Kd']}: 弱微分作用")
    
    # 目标利用率分析
    target_util = params['TargetUtilization']
    if target_util >= 0.8:
        print(f"  • 目标利用率={target_util*100:.0f}%: 高利用率，激进策略")
    elif target_util >= 0.6:
        print(f"  • 目标利用率={target_util*100:.0f}%: 标准利用率")
    else:
        print(f"  • 目标利用率={target_util*100:.0f}%: 低利用率，保守策略")
    
    # 补贴范围分析
    if params['MaxSubsidy'] >= 5.0:
        print(f"  • 补贴范围=[{params['MinSubsidy']}, {params['MaxSubsidy']}]: 宽松补贴上限")
    elif params['MaxSubsidy'] >= 3.0:
        print(f"  • 补贴范围=[{params['MinSubsidy']}, {params['MaxSubsidy']}]: 标准补贴上限")
    else:
        print(f"  • 补贴范围=[{params['MinSubsidy']}, {params['MaxSubsidy']}]: 严格补贴上限")
    
    # 综合评估
    print("\n综合评估:")
    if params['Kp'] >= 1.5 and params['Ki'] >= 0.1:
        print("  ⚡ 激进模式：快速响应，强力控制")
    elif params['Kp'] >= 1.0 and params['Ki'] >= 0.05:
        print("  ✅ 标准模式：平衡的控制策略")
    else:
        print("  🔵 保守模式：温和控制，稳定优先")

def generate_summary_report(ctx_percentage, ctx_count, itx_count, cross_shard_latency, inner_shard_latency):
    """生成总结报告"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 实验总结")
    print(f"{'='*80}")
    
    print(f"\n📊 关键指标:")
    print(f"  • CTX占比:           {ctx_percentage:.2f}%")
    print(f"  • CTX数量:           {ctx_count:,}")
    print(f"  • ITX数量:           {itx_count:,}")
    
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        ratio = cross_shard_latency.mean() / inner_shard_latency.mean()
        print(f"  • 时延比率:          {ratio:.2f}x")
        print(f"  • CTX平均时延:       {cross_shard_latency.mean():.2f} ms")
        print(f"  • ITX平均时延:       {inner_shard_latency.mean():.2f} ms")
    
    print(f"\n🎯 PID控制器特点:")
    print(f"  ✓ 自动调节队列长度到目标值")
    print(f"  ✓ 响应快速，适合实时控制")
    print(f"  ✓ 无需离线训练")
    print(f"  ✗ 无全局预算约束")
    
    # 效果评估
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        ratio = cross_shard_latency.mean() / inner_shard_latency.mean()
        if ratio < 1.5:
            print(f"\n🟢 效果评级: 优秀 (时延比率 {ratio:.2f}x < 1.5x)")
        elif ratio < 2.0:
            print(f"\n🟡 效果评级: 良好 (时延比率 {ratio:.2f}x < 2.0x)")
        elif ratio < 3.0:
            print(f"\n🟠 效果评级: 一般 (时延比率 {ratio:.2f}x < 3.0x)")
        else:
            print(f"\n🔴 效果评级: 较差 (时延比率 {ratio:.2f}x >= 3.0x)")

def main():
    """主函数"""
    print(f"\n{'#'*80}")
    print(f"# {MODE_NAME} Mode - Experimental Results Analysis")
    print(f"# PID 控制器模式 - 实验结果分析")
    print(f"{'#'*80}")
    
    ensure_output_dir()
    
    # 加载数据
    df, latency_df = load_data()
    if df is None:
        return
    
    # 分类交易
    cross_shard_mask, inner_shard_mask = classify_transactions(df)
    
    # 分析CTX占比
    ctx_percentage, ctx_count, itx_count = analyze_ctx_percentage(df, cross_shard_mask, inner_shard_mask)
    
    # 分析利润
    profit_data = analyze_profit(df, cross_shard_mask, inner_shard_mask)
    
    # 分析时延
    cross_shard_latency, inner_shard_latency = analyze_latency(df, cross_shard_mask, inner_shard_mask)
    
    # 绘制图表
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        plot_latency_distribution(cross_shard_latency, inner_shard_latency)
    
    # 分析PID参数
    analyze_pid_parameters()
    
    # 生成总结报告
    generate_summary_report(ctx_percentage, ctx_count, itx_count, cross_shard_latency, inner_shard_latency)
    
    print(f"\n{'='*80}")
    print(f"分析完成！结果保存在: {OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    input("按Enter键关闭窗口...")

if __name__ == "__main__":
    main()
