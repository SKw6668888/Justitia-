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

def analyze_ctx_percentage(df, cross_shard_mask, inner_shard_mask):
    """分析被成功打包进区块的交易中CTX占比"""
    print("\n" + "=" * 80)
    print("CTX交易占比分析")
    print("=" * 80)
    
    total_txs = len(df)
    ctx_count = cross_shard_mask.sum()
    itx_count = inner_shard_mask.sum()
    
    ctx_percentage = (ctx_count / total_txs * 100) if total_txs > 0 else 0
    itx_percentage = (itx_count / total_txs * 100) if total_txs > 0 else 0
    
    print(f"\n成功打包进区块的交易统计:")
    print(f"{'类型':<20} {'数量':<15} {'占比':<15}")
    print("-" * 50)
    print(f"{'总交易数':<20} {total_txs:<15,} {100.0:<15.2f}%")
    print(f"{'跨片交易 (CTX)':<20} {ctx_count:<15,} {ctx_percentage:<15.2f}%")
    print(f"{'片内交易 (ITX)':<20} {itx_count:<15,} {itx_percentage:<15.2f}%")
    
    return ctx_percentage, ctx_count, itx_count, total_txs

def analyze_miner_profit(df, cross_shard_mask, inner_shard_mask):
    """分析矿工打包交易的利润"""
    print("\n" + "=" * 80)
    print("矿工利润分析")
    print("=" * 80)
    
    # 查找费用相关列
    fee_columns = [col for col in df.columns if 'fee' in col.lower() or 'proposer' in col.lower()]
    subsidy_columns = [col for col in df.columns if 'subsidy' in col.lower()]
    
    if not fee_columns:
        print("\n⚠️  警告: 数据中未找到费用相关列")
        print("可用列:", df.columns.tolist())
        print("\n建议:")
        print("1. 确保实验配置中启用了费用记录")
        print("2. 检查 measure_TxDetail.go 是否记录了费用信息")
        print("3. 或使用 CTX_Fee_Latency.csv 文件进行费用分析")
        return None
    
    print(f"\n找到费用相关列: {fee_columns}")
    if subsidy_columns:
        print(f"找到补贴相关列: {subsidy_columns}")
    
    # 假设费用列名为 'FeeToProposer' 或类似
    # 这里需要根据实际数据结构调整
    fee_col = None
    for col in fee_columns:
        if 'proposer' in col.lower() or 'miner' in col.lower():
            fee_col = col
            break
    
    if fee_col is None and len(fee_columns) > 0:
        fee_col = fee_columns[0]
    
    # 查找补贴列
    subsidy_col = None
    if subsidy_columns:
        subsidy_col = subsidy_columns[0]
    
    if fee_col:
        print(f"\n使用费用列: {fee_col}")
        if subsidy_col:
            print(f"使用补贴列: {subsidy_col}")
        
        # 转换为数值类型
        df[fee_col] = pd.to_numeric(df[fee_col], errors='coerce')
        if subsidy_col:
            df[subsidy_col] = pd.to_numeric(df[subsidy_col], errors='coerce')
        
        # 计算总收益 = 费用 + 补贴（仅对CTX）
        df['TotalProfit'] = df[fee_col].fillna(0)
        if subsidy_col:
            # 只有CTX有补贴
            df.loc[cross_shard_mask, 'TotalProfit'] = df.loc[cross_shard_mask, fee_col].fillna(0) + df.loc[cross_shard_mask, subsidy_col].fillna(0)
        
        # 计算统计信息（使用总收益）
        all_fees = df['TotalProfit'].dropna()
        ctx_fees = df[cross_shard_mask]['TotalProfit'].dropna()
        itx_fees = df[inner_shard_mask]['TotalProfit'].dropna()
        
        print(f"\n矿工打包交易利润统计 (单位: wei):")
        print(f"{'交易类型':<20} {'平均利润':<20} {'中位数利润':<20} {'最小利润':<20} {'最大利润':<20}")
        print("-" * 100)
        
        if len(all_fees) > 0:
            print(f"{'所有交易':<20} {all_fees.mean():<20.2e} {all_fees.median():<20.2e} {all_fees.min():<20.2e} {all_fees.max():<20.2e}")
        if len(ctx_fees) > 0:
            print(f"{'跨片交易 (CTX)':<20} {ctx_fees.mean():<20.2e} {ctx_fees.median():<20.2e} {ctx_fees.min():<20.2e} {ctx_fees.max():<20.2e}")
        if len(itx_fees) > 0:
            print(f"{'片内交易 (ITX)':<20} {itx_fees.mean():<20.2e} {itx_fees.median():<20.2e} {itx_fees.min():<20.2e} {itx_fees.max():<20.2e}")
        
        # 转换为以太币单位 (1 ETH = 10^18 wei)
        print(f"\n矿工打包交易利润统计 (单位: ETH):")
        print(f"{'交易类型':<20} {'平均利润':<20} {'中位数利润':<20} {'最小利润':<20} {'最大利润':<20}")
        print("-" * 100)
        
        wei_to_eth = 1e18
        if len(all_fees) > 0:
            print(f"{'所有交易':<20} {all_fees.mean()/wei_to_eth:<20.10f} {all_fees.median()/wei_to_eth:<20.10f} {all_fees.min()/wei_to_eth:<20.10f} {all_fees.max()/wei_to_eth:<20.10f}")
        if len(ctx_fees) > 0:
            print(f"{'跨片交易 (CTX)':<20} {ctx_fees.mean()/wei_to_eth:<20.10f} {ctx_fees.median()/wei_to_eth:<20.10f} {ctx_fees.min()/wei_to_eth:<20.10f} {ctx_fees.max()/wei_to_eth:<20.10f}")
        if len(itx_fees) > 0:
            print(f"{'片内交易 (ITX)':<20} {itx_fees.mean()/wei_to_eth:<20.10f} {itx_fees.median()/wei_to_eth:<20.10f} {itx_fees.min()/wei_to_eth:<20.10f} {itx_fees.max()/wei_to_eth:<20.10f}")
        
        # 比较CTX和ITX的利润差异
        if len(ctx_fees) > 0 and len(itx_fees) > 0:
            print(f"\n利润差异分析:")
            profit_ratio = ctx_fees.mean() / itx_fees.mean() if itx_fees.mean() > 0 else 0
            profit_diff = ctx_fees.mean() - itx_fees.mean()
            print(f"CTX平均利润是ITX的 {profit_ratio:.2f} 倍")
            print(f"CTX平均利润比ITX {'高' if profit_diff > 0 else '低'} {abs(profit_diff):.2e} wei ({abs(profit_diff)/wei_to_eth:.10f} ETH)")
            
            # 统计显著性检验
            if len(ctx_fees) > 1 and len(itx_fees) > 1:
                statistic, p_value = stats.mannwhitneyu(ctx_fees, itx_fees, alternative='two-sided')
                print(f"\nMann-Whitney U检验 p值: {p_value:.6f}")
                if p_value < 0.05:
                    print("结论: CTX和ITX的利润分布存在显著差异 (p < 0.05)")
                else:
                    print("结论: CTX和ITX的利润分布无显著差异 (p >= 0.05)")
        
        return {
            'all_fees': all_fees,
            'ctx_fees': ctx_fees,
            'itx_fees': itx_fees,
            'fee_col': fee_col
        }
    
    return None

def analyze_justitia_effectiveness(df, cross_shard_mask, inner_shard_mask):
    """分析Justitia机制的有效性"""
    print("\n" + "=" * 80)
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
    
    # 5. 交易分布分析 (保留原有功能)
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

def create_ctx_percentage_plot(ctx_percentage, ctx_count, itx_count, total_txs):
    """创建CTX占比饼图"""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    
    labels = [f'跨片交易 (CTX)\n{ctx_count:,} 笔', f'片内交易 (ITX)\n{itx_count:,} 笔']
    sizes = [ctx_count, itx_count]
    colors = ['#ff9999', '#66b3ff']
    explode = (0.05, 0)  # 突出显示CTX
    
    ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
           shadow=True, startangle=90, textprops={'fontsize': 12, 'weight': 'bold'})
    ax.set_title(f'成功打包交易类型分布\n(总计 {total_txs:,} 笔交易)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    return fig

def create_miner_profit_plots(profit_data):
    """创建矿工利润分析图表"""
    if profit_data is None:
        return None
    
    all_fees = profit_data['all_fees']
    ctx_fees = profit_data['ctx_fees']
    itx_fees = profit_data['itx_fees']
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('矿工利润分析', fontsize=16, fontweight='bold')
    
    # 1. 利润分布箱线图
    ax1 = axes[0, 0]
    data_for_box = []
    labels_for_box = []
    
    if len(itx_fees) > 0:
        data_for_box.append(itx_fees)
        labels_for_box.append(f'ITX\n(n={len(itx_fees)})')
    if len(ctx_fees) > 0:
        data_for_box.append(ctx_fees)
        labels_for_box.append(f'CTX\n(n={len(ctx_fees)})')
    
    if len(data_for_box) > 0:
        box_plot = ax1.boxplot(data_for_box, labels=labels_for_box, patch_artist=True)
        colors = ['lightblue', 'lightcoral']
        for patch, color in zip(box_plot['boxes'], colors[:len(data_for_box)]):
            patch.set_facecolor(color)
        ax1.set_title('交易利润分布对比')
        ax1.set_ylabel('利润 (wei)')
        ax1.grid(True, alpha=0.3)
    
    # 2. 利润分布直方图
    ax2 = axes[0, 1]
    if len(itx_fees) > 0:
        ax2.hist(itx_fees, bins=50, alpha=0.6, label=f'ITX (n={len(itx_fees)})', color='blue')
    if len(ctx_fees) > 0:
        ax2.hist(ctx_fees, bins=50, alpha=0.6, label=f'CTX (n={len(ctx_fees)})', color='red')
    ax2.set_title('交易利润分布直方图')
    ax2.set_xlabel('利润 (wei)')
    ax2.set_ylabel('频数')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 平均利润对比柱状图
    ax3 = axes[1, 0]
    means = []
    labels_bar = []
    colors_bar = []
    
    if len(itx_fees) > 0:
        means.append(itx_fees.mean())
        labels_bar.append('ITX')
        colors_bar.append('lightblue')
    if len(ctx_fees) > 0:
        means.append(ctx_fees.mean())
        labels_bar.append('CTX')
        colors_bar.append('lightcoral')
    
    if len(means) > 0:
        bars = ax3.bar(labels_bar, means, color=colors_bar)
        ax3.set_title('平均交易利润对比')
        ax3.set_ylabel('平均利润 (wei)')
        ax3.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{mean:.2e}',
                    ha='center', va='bottom', fontsize=10)
    
    # 4. 累积分布函数 (CDF)
    ax4 = axes[1, 1]
    
    def plot_cdf(data, label, color):
        sorted_data = np.sort(data)
        y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        ax4.plot(sorted_data, y, label=label, color=color, linewidth=2)
    
    if len(itx_fees) > 0:
        plot_cdf(itx_fees, f'ITX (n={len(itx_fees)})', 'blue')
    if len(ctx_fees) > 0:
        plot_cdf(ctx_fees, f'CTX (n={len(ctx_fees)})', 'red')
    
    ax4.set_title('交易利润累积分布函数 (CDF)')
    ax4.set_xlabel('利润 (wei)')
    ax4.set_ylabel('累积概率')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def create_justitia_analysis_plots(df, cross_shard_mask, inner_shard_mask):
    """创建Justitia机制分析图表"""
    
    latency_column = 'Confirmed latency of this tx (ms)'
    cross_shard_latency = df[cross_shard_mask][latency_column]
    inner_shard_latency = df[inner_shard_mask][latency_column]
    
    # 创建子图
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Justitia机制时延分析', fontsize=16, fontweight='bold')
    
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
    
    # 新增: CTX占比分析
    print("\n正在分析CTX占比...")
    ctx_percentage, ctx_count, itx_count, total_txs = analyze_ctx_percentage(df, cross_shard_mask, inner_shard_mask)
    
    # 新增: 矿工利润分析
    print("\n正在分析矿工利润...")
    profit_data = analyze_miner_profit(df, cross_shard_mask, inner_shard_mask)
    
    print("\n正在分析Justitia机制有效性...")
    ratio_mean, effectiveness = analyze_justitia_effectiveness(df, cross_shard_mask, inner_shard_mask)
    
    print("\n正在生成分析图表...")
    fig_latency = create_justitia_analysis_plots(df, cross_shard_mask, inner_shard_mask)
    fig_ctx_percentage = create_ctx_percentage_plot(ctx_percentage, ctx_count, itx_count, total_txs)
    
    if profit_data is not None:
        fig_profit = create_miner_profit_plots(profit_data)
    else:
        fig_profit = None
    
    print("\n正在显示图表...")
    plt.show()
    
    print(f"\n{'='*80}")
    print("分析总结")
    print(f"{'='*80}")
    print(f"\n1. CTX占比: {ctx_percentage:.2f}% ({ctx_count:,}/{total_txs:,} 笔交易)")
    print(f"2. Justitia机制效果评级: {effectiveness}")
    print(f"3. 跨片交易时延是片内交易的 {ratio_mean:.2f} 倍")
    
    if profit_data is not None:
        if len(profit_data['ctx_fees']) > 0 and len(profit_data['itx_fees']) > 0:
            profit_ratio = profit_data['ctx_fees'].mean() / profit_data['itx_fees'].mean()
            print(f"4. CTX平均利润是ITX的 {profit_ratio:.2f} 倍")
            print(f"   - CTX平均利润: {profit_data['ctx_fees'].mean():.2e} wei")
            print(f"   - ITX平均利润: {profit_data['itx_fees'].mean():.2e} wei")
    
    if ratio_mean > 2.0:
        print("\n⚠️  建议检查Justitia机制配置和实现")
    else:
        print("\n✅ Justitia机制运行良好")
    print(f"{'='*80}")
    
    input("\n按Enter键关闭窗口...")

if __name__ == "__main__":
    main()
