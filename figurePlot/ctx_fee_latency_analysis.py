import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
import argparse
import os
warnings.filterwarnings('ignore')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def load_ctx_fee_latency_data(data_path):
    """加载 CTX 费用和时延数据"""
    try:
        df = pd.read_csv(data_path)
        print(f"成功加载数据: {len(df)} 条 CTX 记录")
        return df
    except FileNotFoundError:
        print(f"错误: 找不到数据文件 {data_path}")
        print("请确保已经运行实验并生成 CTX_Fee_Latency.csv 文件")
        return None
    except Exception as e:
        print(f"加载数据时出错: {e}")
        return None

def preprocess_data(df):
    """预处理数据：清洗和转换"""
    # 转换费用为数值类型
    df['FeeToProposer (wei)'] = pd.to_numeric(df['FeeToProposer (wei)'], errors='coerce')
    
    # 转换时延为数值类型
    df['QueueLatency (ms)'] = pd.to_numeric(df['QueueLatency (ms)'], errors='coerce')
    
    # 移除无效数据
    df = df.dropna(subset=['FeeToProposer (wei)', 'QueueLatency (ms)'])
    
    # 移除异常值（时延为负或过大）
    df = df[(df['QueueLatency (ms)'] > 0) & (df['QueueLatency (ms)'] < 500000)]
    
    # 移除费用为负或零的交易（可能的数据错误）
    df = df[df['FeeToProposer (wei)'] > 0]
    
    print(f"预处理后数据: {len(df)} 条有效记录")
    print(f"费用范围: {df['FeeToProposer (wei)'].min():.2e} - {df['FeeToProposer (wei)'].max():.2e} wei")
    print(f"时延范围: {df['QueueLatency (ms)'].min():.2f} - {df['QueueLatency (ms)'].max():.2f} ms")
    
    return df

def calculate_fee_quantiles(df, n_quantiles=20):
    """计算费用分位数并分组"""
    # 检查费用是否全部相同
    unique_fees = df['FeeToProposer (wei)'].unique()
    if len(unique_fees) == 1:
        print(f"警告: 所有交易费用值相同 ({unique_fees[0]:.2e} wei)，无法计算有效的分位数")
        # 所有交易都分配到同一个分位数
        df['FeeQuantile'] = pd.Series([1] * len(df), index=df.index)
        
        # 创建简化的分位数统计
        quantile_stats = pd.DataFrame({
            'FeeQuantile': [1],
            'FeeMean': [df['FeeToProposer (wei)'].mean()],
            'FeeMedian': [df['FeeToProposer (wei)'].median()],
            'FeeMin': [df['FeeToProposer (wei)'].min()],
            'FeeMax': [df['FeeToProposer (wei)'].max()],
            'FeeCount': [len(df)],
            'LatencyMean': [df['QueueLatency (ms)'].mean()],
            'LatencyMedian': [df['QueueLatency (ms)'].median()],
            'LatencyStd': [df['QueueLatency (ms)'].std()],
            'LatencyCount': [len(df)],
            'FeeQuantileCenter': [1]
        })
        return quantile_stats, df
    
    # 正常情况：计算费用分位数边界
    quantile_edges = np.linspace(0, 100, n_quantiles + 1)
    fee_percentiles = np.percentile(df['FeeToProposer (wei)'], quantile_edges)
    
    # 处理可能的重复边界
    # 添加小的扰动，或者使用duplicates参数
    df['FeeQuantile'] = pd.cut(df['FeeToProposer (wei)'], 
                                bins=fee_percentiles,
                                labels=range(1, n_quantiles + 1),
                                include_lowest=True,
                                duplicates='drop')  # 处理重复边界
    
    # 计算每个分位数的统计信息
    quantile_stats = df.groupby('FeeQuantile').agg({
        'FeeToProposer (wei)': ['mean', 'median', 'min', 'max', 'count'],
        'QueueLatency (ms)': ['mean', 'median', 'std', 'count']
    }).reset_index()
    
    #  flatten column names
    quantile_stats.columns = ['FeeQuantile', 'FeeMean', 'FeeMedian', 'FeeMin', 'FeeMax', 'FeeCount',
                               'LatencyMean', 'LatencyMedian', 'LatencyStd', 'LatencyCount']
    
    # 计算分位数的中心值（用于绘图）
    quantile_stats['FeeQuantileCenter'] = quantile_stats['FeeQuantile'].astype(int)
    
    return quantile_stats, df

def check_monotonicity(quantile_stats, df_with_quantiles):
    """检查时延是否单调不增（高费用应该对应低或相等的时延）"""
    print("\n" + "="*80)
    print("单调性检查")
    print("="*80)
    
    # 按费用分位数排序
    quantile_stats_sorted = quantile_stats.sort_values('FeeQuantileCenter')
    
    # 检查平均时延是否单调不增
    mean_latencies = quantile_stats_sorted['LatencyMean'].values
    violations_mean = []
    
    for i in range(1, len(mean_latencies)):
        if mean_latencies[i] > mean_latencies[i-1]:
            violations_mean.append({
                'quantile': quantile_stats_sorted.iloc[i]['FeeQuantileCenter'],
                'prev_latency': mean_latencies[i-1],
                'current_latency': mean_latencies[i],
                'increase': mean_latencies[i] - mean_latencies[i-1],
                'increase_pct': (mean_latencies[i] - mean_latencies[i-1]) / mean_latencies[i-1] * 100
            })
    
    # 检查中位数时延是否单调不增
    median_latencies = quantile_stats_sorted['LatencyMedian'].values
    violations_median = []
    
    for i in range(1, len(median_latencies)):
        if median_latencies[i] > median_latencies[i-1]:
            violations_median.append({
                'quantile': quantile_stats_sorted.iloc[i]['FeeQuantileCenter'],
                'prev_latency': median_latencies[i-1],
                'current_latency': median_latencies[i],
                'increase': median_latencies[i] - median_latencies[i-1],
                'increase_pct': (median_latencies[i] - median_latencies[i-1]) / median_latencies[i-1] * 100
            })
    
    # 输出结果
    print(f"\n平均时延单调性检查:")
    if len(violations_mean) == 0:
        print("✅ 通过: 平均时延单调不增（高费用对应低或相等的时延）")
    else:
        print(f"❌ 违反: 发现 {len(violations_mean)} 处违反单调不增性质")
        print("\n违反详情（平均时延）:")
        for v in violations_mean[:10]:  # 只显示前10个违反
            print(f"  分位数 {int(v['quantile'])-1} → {int(v['quantile'])}: "
                  f"时延从 {v['prev_latency']:.2f} ms 增加到 {v['current_latency']:.2f} ms "
                  f"(增加 {v['increase']:.2f} ms, {v['increase_pct']:.2f}%)")
        if len(violations_mean) > 10:
            print(f"  ... 还有 {len(violations_mean) - 10} 处违反未显示")
    
    print(f"\n中位数时延单调性检查:")
    if len(violations_median) == 0:
        print("✅ 通过: 中位数时延单调不增（高费用对应低或相等的时延）")
    else:
        print(f"❌ 违反: 发现 {len(violations_median)} 处违反单调不增性质")
        print("\n违反详情（中位数时延）:")
        for v in violations_median[:10]:  # 只显示前10个违反
            print(f"  分位数 {int(v['quantile'])-1} → {int(v['quantile'])}: "
                  f"时延从 {v['prev_latency']:.2f} ms 增加到 {v['current_latency']:.2f} ms "
                  f"(增加 {v['increase']:.2f} ms, {v['increase_pct']:.2f}%)")
        if len(violations_median) > 10:
            print(f"  ... 还有 {len(violations_median) - 10} 处违反未显示")
    
    # 统计显著性检验：检查高费用组和低费用组的时延差异
    print(f"\n统计显著性检验:")
    # 获取最高和最低费用分位数的数据
    high_quantiles = quantile_stats_sorted.tail(max(1, len(quantile_stats_sorted) // 4))
    low_quantiles = quantile_stats_sorted.head(max(1, len(quantile_stats_sorted) // 4))
    
    high_fee_mean = high_quantiles['LatencyMean'].mean()
    low_fee_mean = low_quantiles['LatencyMean'].mean()
    
    # 从原始数据中获取对应的时延数据进行统计检验
    high_fee_quantile_ids = high_quantiles['FeeQuantileCenter'].astype(int).tolist()
    low_fee_quantile_ids = low_quantiles['FeeQuantileCenter'].astype(int).tolist()
    
    high_fee_latencies = df_with_quantiles[df_with_quantiles['FeeQuantile'].astype(int).isin(high_fee_quantile_ids)]['QueueLatency (ms)']
    low_fee_latencies = df_with_quantiles[df_with_quantiles['FeeQuantile'].astype(int).isin(low_fee_quantile_ids)]['QueueLatency (ms)']
    
    if len(high_fee_latencies) > 0 and len(low_fee_latencies) > 0:
        # Mann-Whitney U 检验（非参数检验）
        statistic, p_value = stats.mannwhitneyu(high_fee_latencies, low_fee_latencies, alternative='less')
        print(f"  高费用组平均时延: {high_fee_mean:.2f} ms (n={len(high_fee_latencies)})")
        print(f"  低费用组平均时延: {low_fee_mean:.2f} ms (n={len(low_fee_latencies)})")
        print(f"  时延差异: {low_fee_mean - high_fee_mean:.2f} ms "
              f"({(low_fee_mean - high_fee_mean) / low_fee_mean * 100:.2f}%)")
        print(f"  Mann-Whitney U 检验 p-value: {p_value:.4e}")
        
        if high_fee_mean < low_fee_mean and p_value < 0.05:
            print("  ✅ 高费用组时延显著更低（符合预期，p < 0.05）")
        elif high_fee_mean < low_fee_mean:
            print("  ⚠️  高费用组时延更低，但不显著（p >= 0.05）")
        else:
            print("  ❌ 高费用组时延更高（违反预期）")
    
    return violations_mean, violations_median

def plot_fee_latency_curve(quantile_stats, output_path=None):
    """绘制费用分位数 → 平均/中位排队时延曲线"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('CTX 费用分位数 → 排队时延分析', fontsize=16, fontweight='bold')
    
    # 1. 平均时延曲线
    ax1 = axes[0, 0]
    ax1.plot(quantile_stats['FeeQuantileCenter'], quantile_stats['LatencyMean'], 
             'o-', color='blue', linewidth=2, markersize=6, label='平均时延')
    ax1.fill_between(quantile_stats['FeeQuantileCenter'], 
                      quantile_stats['LatencyMean'] - quantile_stats['LatencyStd'],
                      quantile_stats['LatencyMean'] + quantile_stats['LatencyStd'],
                      alpha=0.3, color='blue', label='±1 标准差')
    ax1.set_xlabel('费用分位数')
    ax1.set_ylabel('平均排队时延 (ms)')
    ax1.set_title('费用分位数 → 平均排队时延')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. 中位数时延曲线
    ax2 = axes[0, 1]
    ax2.plot(quantile_stats['FeeQuantileCenter'], quantile_stats['LatencyMedian'], 
             's-', color='red', linewidth=2, markersize=6, label='中位数时延')
    ax2.set_xlabel('费用分位数')
    ax2.set_ylabel('中位数排队时延 (ms)')
    ax2.set_title('费用分位数 → 中位数排队时延')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # 3. 平均和中位数时延对比
    ax3 = axes[1, 0]
    ax3.plot(quantile_stats['FeeQuantileCenter'], quantile_stats['LatencyMean'], 
             'o-', color='blue', linewidth=2, markersize=6, label='平均时延')
    ax3.plot(quantile_stats['FeeQuantileCenter'], quantile_stats['LatencyMedian'], 
             's-', color='red', linewidth=2, markersize=6, label='中位数时延')
    ax3.set_xlabel('费用分位数')
    ax3.set_ylabel('排队时延 (ms)')
    ax3.set_title('平均 vs 中位数时延对比')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # 4. 费用分布（对数尺度）
    ax4 = axes[1, 1]
    ax4.plot(quantile_stats['FeeQuantileCenter'], quantile_stats['FeeMean'], 
             'o-', color='green', linewidth=2, markersize=6, label='平均费用')
    ax4.set_xlabel('费用分位数')
    ax4.set_ylabel('平均费用 (wei)')
    ax4.set_title('费用分位数 → 平均费用')
    ax4.set_yscale('log')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n图表已保存到: {output_path}")
    
    return fig

def analyze_fee_latency_correlation(df):
    """分析费用和时延的相关性"""
    print("\n" + "="*80)
    print("费用-时延相关性分析")
    print("="*80)
    
    # 计算 Pearson 相关系数
    pearson_corr, pearson_p = stats.pearsonr(df['FeeToProposer (wei)'], df['QueueLatency (ms)'])
    print(f"\nPearson 相关系数: {pearson_corr:.4f} (p-value: {pearson_p:.4e})")
    
    if pearson_corr < -0.1:
        print("  ✅ 强负相关：高费用对应低时延（符合预期）")
    elif pearson_corr < 0:
        print("  ⚠️  弱负相关：费用和时延呈负相关，但相关性较弱")
    elif pearson_corr < 0.1:
        print("  ⚠️  几乎无相关：费用和时延几乎没有相关性")
    else:
        print("  ❌ 正相关：高费用对应高时延（违反预期）")
    
    # 计算 Spearman 秩相关系数（对单调关系更敏感）
    spearman_corr, spearman_p = stats.spearmanr(df['FeeToProposer (wei)'], df['QueueLatency (ms)'])
    print(f"\nSpearman 秩相关系数: {spearman_corr:.4f} (p-value: {spearman_p:.4e})")
    
    if spearman_corr < -0.1:
        print("  ✅ 强负相关：高费用对应低时延（符合预期）")
    elif spearman_corr < 0:
        print("  ⚠️  弱负相关：费用和时延呈负相关，但相关性较弱")
    else:
        print("  ❌ 非负相关：费用和时延不是负相关关系（可能违反预期）")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='CTX费用和时延分析工具')
    parser.add_argument('--data', type=str, default='../expTest/result/supervisor_measureOutput/CTX_Fee_Latency.csv',
                        help='CTX费用时延数据文件路径')
    args = parser.parse_args()
    
    # 数据文件路径
    data_path = args.data
    
    print("="*80)
    print("CTX 费用分位数 → 排队时延分析")
    print("="*80)
    print(f"使用数据文件: {os.path.abspath(data_path)}")
    
    # 加载数据
    df = load_ctx_fee_latency_data(data_path)
    if df is None:
        return
    
    # 预处理数据
    df = preprocess_data(df)
    if len(df) == 0:
        print("错误: 没有有效数据可供分析")
        return
    
    # 计算费用分位数
    print("\n正在计算费用分位数...")
    quantile_stats, df_with_quantiles = calculate_fee_quantiles(df, n_quantiles=20)
    
    # 检查单调性
    violations_mean, violations_median = check_monotonicity(quantile_stats, df_with_quantiles)
    
    # 分析相关性
    analyze_fee_latency_correlation(df)
    
    # 获取数据文件的目录
    data_dir = os.path.dirname(os.path.abspath(data_path))
    
    # 绘制曲线
    print("\n正在生成图表...")
    output_path = os.path.join(data_dir, 'CTX_Fee_Latency_Analysis.png')
    fig = plot_fee_latency_curve(quantile_stats, output_path)
    
    # 保存统计结果
    stats_output_path = os.path.join(data_dir, 'CTX_Fee_Latency_QuantileStats.csv')
    quantile_stats.to_csv(stats_output_path, index=False)
    print(f"\n分位数统计结果已保存到: {os.path.abspath(stats_output_path)}")
    
    # 显示图表
    plt.show()
    
    # 总结
    print("\n" + "="*80)
    print("分析总结")
    print("="*80)
    if len(violations_mean) == 0 and len(violations_median) == 0:
        print("✅ 系统表现良好：未发现高费反而更慢的系统性违背")
    else:
        print(f"❌ 发现系统性违背：")
        print(f"  - 平均时延违反次数: {len(violations_mean)}")
        print(f"  - 中位数时延违反次数: {len(violations_median)}")
        print("  建议检查：")
        print("  1. Justitia 机制是否正确实现")
        print("  2. 交易调度器是否正确使用费用进行排序")
        print("  3. 是否存在其他因素影响交易优先级")
    
    input("\n按 Enter 键关闭...")

if __name__ == "__main__":
    main()

