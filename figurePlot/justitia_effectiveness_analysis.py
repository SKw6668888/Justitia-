import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_and_process_data():
    """加载并处理交易数据"""
    # 读取交易详情数据
    tx_details_path = '../expTest/result/supervisor_measureOutput/Tx_Details.csv'
    df = pd.read_csv(tx_details_path)
    
    # 读取时延汇总数据
    latency_summary_path = '../expTest/result/supervisor_measureOutput/Transaction_Confirm_Latency.csv'
    latency_df = pd.read_csv(latency_summary_path)
    
    return df, latency_df

def classify_transactions(df):
    """分类交易类型"""
    # 跨片交易 (Cross-Shard Transactions)
    # 有Relay1或Relay2时间戳的交易
    cross_shard_mask = (df['Relay1 Tx commit timestamp (not a relay tx -> nil)'].notna()) | \
                      (df['Relay2 Tx commit timestamp (not a relay tx -> nil)'].notna())
    
    # 片内交易 (Inner-Shard Transactions)
    inner_shard_mask = ~cross_shard_mask
    
    return cross_shard_mask, inner_shard_mask

def analyze_justitia_effectiveness(df, cross_shard_mask, inner_shard_mask):
    """分析Justitia机制的有效性"""
    print("=" * 80)
    print("Justitia机制有效性分析")
    print("=" * 80)
    
    latency_column = 'Confirmed latency of this tx (ms)'
    cross_shard_latency = df[cross_shard_mask][latency_column]
    inner_shard_latency = df[inner_shard_mask][latency_column]
    
    # 1. 基本统计对比
    print("\n1. 基本时延统计对比:")
    print(f"{'交易类型':<15} {'平均时延(ms)':<15} {'中位数(ms)':<15} {'标准差(ms)':<15} {'95%分位数(ms)':<15}")
    print("-" * 80)
    
    inner_stats = {
        'mean': inner_shard_latency.mean(),
        'median': inner_shard_latency.median(),
        'std': inner_shard_latency.std(),
        'p95': inner_shard_latency.quantile(0.95)
    }
    
    cross_stats = {
        'mean': cross_shard_latency.mean(),
        'median': cross_shard_latency.median(),
        'std': cross_shard_latency.std(),
        'p95': cross_shard_latency.quantile(0.95)
    }
    
    print(f"{'片内交易':<15} {inner_stats['mean']:<15.2f} {inner_stats['median']:<15.2f} {inner_stats['std']:<15.2f} {inner_stats['p95']:<15.2f}")
    print(f"{'跨片交易':<15} {cross_stats['mean']:<15.2f} {cross_stats['median']:<15.2f} {cross_stats['std']:<15.2f} {cross_stats['p95']:<15.2f}")
    
    # 2. 时延比率分析
    print(f"\n2. 时延比率分析:")
    ratio_mean = cross_stats['mean'] / inner_stats['mean']
    ratio_median = cross_stats['median'] / inner_stats['median']
    ratio_p95 = cross_stats['p95'] / inner_stats['p95']
    
    print(f"跨片交易平均时延是片内交易的 {ratio_mean:.2f} 倍")
    print(f"跨片交易中位数时延是片内交易的 {ratio_median:.2f} 倍")
    print(f"跨片交易95%分位数时延是片内交易的 {ratio_p95:.2f} 倍")
    
    # 3. 统计显著性检验
    print(f"\n3. 统计显著性检验:")
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        # Mann-Whitney U检验（非参数检验）
        statistic, p_value = stats.mannwhitneyu(cross_shard_latency, inner_shard_latency, alternative='two-sided')
        print(f"Mann-Whitney U检验 p值: {p_value:.6f}")
        
        if p_value < 0.05:
            print("结论: 两种交易类型的时延分布存在显著差异 (p < 0.05)")
        else:
            print("结论: 两种交易类型的时延分布无显著差异 (p >= 0.05)")
        
        # t检验（参数检验）
        t_stat, t_p_value = stats.ttest_ind(cross_shard_latency, inner_shard_latency)
        print(f"独立样本t检验 p值: {t_p_value:.6f}")
    
    # 4. Justitia机制效果评估
    print(f"\n4. Justitia机制效果评估:")
    
    # 理想情况下，Justitia机制应该让跨片交易时延接近片内交易
    # 如果比率接近1，说明机制有效
    if ratio_mean < 1.5:
        effectiveness = "优秀"
        color = "🟢"
    elif ratio_mean < 2.0:
        effectiveness = "良好"
        color = "🟡"
    elif ratio_mean < 3.0:
        effectiveness = "一般"
        color = "🟠"
    else:
        effectiveness = "较差"
        color = "🔴"
    
    print(f"{color} Justitia机制效果评级: {effectiveness}")
    print(f"   跨片交易时延是片内交易的 {ratio_mean:.2f} 倍")
    
    if ratio_mean > 2.0:
        print("   ⚠️  建议检查:")
        print("   - JustitiaEnabled参数是否设置为1")
        print("   - 补贴策略是否正确配置")
        print("   - 交易池优先级排序是否生效")
        print("   - 网络延迟是否过高")
    
    # 5. 交易分布分析
    print(f"\n5. 交易分布分析:")
    total_txs = len(df)
    inner_count = len(inner_shard_latency)
    cross_count = len(cross_shard_latency)
    
    print(f"总交易数: {total_txs:,}")
    print(f"片内交易: {inner_count:,} ({inner_count/total_txs*100:.1f}%)")
    print(f"跨片交易: {cross_count:,} ({cross_count/total_txs*100:.1f}%)")
    
    # 6. 时延分布形状分析
    print(f"\n6. 时延分布形状分析:")
    
    # 计算偏度和峰度
    inner_skew = stats.skew(inner_shard_latency)
    cross_skew = stats.skew(cross_shard_latency)
    inner_kurt = stats.kurtosis(inner_shard_latency)
    cross_kurt = stats.kurtosis(cross_shard_latency)
    
    print(f"片内交易偏度: {inner_skew:.3f} ({'右偏' if inner_skew > 0 else '左偏' if inner_skew < 0 else '对称'})")
    print(f"跨片交易偏度: {cross_skew:.3f} ({'右偏' if cross_skew > 0 else '左偏' if cross_skew < 0 else '对称'})")
    print(f"片内交易峰度: {inner_kurt:.3f}")
    print(f"跨片交易峰度: {cross_kurt:.3f}")
    
    return ratio_mean, effectiveness

def create_justitia_analysis_plots(df, cross_shard_mask, inner_shard_mask):
    """创建Justitia机制分析图表"""
    
    latency_column = 'Confirmed latency of this tx (ms)'
    cross_shard_latency = df[cross_shard_mask][latency_column]
    inner_shard_latency = df[inner_shard_mask][latency_column]
    
    # 创建子图
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Justitia机制有效性分析', fontsize=16, fontweight='bold')
    
    # 1. 密度分布对比
    ax1 = axes[0, 0]
    sns.kdeplot(inner_shard_latency, color='green', label='片内交易', ax=ax1, alpha=0.7, linewidth=2)
    sns.kdeplot(cross_shard_latency, color='red', label='跨片交易', ax=ax1, alpha=0.7, linewidth=2)
    ax1.set_title('时延分布密度对比')
    ax1.set_xlabel('确认时延 (ms)')
    ax1.set_ylabel('密度')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 箱线图对比
    ax2 = axes[0, 1]
    data_for_box = [inner_shard_latency, cross_shard_latency]
    labels = ['片内交易', '跨片交易']
    box_plot = ax2.boxplot(data_for_box, labels=labels, patch_artist=True)
    
    colors = ['lightgreen', 'lightcoral']
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
    
    ax2.set_title('时延分布箱线图对比')
    ax2.set_ylabel('确认时延 (ms)')
    ax2.grid(True, alpha=0.3)
    
    # 3. 累积分布函数 (CDF)
    ax3 = axes[1, 0]
    
    def plot_cdf(data, label, color):
        sorted_data = np.sort(data)
        y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        ax3.plot(sorted_data, y, label=label, color=color, linewidth=2)
    
    plot_cdf(inner_shard_latency, '片内交易', 'green')
    plot_cdf(cross_shard_latency, '跨片交易', 'red')
    
    ax3.set_title('累积分布函数 (CDF)')
    ax3.set_xlabel('确认时延 (ms)')
    ax3.set_ylabel('累积概率')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 时延比率分析
    ax4 = axes[1, 1]
    
    # 计算不同分位数的比率
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    ratios = []
    
    for p in percentiles:
        inner_val = inner_shard_latency.quantile(p/100)
        cross_val = cross_shard_latency.quantile(p/100)
        if inner_val > 0:
            ratio = cross_val / inner_val
            ratios.append(ratio)
        else:
            ratios.append(0)
    
    bars = ax4.bar(range(len(percentiles)), ratios, color=['lightblue' if r < 2 else 'lightcoral' for r in ratios])
    ax4.set_title('不同分位数时延比率')
    ax4.set_xlabel('分位数 (%)')
    ax4.set_ylabel('跨片/片内时延比率')
    ax4.set_xticks(range(len(percentiles)))
    ax4.set_xticklabels([f'{p}%' for p in percentiles])
    ax4.axhline(y=1, color='black', linestyle='--', alpha=0.5, label='理想比率')
    ax4.axhline(y=2, color='red', linestyle='--', alpha=0.5, label='可接受上限')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 添加数值标签
    for i, (bar, ratio) in enumerate(zip(bars, ratios)):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, 
                f'{ratio:.2f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    return fig

def main():
    """主函数"""
    print("正在加载数据...")
    df, latency_df = load_and_process_data()
    
    print("正在分类交易类型...")
    cross_shard_mask, inner_shard_mask = classify_transactions(df)
    
    print("正在分析Justitia机制有效性...")
    ratio_mean, effectiveness = analyze_justitia_effectiveness(df, cross_shard_mask, inner_shard_mask)
    
    print("正在生成分析图表...")
    fig = create_justitia_analysis_plots(df, cross_shard_mask, inner_shard_mask)
    
    print("\n正在显示图表...")
    plt.show()
    
    print(f"\n{'='*50}")
    print(f"最终结论: Justitia机制效果评级为 {effectiveness}")
    print(f"跨片交易时延是片内交易的 {ratio_mean:.2f} 倍")
    if ratio_mean > 2.0:
        print("建议检查Justitia机制配置和实现")
    else:
        print("Justitia机制运行良好")
    print(f"{'='*50}")
    
    input("按Enter键关闭窗口...")

if __name__ == "__main__":
    main()
