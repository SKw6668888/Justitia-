"""
Comparative Analysis Script for All Three Modes
对比分析三种模式 (PID, Lagrangian, RL) 的实验结果
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import warnings
import os
warnings.filterwarnings('ignore')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配置
MODES = {
    'PID': {
        'dir': '../expTest_PID/result/supervisor_measureOutput',
        'name': 'PID Controller',
        'color': '#3498db'
    },
    'Lagrangian': {
        'dir': '../expTest_Lagrangian/result/supervisor_measureOutput',
        'name': 'Lagrangian Optimization',
        'color': '#e74c3c'
    },
    'RL': {
        'dir': '../expTest_RL/result/supervisor_measureOutput',
        'name': 'Reinforcement Learning',
        'color': '#2ecc71'
    }
}

OUTPUT_DIR = '../comparison_analysis'

def ensure_output_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"创建输出目录: {OUTPUT_DIR}")

def load_mode_data(mode_key):
    """加载单个模式的数据"""
    mode_dir = MODES[mode_key]['dir']
    tx_details_path = os.path.join(mode_dir, 'Tx_Details.csv')
    
    if not os.path.exists(tx_details_path):
        print(f"⚠️  {mode_key} 模式数据不存在: {tx_details_path}")
        return None
    
    df = pd.read_csv(tx_details_path)
    print(f"✓ 加载 {mode_key} 数据: {len(df)} 条记录")
    return df

def classify_transactions(df):
    """分类交易类型"""
    cross_shard_mask = (df['Relay1 Tx commit timestamp (not a relay tx -> nil)'].notna()) | \
                      (df['Relay2 Tx commit timestamp (not a relay tx -> nil)'].notna())
    inner_shard_mask = ~cross_shard_mask
    return cross_shard_mask, inner_shard_mask

def extract_metrics(df, mode_key):
    """提取关键指标"""
    cross_shard_mask, inner_shard_mask = classify_transactions(df)
    
    latency_column = 'Confirmed latency of this tx (ms)'
    cross_shard_latency = df[cross_shard_mask][latency_column].dropna()
    inner_shard_latency = df[inner_shard_mask][latency_column].dropna()
    
    total_txs = len(df)
    ctx_count = cross_shard_mask.sum()
    ctx_percentage = (ctx_count / total_txs * 100) if total_txs > 0 else 0
    
    # 提取利润相关数据
    fee_columns = [col for col in df.columns if 'fee' in col.lower() and 'proposer' in col.lower()]
    subsidy_columns = [col for col in df.columns if 'subsidy' in col.lower() and 'r' in col.lower()]
    
    profit_metrics = {}
    if fee_columns and subsidy_columns:
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
        
        profit_metrics = {
            'ctx_mean_fee': ctx_fees.mean(),
            'ctx_mean_subsidy': ctx_subsidies.mean(),
            'ctx_mean_profit': ctx_total_profit.mean(),
            'itx_mean_fee': itx_fees.mean(),
            'itx_mean_profit': itx_fees.mean(),
            'profit_ratio': (ctx_total_profit.mean() / itx_fees.mean()) if itx_fees.mean() > 0 else 0,
            'subsidy_ratio': (ctx_subsidies.mean() / ctx_fees.mean()) if ctx_fees.mean() > 0 else 0,
            'total_subsidy': ctx_subsidies.sum(),
            'ctx_fees': ctx_fees,
            'ctx_subsidies': ctx_subsidies,
            'ctx_total_profit': ctx_total_profit,
            'itx_fees': itx_fees
        }
    
    metrics = {
        'mode': mode_key,
        'total_txs': total_txs,
        'ctx_count': ctx_count,
        'ctx_percentage': ctx_percentage,
        'ctx_mean_latency': cross_shard_latency.mean() if len(cross_shard_latency) > 0 else 0,
        'ctx_median_latency': cross_shard_latency.median() if len(cross_shard_latency) > 0 else 0,
        'ctx_std_latency': cross_shard_latency.std() if len(cross_shard_latency) > 0 else 0,
        'ctx_p95_latency': cross_shard_latency.quantile(0.95) if len(cross_shard_latency) > 0 else 0,
        'itx_mean_latency': inner_shard_latency.mean() if len(inner_shard_latency) > 0 else 0,
        'itx_median_latency': inner_shard_latency.median() if len(inner_shard_latency) > 0 else 0,
        'latency_ratio': (cross_shard_latency.mean() / inner_shard_latency.mean()) if len(inner_shard_latency) > 0 and inner_shard_latency.mean() > 0 else 0,
        'cross_shard_latency': cross_shard_latency,
        'inner_shard_latency': inner_shard_latency,
        **profit_metrics
    }
    
    return metrics

def print_comparison_table(all_metrics):
    """打印对比表格"""
    print(f"\n{'='*100}")
    print(f"三种模式对比分析")
    print(f"{'='*100}")
    
    print(f"\n1. 交易统计对比:")
    print(f"{'模式':<20} {'总交易数':<15} {'CTX数量':<15} {'CTX占比':<15}")
    print("-" * 65)
    for metrics in all_metrics:
        print(f"{MODES[metrics['mode']]['name']:<20} {metrics['total_txs']:<15,} "
              f"{metrics['ctx_count']:<15,} {metrics['ctx_percentage']:<15.2f}%")
    
    print(f"\n2. CTX时延对比:")
    print(f"{'模式':<20} {'平均(ms)':<12} {'中位数(ms)':<12} {'标准差(ms)':<12} {'95%分位(ms)':<12}")
    print("-" * 70)
    for metrics in all_metrics:
        print(f"{MODES[metrics['mode']]['name']:<20} {metrics['ctx_mean_latency']:<12.2f} "
              f"{metrics['ctx_median_latency']:<12.2f} {metrics['ctx_std_latency']:<12.2f} "
              f"{metrics['ctx_p95_latency']:<12.2f}")
    
    print(f"\n3. 时延比率对比 (CTX/ITX):")
    print(f"{'模式':<20} {'时延比率':<15} {'评级':<15}")
    print("-" * 50)
    for metrics in all_metrics:
        ratio = metrics['latency_ratio']
        if ratio < 1.5:
            rating = "🟢 优秀"
        elif ratio < 2.0:
            rating = "🟡 良好"
        elif ratio < 3.0:
            rating = "🟠 一般"
        else:
            rating = "🔴 较差"
        print(f"{MODES[metrics['mode']]['name']:<20} {ratio:<15.2f} {rating:<15}")
    
    # 添加利润分析
    if 'ctx_mean_profit' in all_metrics[0]:
        wei_to_eth = 1e18
        print(f"\n4. 矿工利润对比 (单位: ETH):")
        print(f"{'模式':<20} {'CTX费用':<15} {'CTX补贴':<15} {'CTX总利润':<15} {'ITX利润':<15} {'利润比率':<15}")
        print("-" * 95)
        for metrics in all_metrics:
            ctx_fee_eth = metrics.get('ctx_mean_fee', 0) / wei_to_eth
            ctx_subsidy_eth = metrics.get('ctx_mean_subsidy', 0) / wei_to_eth
            ctx_profit_eth = metrics.get('ctx_mean_profit', 0) / wei_to_eth
            itx_profit_eth = metrics.get('itx_mean_profit', 0) / wei_to_eth
            profit_ratio = metrics.get('profit_ratio', 0)
            print(f"{MODES[metrics['mode']]['name']:<20} {ctx_fee_eth:<15.10f} {ctx_subsidy_eth:<15.10f} "
                  f"{ctx_profit_eth:<15.10f} {itx_profit_eth:<15.10f} {profit_ratio:<15.2f}x")
        
        print(f"\n5. 补贴统计 (单位: ETH):")
        print(f"{'模式':<20} {'总补贴':<20} {'平均补贴':<20} {'补贴/费用比':<15}")
        print("-" * 75)
        for metrics in all_metrics:
            total_subsidy_eth = metrics.get('total_subsidy', 0) / wei_to_eth
            avg_subsidy_eth = metrics.get('ctx_mean_subsidy', 0) / wei_to_eth
            subsidy_ratio = metrics.get('subsidy_ratio', 0)
            print(f"{MODES[metrics['mode']]['name']:<20} {total_subsidy_eth:<20.6f} "
                  f"{avg_subsidy_eth:<20.10f} {subsidy_ratio:<15.2f}x")

def plot_comparison(all_metrics):
    """绘制对比图表"""
    print(f"\n生成对比图表...")
    
    # 检查是否有利润数据
    has_profit_data = 'ctx_mean_profit' in all_metrics[0]
    
    if has_profit_data:
        fig = plt.figure(figsize=(20, 16))
        gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.35)
    else:
        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)
    
    mode_names = [MODES[m['mode']]['name'] for m in all_metrics]
    colors = [MODES[m['mode']]['color'] for m in all_metrics]
    
    # 1. CTX占比对比
    ax1 = fig.add_subplot(gs[0, 0])
    ctx_percentages = [m['ctx_percentage'] for m in all_metrics]
    bars1 = ax1.bar(mode_names, ctx_percentages, color=colors, alpha=0.7)
    ax1.set_ylabel('CTX Percentage (%)')
    ax1.set_title('CTX Transaction Percentage')
    ax1.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, ctx_percentages):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom')
    
    # 2. CTX平均时延对比
    ax2 = fig.add_subplot(gs[0, 1])
    ctx_mean_latencies = [m['ctx_mean_latency'] for m in all_metrics]
    bars2 = ax2.bar(mode_names, ctx_mean_latencies, color=colors, alpha=0.7)
    ax2.set_ylabel('Mean Latency (ms)')
    ax2.set_title('CTX Mean Latency')
    ax2.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars2, ctx_mean_latencies):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}', ha='center', va='bottom')
    
    # 3. 时延比率对比
    ax3 = fig.add_subplot(gs[0, 2])
    latency_ratios = [m['latency_ratio'] for m in all_metrics]
    bars3 = ax3.bar(mode_names, latency_ratios, color=colors, alpha=0.7)
    ax3.axhline(y=1.5, color='g', linestyle='--', label='Excellent (1.5x)', alpha=0.5)
    ax3.axhline(y=2.0, color='orange', linestyle='--', label='Good (2.0x)', alpha=0.5)
    ax3.set_ylabel('Latency Ratio (CTX/ITX)')
    ax3.set_title('CTX to ITX Latency Ratio')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars3, latency_ratios):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}x', ha='center', va='bottom')
    
    # 4-6. CTX时延分布对比 (箱线图)
    for idx, metrics in enumerate(all_metrics):
        ax = fig.add_subplot(gs[1, idx])
        data_to_plot = [metrics['inner_shard_latency'], metrics['cross_shard_latency']]
        bp = ax.boxplot(data_to_plot, labels=['ITX', 'CTX'], patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor(colors[idx])
            patch.set_alpha(0.6)
        ax.set_ylabel('Latency (ms)')
        ax.set_title(f"{MODES[metrics['mode']]['name']}\nLatency Distribution")
        ax.grid(True, alpha=0.3, axis='y')
    
    # 7. 综合时延对比 (分组柱状图)
    ax7 = fig.add_subplot(gs[2, :2])
    metrics_names = ['Mean', 'Median', '95th Percentile']
    x = np.arange(len(metrics_names))
    width = 0.25
    
    for idx, metrics in enumerate(all_metrics):
        values = [
            metrics['ctx_mean_latency'],
            metrics['ctx_median_latency'],
            metrics['ctx_p95_latency']
        ]
        offset = (idx - 1) * width
        ax7.bar(x + offset, values, width, label=MODES[metrics['mode']]['name'],
               color=colors[idx], alpha=0.7)
    
    ax7.set_ylabel('Latency (ms)')
    ax7.set_title('CTX Latency Metrics Comparison')
    ax7.set_xticks(x)
    ax7.set_xticklabels(metrics_names)
    ax7.legend()
    ax7.grid(True, alpha=0.3, axis='y')
    
    # 8. 性能雷达图
    ax8 = fig.add_subplot(gs[2, 2], projection='polar')
    
    # 归一化指标 (越小越好)
    categories = ['Latency\nRatio', 'Mean\nLatency', 'Std\nLatency']
    N = len(categories)
    
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    ax8.set_theta_offset(np.pi / 2)
    ax8.set_theta_direction(-1)
    ax8.set_xticks(angles[:-1])
    ax8.set_xticklabels(categories)
    
    for idx, metrics in enumerate(all_metrics):
        # 归一化到 0-1 (反转，越小越好)
        max_ratio = max([m['latency_ratio'] for m in all_metrics])
        max_mean = max([m['ctx_mean_latency'] for m in all_metrics])
        max_std = max([m['ctx_std_latency'] for m in all_metrics])
        
        values = [
            1 - (metrics['latency_ratio'] / max_ratio if max_ratio > 0 else 0),
            1 - (metrics['ctx_mean_latency'] / max_mean if max_mean > 0 else 0),
            1 - (metrics['ctx_std_latency'] / max_std if max_std > 0 else 0)
        ]
        values += values[:1]
        
        ax8.plot(angles, values, 'o-', linewidth=2, label=MODES[metrics['mode']]['name'],
                color=colors[idx])
        ax8.fill(angles, values, alpha=0.15, color=colors[idx])
    
    ax8.set_ylim(0, 1)
    ax8.set_title('Performance Radar Chart\n(Larger is Better)', y=1.08)
    ax8.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax8.grid(True)
    
    # 添加利润对比图表（如果有数据）
    if has_profit_data:
        wei_to_eth = 1e18
        
        # 9. CTX vs ITX 利润对比
        ax9 = fig.add_subplot(gs[3, 0])
        x = np.arange(len(mode_names))
        width = 0.35
        
        ctx_profits = [m.get('ctx_mean_profit', 0) / wei_to_eth for m in all_metrics]
        itx_profits = [m.get('itx_mean_profit', 0) / wei_to_eth for m in all_metrics]
        
        ax9.bar(x - width/2, ctx_profits, width, label='CTX', alpha=0.7)
        ax9.bar(x + width/2, itx_profits, width, label='ITX', alpha=0.7)
        ax9.set_ylabel('Mean Profit (ETH)')
        ax9.set_title('CTX vs ITX Miner Profit')
        ax9.set_xticks(x)
        ax9.set_xticklabels(mode_names, rotation=15, ha='right')
        ax9.legend()
        ax9.grid(True, alpha=0.3, axis='y')
        ax9.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        
        # 10. 利润比率对比
        ax10 = fig.add_subplot(gs[3, 1])
        profit_ratios = [m.get('profit_ratio', 0) for m in all_metrics]
        bars10 = ax10.bar(mode_names, profit_ratios, color=colors, alpha=0.7)
        ax10.axhline(y=1.0, color='r', linestyle='--', label='Equal Profit', alpha=0.5)
        ax10.set_ylabel('Profit Ratio (CTX/ITX)')
        ax10.set_title('CTX to ITX Profit Ratio')
        ax10.legend()
        ax10.grid(True, alpha=0.3, axis='y')
        for bar, val in zip(bars10, profit_ratios):
            height = bar.get_height()
            ax10.text(bar.get_x() + bar.get_width()/2., height,
                     f'{val:.2f}x', ha='center', va='bottom')
        
        # 11. 补贴效果分析
        ax11 = fig.add_subplot(gs[3, 2])
        x = np.arange(len(mode_names))
        width = 0.25
        
        ctx_fees = [m.get('ctx_mean_fee', 0) / wei_to_eth for m in all_metrics]
        ctx_subsidies = [m.get('ctx_mean_subsidy', 0) / wei_to_eth for m in all_metrics]
        
        ax11.bar(x - width/2, ctx_fees, width, label='Fee', color='#3498db', alpha=0.7)
        ax11.bar(x + width/2, ctx_subsidies, width, label='Subsidy', color='#e74c3c', alpha=0.7)
        ax11.set_ylabel('Amount (ETH)')
        ax11.set_title('CTX Fee vs Subsidy')
        ax11.set_xticks(x)
        ax11.set_xticklabels(mode_names, rotation=15, ha='right')
        ax11.legend()
        ax11.grid(True, alpha=0.3, axis='y')
        ax11.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
    
    plt.suptitle('Comprehensive Comparison of Three Modes', fontsize=18, fontweight='bold', y=0.995)
    
    output_path = os.path.join(OUTPUT_DIR, 'comprehensive_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ 保存对比图表: {output_path}")
    plt.close()

def generate_summary_report(all_metrics):
    """生成总结报告"""
    print(f"\n{'='*100}")
    print(f"总结与建议")
    print(f"{'='*100}")
    
    # 找出最佳模式
    best_latency_ratio = min(all_metrics, key=lambda x: x['latency_ratio'])
    best_ctx_latency = min(all_metrics, key=lambda x: x['ctx_mean_latency'])
    
    print(f"\n🏆 最佳性能:")
    print(f"  • 最低时延比率:      {MODES[best_latency_ratio['mode']]['name']} ({best_latency_ratio['latency_ratio']:.2f}x)")
    print(f"  • 最低CTX时延:       {MODES[best_ctx_latency['mode']]['name']} ({best_ctx_latency['ctx_mean_latency']:.2f} ms)")
    
    # 时延差异分析
    print(f"\n📊 时延差异原因分析:")
    print(f"\n  观察到的现象:")
    for metrics in all_metrics:
        mode_name = MODES[metrics['mode']]['name']
        ctx_latency = metrics['ctx_mean_latency']
        print(f"    • {mode_name:<25} CTX平均时延: {ctx_latency:>10,.0f} ms")
    
    print(f"\n  可能的原因:")
    print(f"    1. 补贴策略差异 → 影响矿工打包CTX的激励")
    print(f"    2. 队列拥塞程度 → 不同模式导致不同的队列长度")
    print(f"    3. CTX占比不同 → 影响整体处理效率")
    print(f"    4. 参数配置差异 → 不同模式的参数设置可能不够优化")
    
    # 利润激励分析
    if 'ctx_mean_profit' in all_metrics[0]:
        wei_to_eth = 1e18
        print(f"\n💰 利润激励分析:")
        print(f"\n  矿工打包CTX的利润激励:")
        for metrics in all_metrics:
            mode_name = MODES[metrics['mode']]['name']
            profit_ratio = metrics.get('profit_ratio', 0)
            ctx_profit = metrics.get('ctx_mean_profit', 0) / wei_to_eth
            itx_profit = metrics.get('itx_mean_profit', 0) / wei_to_eth
            subsidy_ratio = metrics.get('subsidy_ratio', 0)
            
            print(f"\n    {mode_name}:")
            print(f"      CTX利润:        {ctx_profit:.10f} ETH")
            print(f"      ITX利润:        {itx_profit:.10f} ETH")
            print(f"      利润比率:       {profit_ratio:.2f}x")
            print(f"      补贴/费用比:    {subsidy_ratio:.2f}x")
            
            if profit_ratio > 1.2:
                print(f"      ✓ CTX利润显著高于ITX，激励充足")
            elif profit_ratio > 0.8:
                print(f"      • CTX与ITX利润接近，激励适中")
            else:
                print(f"      ✗ CTX利润低于ITX，激励不足！")
        
        print(f"\n  关键发现:")
        print(f"    • 如果利润比率 > 1.0，说明补贴有效激励了矿工")
        print(f"    • 如果利润比率 < 1.0，矿工更倾向打包ITX")
        print(f"    • 时延与利润激励应该呈负相关（激励越高，时延越低）")
    
    print(f"\n📋 模式特点总结:")
    print(f"\n  PID 控制器:")
    print(f"    ✓ 简单易用，无需训练")
    print(f"    ✓ 响应快速")
    print(f"    ✗ 无全局预算约束")
    print(f"    • 适合需要快速部署的场景")
    
    print(f"\n  拉格朗日优化:")
    print(f"    ✓ 强制预算约束")
    print(f"    ✓ 理论最优性")
    print(f"    • 需要调整参数（Alpha, Lambda范围）")
    print(f"    • 可能因预算约束导致补贴不足")
    
    print(f"\n  强化学习:")
    print(f"    ✓ 学习最优策略")
    print(f"    ✓ 多目标权衡")
    print(f"    • 需要离线训练（可选）")
    print(f"    • 启发式策略可能需要优化")
    
    print(f"\n💡 改进建议:")
    
    # 针对每个模式给出具体建议
    for metrics in all_metrics:
        mode_name = MODES[metrics['mode']]['name']
        mode_key = metrics['mode']
        ctx_latency = metrics['ctx_mean_latency']
        latency_ratio = metrics['latency_ratio']
        
        print(f"\n  {mode_name}:")
        
        if mode_key == 'PID':
            if ctx_latency > 20000:
                print(f"    • 增大 Kp 参数以提高响应速度")
                print(f"    • 增大 MaxSubsidy 以提供更多补贴")
            print(f"    • 监控队列长度是否达到目标值")
        
        elif mode_key == 'Lagrangian':
            if ctx_latency > 100000:
                print(f"    ⚠️  时延过高！可能原因：")
                print(f"       - 预算约束过严，补贴不足")
                print(f"       - Alpha 学习率过小，调整缓慢")
                print(f"       - Lambda 上限过高，过度削减补贴")
                print(f"    • 建议增大 MaxInflation 预算")
                print(f"    • 建议增大 Alpha 到 0.05-0.1")
                print(f"    • 建议降低 MaxLambda 到 5.0")
        
        elif mode_key == 'RL':
            if ctx_latency > 30000:
                print(f"    • 检查 Q-Table 策略是否合理")
                print(f"    • 考虑增大 MaxBeta 上限")
                print(f"    • 调整状态离散化阈值")
            print(f"    • 可以使用历史数据训练更好的策略")
    
    print(f"\n🎯 总体建议:")
    print(f"  • 追求简单快速 → PID 控制器")
    print(f"  • 需要预算约束 → 拉格朗日优化（需优化参数）")
    print(f"  • 追求最优性能 → 强化学习（需训练）")
    print(f"  • 如果时延差异大，优先检查补贴是否充足")

def main():
    """主函数"""
    print(f"\n{'#'*100}")
    print(f"# Comparative Analysis of Three Justitia Modes")
    print(f"# Justitia 三种模式对比分析")
    print(f"{'#'*100}")
    
    ensure_output_dir()
    
    # 加载所有模式的数据
    print(f"\n{'='*100}")
    print(f"加载实验数据")
    print(f"{'='*100}")
    
    all_metrics = []
    for mode_key in ['PID', 'Lagrangian', 'RL']:
        df = load_mode_data(mode_key)
        if df is not None:
            metrics = extract_metrics(df, mode_key)
            all_metrics.append(metrics)
    
    if len(all_metrics) == 0:
        print(f"\n❌ 错误: 没有找到任何实验数据")
        print(f"请先运行实验生成数据:")
        print(f"  - run_PID_simple.bat")
        print(f"  - run_Lagrangian_simple.bat")
        print(f"  - run_RL_simple.bat")
        input("\n按Enter键关闭窗口...")
        return
    
    if len(all_metrics) < 3:
        print(f"\n⚠️  警告: 只找到 {len(all_metrics)} 个模式的数据")
        print(f"建议运行所有三个模式以进行完整对比")
    
    # 打印对比表格
    print_comparison_table(all_metrics)
    
    # 绘制对比图表
    plot_comparison(all_metrics)
    
    # 生成总结报告
    generate_summary_report(all_metrics)
    
    print(f"\n{'='*100}")
    print(f"对比分析完成！结果保存在: {OUTPUT_DIR}")
    print(f"{'='*100}\n")
    
    input("按Enter键关闭窗口...")

if __name__ == "__main__":
    main()
