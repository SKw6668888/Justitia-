#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版分片公平性可视化 - 突出显示资源倾斜
Enhanced Shard Fairness Visualization - Emphasizing Resource Tilt
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 11
sns.set_palette("Set2")

def analyze_and_visualize(exp_dir, exp_name):
    """分析并生成增强版可视化"""
    
    # 1. 加载数据
    tx_path = Path(exp_dir) / 'result' / 'supervisor_measureOutput' / 'Tx_Details.csv'
    df = pd.read_csv(tx_path)
    ctx = df[(df['IsCrossShard'] == True) & 
             (df['Tx finally commit timestamp'].notna())].copy()
    
    # 2. 按目标分片聚合
    subsidy_by_dest = ctx.groupby('ToShard').agg({
        'SubsidyR (wei)': ['sum', 'count', 'mean']
    }).reset_index()
    subsidy_by_dest.columns = ['ShardID', 'TotalSubsidy_wei', 'CTX_Count', 'AvgSubsidy_wei']
    subsidy_by_dest['TotalSubsidy_ETH'] = subsidy_by_dest['TotalSubsidy_wei'] / 1e18
    subsidy_by_dest['AvgSubsidy_Gwei'] = subsidy_by_dest['AvgSubsidy_wei'] / 1e9
    
    # 3. 加载队列统计
    shard_stats = []
    for shard_id in range(4):
        shard_path = Path(exp_dir) / 'result' / 'pbft_shardNum=4' / f'Shard{shard_id}4.csv'
        if not shard_path.exists():
            continue
        shard_df = pd.read_csv(shard_path)
        avg_queue = shard_df['TxPool Size'].mean() if 'TxPool Size' in shard_df.columns else 0
        shard_stats.append({'ShardID': shard_id, 'AvgQueueLength': avg_queue})
    
    queue_df = pd.DataFrame(shard_stats)
    result = queue_df.merge(subsidy_by_dest, on='ShardID', how='left')
    
    # 4. 计算归一化指标（以最弱分片为基准100%）
    min_subsidy = result['TotalSubsidy_ETH'].min()
    min_queue = result['AvgQueueLength'].min()
    
    result['Subsidy_Normalized'] = (result['TotalSubsidy_ETH'] / min_subsidy) * 100
    result['Queue_Normalized'] = (result['AvgQueueLength'] / min_queue) * 100
    result['Subsidy_Increase_%'] = result['Subsidy_Normalized'] - 100
    
    # 5. 生成增强版可视化
    fig = plt.figure(figsize=(18, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # ===== 图1: 归一化补贴对比（大图，占2列）=====
    ax1 = fig.add_subplot(gs[0, :2])
    
    colors = ['#3498db' if x < 10 else '#e74c3c' if x > 20 else '#f39c12' 
              for x in result['Subsidy_Increase_%']]
    bars1 = ax1.bar(result['ShardID'], result['Subsidy_Normalized'], 
                    color=colors, edgecolor='black', linewidth=2, alpha=0.85)
    
    # 添加基准线
    ax1.axhline(y=100, color='green', linestyle='--', linewidth=2, 
                label='Baseline (Least Congested Shard)', alpha=0.7)
    
    # 标注百分比增益
    for i, (bar, pct) in enumerate(zip(bars1, result['Subsidy_Increase_%'])):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'+{pct:.1f}%' if pct > 0 else f'{pct:.1f}%',
                ha='center', va='bottom', fontsize=13, fontweight='bold',
                color='darkred' if pct > 0 else 'darkgreen')
        
        # 在柱内标注绝对值
        ax1.text(bar.get_x() + bar.get_width()/2., height/2,
                f'{height:.1f}',
                ha='center', va='center', fontsize=11, color='white', fontweight='bold')
    
    ax1.set_xlabel('Shard ID', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Normalized Subsidy (%)', fontsize=14, fontweight='bold')
    ax1.set_title('Subsidy Allocation (Normalized to Weakest Shard = 100%)', 
                  fontsize=15, fontweight='bold', pad=15)
    ax1.set_ylim([95, result['Subsidy_Normalized'].max() * 1.15])
    ax1.legend(fontsize=11, loc='upper left')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # ===== 图2: 队列 vs 补贴关系（强化版）=====
    ax2 = fig.add_subplot(gs[0, 2])
    
    # 使用渐变色表示差异
    scatter = ax2.scatter(result['AvgQueueLength'] / 1000, 
                         result['TotalSubsidy_ETH'],
                         s=400, c=result['Subsidy_Increase_%'], 
                         cmap='RdYlGn_r', edgecolors='black', linewidths=2,
                         vmin=-5, vmax=30, alpha=0.9)
    
    # 添加趋势线
    z = np.polyfit(result['AvgQueueLength'], result['TotalSubsidy_ETH'], 1)
    p = np.poly1d(z)
    x_trend = np.linspace(result['AvgQueueLength'].min(), 
                         result['AvgQueueLength'].max(), 100)
    ax2.plot(x_trend / 1000, p(x_trend), "r--", linewidth=3, alpha=0.8,
            label=f'Trend: R² = {np.corrcoef(result["AvgQueueLength"], result["TotalSubsidy_ETH"])[0,1]**2:.3f}')
    
    # 标注分片ID和增益
    for _, row in result.iterrows():
        ax2.annotate(f'S{int(row["ShardID"])}\n+{row["Subsidy_Increase_%"]:.0f}%', 
                    (row['AvgQueueLength'] / 1000, row['TotalSubsidy_ETH']),
                    xytext=(8, 8), textcoords='offset points', 
                    fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    ax2.set_xlabel('Avg Queue (×1000)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Total Subsidy (ETH)', fontsize=12, fontweight='bold')
    ax2.set_title('Queue Congestion\nvs Subsidy', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=9, loc='lower right')
    ax2.grid(True, alpha=0.3)
    
    # 添加色条
    cbar = plt.colorbar(scatter, ax=ax2, orientation='horizontal', pad=0.1, aspect=15)
    cbar.set_label('Subsidy Gain (%)', fontsize=9)
    
    # ===== 图3: 每笔交易补贴对比（带百分比）=====
    ax3 = fig.add_subplot(gs[1, 0])
    
    min_avg = result['AvgSubsidy_Gwei'].min()
    result['AvgGain_%'] = ((result['AvgSubsidy_Gwei'] / min_avg) - 1) * 100
    
    bars3 = ax3.barh(result['ShardID'].astype(str), result['AvgSubsidy_Gwei'],
                     color=sns.color_palette('coolwarm', len(result)),
                     edgecolor='black', linewidth=1.5)
    
    for bar, val, gain in zip(bars3, result['AvgSubsidy_Gwei'], result['AvgGain_%']):
        width = bar.get_width()
        ax3.text(width + 0.05, bar.get_y() + bar.get_height()/2,
                f'{val:.2f} Gwei\n(+{gain:.0f}%)',
                ha='left', va='center', fontsize=10, fontweight='bold')
    
    ax3.set_ylabel('Shard ID', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Avg Subsidy per CTX (Gwei)', fontsize=12, fontweight='bold')
    ax3.set_title('Per-Transaction Subsidy', fontsize=13, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3, axis='x')
    
    # ===== 图4: 相关性强度可视化 =====
    ax4 = fig.add_subplot(gs[1, 1])
    
    corr_total = result['AvgQueueLength'].corr(result['TotalSubsidy_ETH'])
    corr_per_tx = result['AvgQueueLength'].corr(result['AvgSubsidy_Gwei'])
    
    metrics = ['Queue vs\nTotal Subsidy', 'Queue vs\nPer-Tx Subsidy']
    corr_values = [corr_total, corr_per_tx]
    colors_corr = ['#27ae60' if c > 0.5 else '#f39c12' if c > 0.3 else '#e74c3c' 
                   for c in corr_values]
    
    bars4 = ax4.bar(metrics, corr_values, color=colors_corr, 
                    edgecolor='black', linewidth=2, alpha=0.85)
    
    ax4.axhline(y=0.5, color='green', linestyle='--', linewidth=2, alpha=0.5,
                label='Strong Correlation')
    ax4.axhline(y=0.3, color='orange', linestyle='--', linewidth=2, alpha=0.5,
                label='Moderate Correlation')
    
    for bar, val in zip(bars4, corr_values):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.03,
                f'ρ = {val:.3f}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    ax4.set_ylabel('Correlation Coefficient (ρ)', fontsize=12, fontweight='bold')
    ax4.set_title('Fairness Correlation Strength', fontsize=13, fontweight='bold', pad=10)
    ax4.set_ylim([0, 1])
    ax4.legend(fontsize=9, loc='upper left')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # ===== 图5: 资源分配表格 =====
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.axis('off')
    
    # 创建总结表格
    table_data = []
    for _, row in result.iterrows():
        table_data.append([
            f"S{int(row['ShardID'])}",
            f"{row['AvgQueueLength']/1000:.1f}k",
            f"{row['TotalSubsidy_ETH']:.3f}",
            f"+{row['Subsidy_Increase_%']:.0f}%" if row['Subsidy_Increase_%'] > 0 else "Baseline"
        ])
    
    table = ax5.table(cellText=table_data,
                     colLabels=['Shard', 'Queue', 'Subsidy\n(ETH)', 'Gain'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    # 突出显示最高增益
    max_idx = result['Subsidy_Increase_%'].idxmax()
    for i in range(4):
        if i == max_idx:
            table[(i+1, 0)].set_facecolor('#ffcccc')
            table[(i+1, 3)].set_facecolor('#ffcccc')
    
    ax5.set_title('Resource Allocation Summary', fontsize=13, fontweight='bold', pad=20)
    
    # ===== 图6: 增益排名 =====
    ax6 = fig.add_subplot(gs[2, :])
    
    result_sorted = result.sort_values('Subsidy_Increase_%', ascending=True)
    
    bars6 = ax6.barh(result_sorted['ShardID'].astype(str), 
                     result_sorted['Subsidy_Increase_%'],
                     color=['#27ae60' if x < 5 else '#f39c12' if x < 15 else '#e74c3c' 
                           for x in result_sorted['Subsidy_Increase_%']],
                     edgecolor='black', linewidth=2, alpha=0.85)
    
    ax6.axvline(x=0, color='black', linestyle='-', linewidth=2)
    
    for bar, val, queue in zip(bars6, result_sorted['Subsidy_Increase_%'], 
                                result_sorted['AvgQueueLength']):
        width = bar.get_width()
        ax6.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}% (Queue: {queue/1000:.1f}k)',
                ha='left', va='center', fontsize=11, fontweight='bold')
    
    ax6.set_xlabel('Subsidy Gain Relative to Baseline (%)', fontsize=13, fontweight='bold')
    ax6.set_ylabel('Shard ID', fontsize=13, fontweight='bold')
    ax6.set_title('Ranking: Resource Tilt Effect (Higher = More Subsidy to Congested Shards)', 
                  fontsize=14, fontweight='bold', pad=15)
    ax6.grid(True, alpha=0.3, axis='x')
    
    plt.suptitle(f'{exp_name}: Enhanced Heterogeneous Shard Fairness Analysis', 
                fontsize=17, fontweight='bold', y=0.995)
    
    output_file = Path('figures') / 'shard_fairness_enhanced.png'
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Enhanced visualization saved: {output_file}")
    plt.close()
    
    # 打印总结
    print("\n" + "="*70)
    print("KEY FINDINGS:")
    print("="*70)
    print(f"Correlation (Queue vs Total Subsidy): {corr_total:.3f}")
    print(f"Correlation (Queue vs Per-Tx Subsidy): {corr_per_tx:.3f}")
    print(f"\nMax subsidy gain: +{result['Subsidy_Increase_%'].max():.1f}% (Shard {result.loc[result['Subsidy_Increase_%'].idxmax(), 'ShardID']:.0f})")
    print(f"This shard has {result.loc[result['Subsidy_Increase_%'].idxmax(), 'AvgQueueLength']/1000:.1f}k avg queue")
    print("="*70)

def main():
    lag_dir = '../expTest_Lagrangian_Alpha0.01'
    analyze_and_visualize(lag_dir, 'Lagrangian α=0.01')
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
