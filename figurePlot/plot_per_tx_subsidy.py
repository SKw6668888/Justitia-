#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简洁版分片公平性可视化 - 仅Per-Transaction补贴对比
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 14
sns.set_style("whitegrid")

def create_simple_plot(exp_dir):
    """创建简洁的单图可视化"""
    
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
    
    # 3.5 重新排序: 2, 1, 0, 3
    custom_order = [2, 1, 0, 3]
    result['sort_key'] = result['ShardID'].apply(lambda x: custom_order.index(x) if x in custom_order else 999)
    result = result.sort_values('sort_key').reset_index(drop=True)
    
    # 4. 计算相关性
    correlation = result['AvgQueueLength'].corr(result['AvgSubsidy_Gwei'])
    
    # 5. 创建大图（纵向柱状图）
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 绘制柱状图（纵向）
    colors = sns.color_palette('coolwarm', len(result))
    bars = ax.bar(result['ShardID'].astype(str), result['AvgSubsidy_Gwei'],
                  color=colors, edgecolor='black', linewidth=2, alpha=0.85, width=0.6)
    
    # 在柱顶标注数值
    for bar, val in zip(bars, result['AvgSubsidy_Gwei']):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.3f} Gwei',
                ha='center', va='bottom', fontsize=13, fontweight='bold')
    
    # 绘制趋势线 - 直接连接各柱状图的实际补贴值
    x_positions = np.arange(len(result))
    y_actual = result['AvgSubsidy_Gwei'].values
    
    # 绘制趋势曲线 - 使用实际补贴值
    ax2 = ax.twinx()
    line = ax2.plot(x_positions, y_actual, 'r--', linewidth=3, alpha=0.7, 
                    marker='o', markersize=8, label='Trend Line')
    ax2.set_ylabel('Trend (Same Scale)', fontsize=14, fontweight='bold', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.set_ylim(ax.get_ylim())  # 保持相同的y轴范围
    
    # 在曲线旁标注相关度
    mid_idx = len(result) // 2
    mid_x = x_positions[mid_idx]
    mid_y = y_actual[mid_idx]
    ax2.annotate(f'Correlation: ρ = {correlation:.2f}',
                xy=(mid_x, mid_y),
                xytext=(mid_x + 0.3, mid_y + 0.15),
                fontsize=12, color='darkred', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8, edgecolor='red', linewidth=2),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))
    
    # 设置标签
    ax.set_xlabel('Shard ID', fontsize=16, fontweight='bold')
    ax.set_ylabel('Average Subsidy per CTX (Gwei)', fontsize=16, fontweight='bold')
    ax.set_title('Per-Transaction Subsidy Allocation Across Shards\n(Demonstrating Congestion-Aware Resource Tilt)', 
                 fontsize=17, fontweight='bold', pad=20)
    
    # 添加网格
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    ax.set_axisbelow(True)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存
    output_file = Path('figures') / 'per_tx_subsidy_simple.png'
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Figure saved: {output_file}")
    print(f"Correlation (Queue vs Per-Tx Subsidy): {correlation:.3f}")
    
    plt.close()

def main():
    lag_dir = '../expTest_Lagrangian_Alpha0.01'
    create_simple_plot(lag_dir)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
