#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R_EB 补贴机制实验结果分析脚本
分析 expTest_R_EB 目录下的实验数据
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配置
MODE_NAME = "R_EB Subsidy"
EXP_DIR = "../expTest_R_EB/result/supervisor_measureOutput"
OUTPUT_DIR = "./analysis_results_R_EB"

def ensure_output_dir():
    """确保输出目录存在"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"创建输出目录: {OUTPUT_DIR}")

def load_data():
    """加载实验数据"""
    print(f"\n{'='*80}")
    print(f"加载 {MODE_NAME} 实验数据")
    print(f"{'='*80}")
    
    tx_details_path = os.path.join(EXP_DIR, "Tx_Details.csv")
    latency_path = os.path.join(EXP_DIR, "Transaction_Confirm_Latency.csv")
    
    if not os.path.exists(tx_details_path):
        print(f"\n❌ 错误: 未找到数据文件")
        print(f"期望路径: {tx_details_path}")
        print(f"\n请先运行实验生成数据")
        input("\n按Enter键关闭窗口...")
        return None, None
    
    print(f"\n加载交易详情: {tx_details_path}")
    df = pd.read_csv(tx_details_path)
    print(f"✓ 成功加载 {len(df)} 条交易记录")
    
    latency_df = None
    if os.path.exists(latency_path):
        print(f"加载时延数据: {latency_path}")
        latency_df = pd.read_csv(latency_path)
        print(f"✓ 成功加载时延数据")
    
    return df, latency_df

def classify_transactions(df):
    """分类交易为跨片(CTX)和片内(ITX)"""
    # 检查列名
    if 'IsCrossShard' in df.columns:
        cross_shard_mask = df['IsCrossShard'] == 'true'
        inner_shard_mask = df['IsCrossShard'] == 'false'
    elif 'Is_CrossShard_Transaction' in df.columns:
        cross_shard_mask = df['Is_CrossShard_Transaction'] == 1
        inner_shard_mask = df['Is_CrossShard_Transaction'] == 0
    else:
        print("错误：未找到跨片交易标识列")
        return None, None
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
    fee_columns = [col for col in df.columns if 'fee' in col.lower() or col == 'FeeToProposer']
    subsidy_columns = [col for col in df.columns if 'subsidy' in col.lower() or col == 'SubsidyR']
    
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

def analyze_subsidy_distribution(df, cross_shard_mask):
    """分析补贴分布"""
    print(f"\n{'='*80}")
    print(f"{MODE_NAME} - 补贴分布分析")
    print(f"{'='*80}")
    
    subsidy_columns = [col for col in df.columns if 'subsidy' in col.lower() or col == 'SubsidyR']
    
    if subsidy_columns:
        subsidy_col = subsidy_columns[0]
        ctx_subsidies = df[cross_shard_mask][subsidy_col].fillna(0)
        
        wei_to_eth = 1e18
        
        print(f"\n补贴分布统计:")
        print(f"  平均补贴:            {ctx_subsidies.mean()/wei_to_eth:.10f} ETH")
        print(f"  中位数补贴:          {ctx_subsidies.median()/wei_to_eth:.10f} ETH")
        print(f"  最小补贴:            {ctx_subsidies.min()/wei_to_eth:.10f} ETH")
        print(f"  最大补贴:            {ctx_subsidies.max()/wei_to_eth:.10f} ETH")
        print(f"  标准差:              {ctx_subsidies.std()/wei_to_eth:.10f} ETH")
        
        return ctx_subsidies
    else:
        print("\n⚠️  未找到补贴数据列")
        return None

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

def plot_results(cross_shard_latency, inner_shard_latency, profit_data, ctx_subsidies):
    """绘制综合分析图表"""
    print(f"\n生成综合分析图表...")
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)
    
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
    bp = ax2.boxplot(data_to_plot, labels=['ITX', 'CTX'], patch_artist=True)
    for patch, color in zip(bp['boxes'], ['blue', 'red']):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title(f'{MODE_NAME} - Latency Boxplot')
    ax2.grid(True, alpha=0.3)
    
    # 3. 时延比率
    ax3 = fig.add_subplot(gs[0, 2])
    ratio = cross_shard_latency.mean() / inner_shard_latency.mean()
    ax3.bar(['Latency Ratio'], [ratio], color='orange', alpha=0.7)
    ax3.axhline(y=1.5, color='g', linestyle='--', label='Target (1.5x)', alpha=0.5)
    ax3.set_ylabel('Ratio (CTX/ITX)')
    ax3.set_title('CTX to ITX Latency Ratio')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.text(0, ratio, f'{ratio:.2f}x', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    if profit_data:
        wei_to_eth = 1e18
        
        # 4. CTX vs ITX 利润对比
        ax4 = fig.add_subplot(gs[1, 0])
        profits = [
            profit_data['ctx_total_profit'].mean() / wei_to_eth,
            profit_data['itx_fees'].mean() / wei_to_eth
        ]
        colors_profit = ['red', 'blue']
        bars = ax4.bar(['CTX', 'ITX'], profits, color=colors_profit, alpha=0.7)
        ax4.set_ylabel('Mean Profit (ETH)')
        ax4.set_title('CTX vs ITX Miner Profit')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        for bar, val in zip(bars, profits):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2e}', ha='center', va='bottom', fontsize=9)
        
        # 5. 费用 vs 补贴构成
        ax5 = fig.add_subplot(gs[1, 1])
        components = [
            profit_data['ctx_fees'].mean() / wei_to_eth,
            profit_data['ctx_subsidies'].mean() / wei_to_eth
        ]
        bars = ax5.bar(['Fee', 'Subsidy'], components, color=['#3498db', '#e74c3c'], alpha=0.7)
        ax5.set_ylabel('Amount (ETH)')
        ax5.set_title('CTX Profit Components')
        ax5.grid(True, alpha=0.3, axis='y')
        ax5.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        for bar, val in zip(bars, components):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2e}', ha='center', va='bottom', fontsize=9)
        
        # 6. 利润比率
        ax6 = fig.add_subplot(gs[1, 2])
        profit_ratio = profit_data['profit_ratio']
        ax6.bar(['Profit Ratio'], [profit_ratio], color='green', alpha=0.7)
        ax6.axhline(y=1.0, color='r', linestyle='--', label='Equal (1.0x)', alpha=0.5)
        ax6.set_ylabel('Ratio (CTX/ITX)')
        ax6.set_title('CTX to ITX Profit Ratio')
        ax6.legend()
        ax6.grid(True, alpha=0.3, axis='y')
        ax6.text(0, profit_ratio, f'{profit_ratio:.2f}x', ha='center', va='bottom', 
                fontsize=12, fontweight='bold')
    
    if ctx_subsidies is not None:
        wei_to_eth = 1e18
        
        # 7. 补贴分布直方图
        ax7 = fig.add_subplot(gs[2, 0])
        ax7.hist(ctx_subsidies / wei_to_eth, bins=50, color='purple', alpha=0.7)
        ax7.set_xlabel('Subsidy (ETH)')
        ax7.set_ylabel('Frequency')
        ax7.set_title('Subsidy Distribution')
        ax7.grid(True, alpha=0.3)
        ax7.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
        
        # 8. 补贴箱线图
        ax8 = fig.add_subplot(gs[2, 1])
        bp = ax8.boxplot([ctx_subsidies / wei_to_eth], labels=['CTX Subsidy'], patch_artist=True)
        bp['boxes'][0].set_facecolor('purple')
        bp['boxes'][0].set_alpha(0.6)
        ax8.set_ylabel('Subsidy (ETH)')
        ax8.set_title('Subsidy Statistics')
        ax8.grid(True, alpha=0.3)
        ax8.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        
        # 9. 补贴统计摘要
        ax9 = fig.add_subplot(gs[2, 2])
        ax9.axis('off')
        stats_text = f"""
Subsidy Statistics:
━━━━━━━━━━━━━━━━━━━━━━
Total:    {ctx_subsidies.sum()/wei_to_eth:.6f} ETH
Mean:     {ctx_subsidies.mean()/wei_to_eth:.10f} ETH
Median:   {ctx_subsidies.median()/wei_to_eth:.10f} ETH
Std Dev:  {ctx_subsidies.std()/wei_to_eth:.10f} ETH
Min:      {ctx_subsidies.min()/wei_to_eth:.10f} ETH
Max:      {ctx_subsidies.max()/wei_to_eth:.10f} ETH
        """
        ax9.text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
                verticalalignment='center')
    
    plt.suptitle(f'{MODE_NAME} - Comprehensive Analysis', fontsize=16, fontweight='bold', y=0.995)
    
    output_path = os.path.join(OUTPUT_DIR, 'R_EB_comprehensive_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ 保存图表: {output_path}")
    plt.close()

def generate_summary_report(ctx_percentage, ctx_count, itx_count, cross_shard_latency, inner_shard_latency, profit_data):
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
    
    if profit_data:
        print(f"  • 利润比率:          {profit_data['profit_ratio']:.2f}x")
    
    print(f"\n🎯 R_EB 补贴机制特点:")
    print(f"  • 基于 E_B (目标分片负载) 的补贴计算")
    print(f"  • 考虑分片间的负载差异")
    print(f"  • 激励矿工处理跨片交易")
    
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
    print(f"# R_EB 补贴机制 - 实验结果分析")
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
    
    # 分析补贴分布
    ctx_subsidies = analyze_subsidy_distribution(df, cross_shard_mask)
    
    # 分析时延
    cross_shard_latency, inner_shard_latency = analyze_latency(df, cross_shard_mask, inner_shard_mask)
    
    # 绘制图表
    if len(cross_shard_latency) > 0 and len(inner_shard_latency) > 0:
        plot_results(cross_shard_latency, inner_shard_latency, profit_data, ctx_subsidies)
    
    # 生成总结报告
    generate_summary_report(ctx_percentage, ctx_count, itx_count, cross_shard_latency, inner_shard_latency, profit_data)
    
    print(f"\n{'='*80}")
    print(f"分析完成！结果保存在: {OUTPUT_DIR}")
    print(f"{'='*80}\n")
    
    input("按Enter键关闭窗口...")

if __name__ == "__main__":
    main()
