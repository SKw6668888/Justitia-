"""
Lagrangian Optimization Mode Analysis Script
分析拉格朗日优化模式的实验结果
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
RESULT_DIR = '../expTest_Lagrangian/result/supervisor_measureOutput'
OUTPUT_DIR = '../expTest_Lagrangian/analysis'
MODE_NAME = 'Lagrangian Optimization'

def ensure_output_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"创建输出目录: {OUTPUT_DIR}")

def load_lagrangian_config():
    """从配置文件读取拉格朗日参数"""
    config_path = '../paramsConfig_Lagrangian.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        lag_params = {
            'Alpha': config.get('JustitiaLag_Alpha', 0.01),
            'WindowSize': config.get('JustitiaLag_WindowSize', 1000.0),
            'MinLambda': config.get('JustitiaLag_MinLambda', 1.0),
            'MaxLambda': config.get('JustitiaLag_MaxLambda', 10.0),
            'CongestionExp': config.get('JustitiaLag_CongestionExp', 2.0),
            'MaxInflation': config.get('JustitiaLag_MaxInflation', 5000000000000000000)
        }
        
        return lag_params
    except FileNotFoundError:
        print(f"⚠️  警告: 找不到配置文件 {config_path}，使用默认参数")
        return {
            'Alpha': 0.01,
            'WindowSize': 1000.0,
            'MinLambda': 1.0,
            'MaxLambda': 10.0,
            'CongestionExp': 2.0,
            'MaxInflation': 5000000000000000000
        }
    except Exception as e:
        print(f"⚠️  警告: 读取配置文件出错 ({e})，使用默认参数")
        return {
            'Alpha': 0.01,
            'WindowSize': 1000.0,
            'MinLambda': 1.0,
            'MaxLambda': 10.0,
            'CongestionExp': 2.0,
            'MaxInflation': 5000000000000000000
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
        print("请先运行 run_Lagrangian_simple.bat 生成实验数据")
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
        print(f"     ⚠️  可能原因: 预算约束过严，Lambda过高削减补贴")
    
    return {
        'ctx_fees': ctx_fees,
        'ctx_subsidies': ctx_subsidies,
        'ctx_total_profit': ctx_total_profit,
        'itx_fees': itx_fees,
        'profit_ratio': profit_ratio,
        'total_subsidy': ctx_subsidies.sum()
    }

def analyze_budget_constraint(df, cross_shard_mask):
    """分析预算约束执行情况"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 预算约束分析")
    print(f"{'='*80}")
    
    # 查找补贴相关列
    subsidy_columns = [col for col in df.columns if 'subsidy' in col.lower()]
    
    if subsidy_columns:
        subsidy_col = subsidy_columns[0]
        print(f"\n找到补贴列: {subsidy_col}")
        
        # 计算总补贴
        ctx_subsidies = df[cross_shard_mask][subsidy_col].fillna(0)
        total_subsidy = ctx_subsidies.sum()
        
        # 从配置文件读取真实的预算限制
        params = load_lagrangian_config()
        max_inflation = params['MaxInflation']
        
        print(f"\n预算执行情况:")
        print(f"  总补贴发放:          {total_subsidy:.2e} wei")
        print(f"  总补贴发放:          {total_subsidy/1e18:.6f} ETH")
        print(f"  预算限制:            {max_inflation:.2e} wei ({max_inflation/1e18:.6f} ETH)")
        print(f"  预算使用率:          {(total_subsidy/max_inflation*100):.2f}%")
        
        if total_subsidy <= max_inflation:
            print(f"\n✓ 预算约束满足: 总补贴 <= 预算限制")
        else:
            print(f"\n✗ 预算约束违反: 总补贴 > 预算限制")
            print(f"  超出预算:            {(total_subsidy-max_inflation)/1e18:.6f} ETH")
        
        # 补贴分布
        print(f"\n补贴分布:")
        print(f"  平均补贴:            {ctx_subsidies.mean():.2e} wei ({ctx_subsidies.mean()/1e18:.10f} ETH)")
        print(f"  中位数补贴:          {ctx_subsidies.median():.2e} wei")
        print(f"  最小补贴:            {ctx_subsidies.min():.2e} wei")
        print(f"  最大补贴:            {ctx_subsidies.max():.2e} wei")
        
        return total_subsidy, max_inflation
    else:
        print("\n⚠️  未找到补贴数据列")
        return None, None

def analyze_shadow_price():
    """分析影子价格演化"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 影子价格分析")
    print(f"{'='*80}")
    
    print("\n⚠️  注意: 影子价格分析需要额外的时间序列数据")
    print("建议在实验中记录每个区块的影子价格 (Lambda) 变化")
    print("\n影子价格 (Lambda) 的作用:")
    print("  • Lambda 越大 → 补贴削减越多 → 控制通胀")
    print("  • Lambda 越小 → 补贴削减越少 → 鼓励处理")

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

def plot_results(cross_shard_latency, inner_shard_latency, total_subsidy, max_inflation):
    """绘制分析图表"""
    print(f"\n生成分析图表...")
    
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # 1. 时延分布直方图
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(inner_shard_latency, bins=50, alpha=0.6, label='ITX', color='blue', density=True)
    ax1.hist(cross_shard_latency, bins=50, alpha=0.6, label='CTX', color='red', density=True)
    ax1.set_xlabel('Latency (ms)')
    ax1.set_ylabel('Density')
    ax1.set_title(f'{MODE_NAME} - Latency Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 时延箱线图
    ax2 = fig.add_subplot(gs[0, 1])
    data_to_plot = [inner_shard_latency, cross_shard_latency]
    ax2.boxplot(data_to_plot, labels=['ITX', 'CTX'])
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title(f'{MODE_NAME} - Latency Boxplot')
    ax2.grid(True, alpha=0.3)
    
    # 3. 预算使用情况
    if total_subsidy is not None and max_inflation is not None:
        ax3 = fig.add_subplot(gs[1, 0])
        categories = ['Used', 'Remaining']
        values = [total_subsidy/1e18, (max_inflation-total_subsidy)/1e18 if total_subsidy < max_inflation else 0]
        colors = ['#ff6b6b' if total_subsidy > max_inflation else '#51cf66', '#e9ecef']
        ax3.bar(categories, values, color=colors)
        ax3.axhline(y=max_inflation/1e18, color='r', linestyle='--', label='Budget Limit')
        ax3.set_ylabel('Subsidy (ETH)')
        ax3.set_title(f'{MODE_NAME} - Budget Usage')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. 时延对比
    ax4 = fig.add_subplot(gs[1, 1])
    metrics = ['Mean', 'Median', '95th Percentile']
    itx_values = [inner_shard_latency.mean(), inner_shard_latency.median(), inner_shard_latency.quantile(0.95)]
    ctx_values = [cross_shard_latency.mean(), cross_shard_latency.median(), cross_shard_latency.quantile(0.95)]
    
    x = np.arange(len(metrics))
    width = 0.35
    ax4.bar(x - width/2, itx_values, width, label='ITX', color='blue', alpha=0.7)
    ax4.bar(x + width/2, ctx_values, width, label='CTX', color='red', alpha=0.7)
    ax4.set_ylabel('Latency (ms)')
    ax4.set_title(f'{MODE_NAME} - Latency Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle(f'{MODE_NAME} - Comprehensive Analysis', fontsize=16, fontweight='bold')
    
    output_path = os.path.join(OUTPUT_DIR, 'Lagrangian_comprehensive_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ 保存图表: {output_path}")
    plt.close()

def analyze_lagrangian_parameters():
    """分析拉格朗日参数设置"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 参数配置")
    print(f"{'='*80}")
    
    # 从配置文件读取参数
    params = load_lagrangian_config()
    
    print("\n拉格朗日优化参数:")
    print(f"  Alpha (学习率):       {params['Alpha']}")
    print(f"  WindowSize:           {params['WindowSize']}")
    print(f"  MinLambda:            {params['MinLambda']}")
    print(f"  MaxLambda:            {params['MaxLambda']}")
    print(f"  CongestionExp:        {params['CongestionExp']}")
    print(f"  MaxInflation:         {params['MaxInflation']/1e18:.6f} ETH")
    
    # 智能分析参数特点
    print("\n参数特点分析:")
    
    # Alpha 分析
    if params['Alpha'] >= 0.1:
        print(f"  • Alpha={params['Alpha']}: 快速修正模式，响应迅速")
    elif params['Alpha'] >= 0.05:
        print(f"  • Alpha={params['Alpha']}: 中速修正，平衡响应")
    else:
        print(f"  • Alpha={params['Alpha']}: 慢速修正，平滑稳定")
    
    # MinLambda 分析
    if params['MinLambda'] >= 2.0:
        print(f"  • MinLambda={params['MinLambda']}: 高起点，强力压制补贴")
    elif params['MinLambda'] >= 1.5:
        print(f"  • MinLambda={params['MinLambda']}: 中等压制")
    else:
        print(f"  • MinLambda={params['MinLambda']}: 标准起点")
    
    # CongestionExp 分析
    if params['CongestionExp'] >= 2.0:
        print(f"  • CongestionExp={params['CongestionExp']}: 二次响应，对拥塞敏感")
    elif params['CongestionExp'] == 1.0:
        print(f"  • CongestionExp={params['CongestionExp']}: 线性响应，取消拥塞特权")
    else:
        print(f"  • CongestionExp={params['CongestionExp']}: 次线性响应")
    
    # MaxInflation 分析
    max_inflation_eth = params['MaxInflation'] / 1e18
    if max_inflation_eth < 0.01:
        print(f"  • MaxInflation={max_inflation_eth:.6f} ETH: 极度紧缩，预算恐慌模式")
    elif max_inflation_eth < 1.0:
        print(f"  • MaxInflation={max_inflation_eth:.6f} ETH: 紧缩预算")
    elif max_inflation_eth < 5.0:
        print(f"  • MaxInflation={max_inflation_eth:.1f} ETH: 标准预算")
    else:
        print(f"  • MaxInflation={max_inflation_eth:.1f} ETH: 宽松预算")
    
    # 综合评估
    print("\n综合评估:")
    if params['MinLambda'] >= 2.0 and max_inflation_eth < 0.01 and params['Alpha'] >= 0.1:
        print("  🔥 极端压制模式：强力压制 CTX 利润")
    elif params['MinLambda'] >= 1.5 or max_inflation_eth < 1.0:
        print("  ⚡ 激进模式：较强的补贴控制")
    else:
        print("  ✅ 标准模式：平衡的补贴策略")

def generate_summary_report(ctx_percentage, ctx_count, itx_count, cross_shard_latency, inner_shard_latency, total_subsidy, max_inflation):
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
    
    if total_subsidy is not None and max_inflation is not None:
        print(f"  • 总补贴:            {total_subsidy/1e18:.6f} ETH")
        print(f"  • 预算限制:          {max_inflation/1e18:.1f} ETH")
        print(f"  • 预算使用率:        {(total_subsidy/max_inflation*100):.2f}%")
    
    print(f"\n🎯 拉格朗日优化特点:")
    print(f"  ✓ 强制执行全局预算约束")
    print(f"  ✓ 系统级优化")
    print(f"  ✓ 影子价格自动调节")
    print(f"  ✓ 理论最优性保证")
    
    # 预算约束评估
    if total_subsidy is not None and max_inflation is not None:
        if total_subsidy <= max_inflation:
            print(f"\n🟢 预算约束: 满足 (使用率 {(total_subsidy/max_inflation*100):.2f}%)")
        else:
            print(f"\n🔴 预算约束: 违反 (超出 {((total_subsidy-max_inflation)/1e18):.6f} ETH)")
    
    # 效果评估
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        ratio = cross_shard_latency.mean() / inner_shard_latency.mean()
        if ratio < 1.5:
            print(f"🟢 效果评级: 优秀 (时延比率 {ratio:.2f}x < 1.5x)")
        elif ratio < 2.0:
            print(f"🟡 效果评级: 良好 (时延比率 {ratio:.2f}x < 2.0x)")
        elif ratio < 3.0:
            print(f"🟠 效果评级: 一般 (时延比率 {ratio:.2f}x < 3.0x)")
        else:
            print(f"🔴 效果评级: 较差 (时延比率 {ratio:.2f}x >= 3.0x)")

def main():
    """主函数"""
    print(f"\n{'#'*80}")
    print(f"# {MODE_NAME} Mode - Experimental Results Analysis")
    print(f"# 拉格朗日优化模式 - 实验结果分析")
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
    
    # 分析预算约束
    total_subsidy, max_inflation = analyze_budget_constraint(df, cross_shard_mask)
    
    # 分析影子价格
    analyze_shadow_price()
    
    # 分析时延
    cross_shard_latency, inner_shard_latency = analyze_latency(df, cross_shard_mask, inner_shard_mask)
    
    # 绘制图表
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        plot_results(cross_shard_latency, inner_shard_latency, total_subsidy, max_inflation)
    
    # 分析参数
    analyze_lagrangian_parameters()
    
    # 生成总结报告
    generate_summary_report(ctx_percentage, ctx_count, itx_count, cross_shard_latency, inner_shard_latency, total_subsidy, max_inflation)
    
    print(f"\n{'='*80}")
    print(f"分析完成！结果保存在: {OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    input("按Enter键关闭窗口...")

if __name__ == "__main__":
    main()
