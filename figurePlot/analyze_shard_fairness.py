#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析异构分片公平性 - Lagrangian 资源倾斜分析
Analyze Heterogeneous Shard Fairness - Lagrangian Resource Allocation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

# 设置绘图风格
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 12
sns.set_palette("husl")

def analyze_subsidy_allocation(exp_dir, exp_name):
    """分析补贴在各分片间的分配"""
    
    print(f"\n{'='*80}")
    print(f"分析实验: {exp_name}")
    print(f"{'='*80}")
    
    # 1. 加载交易数据
    tx_path = Path(exp_dir) / 'result' / 'supervisor_measureOutput' / 'Tx_Details.csv'
    if not tx_path.exists():
        print(f"Error: {tx_path} not found")
        return None
    
    df = pd.read_csv(tx_path)
    ctx = df[(df['IsCrossShard'] == True) & 
             (df['Tx finally commit timestamp'].notna())].copy()
    
    print(f"\nTotal CTX transactions: {len(ctx):,}")
    
    # 2. 计算每个分片作为目标分片时获得的补贴
    # （目标分片获得补贴的主要部分，因为它承担更多处理成本）
    
    subsidy_by_dest = ctx.groupby('ToShard').agg({
        'SubsidyR (wei)': ['sum', 'count', 'mean']
    }).reset_index()
    
    subsidy_by_dest.columns = ['ShardID', 'TotalSubsidy_wei', 'CTX_Count', 'AvgSubsidy_wei']
    
    # 转换为ETH
    subsidy_by_dest['TotalSubsidy_ETH'] = subsidy_by_dest['TotalSubsidy_wei'] / 1e18
    subsidy_by_dest['AvgSubsidy_ETH'] = subsidy_by_dest['AvgSubsidy_wei'] / 1e18
    
    print("\n--- Subsidy Allocation by Destination Shard ---")
    print(subsidy_by_dest[['ShardID', 'CTX_Count', 'TotalSubsidy_ETH', 'AvgSubsidy_ETH']])
    
    # 3. 加载队列统计（从各分片的CSV）
    shard_stats = []
    for shard_id in range(4):  # 假设4个分片
        shard_path = Path(exp_dir) / 'result' / 'pbft_shardNum=4' / f'Shard{shard_id}4.csv'
        if not shard_path.exists():
            print(f"Warning: {shard_path} not found, skipping shard {shard_id}")
            continue
        
        shard_df = pd.read_csv(shard_path)
        
        # 提取队列统计
        if 'TxPool Size' in shard_df.columns:
            avg_queue = shard_df['TxPool Size'].mean()
            max_queue = shard_df['TxPool Size'].max()
            std_queue = shard_df['TxPool Size'].std()
        else:
            print(f"Warning: No 'TxPool Size' column in {shard_path}")
            avg_queue, max_queue, std_queue = 0, 0, 0
        
        shard_stats.append({
            'ShardID': shard_id,
            'AvgQueueLength': avg_queue,
            'MaxQueueLength': max_queue,
            'StdQueueLength': std_queue,
            'BlockCount': len(shard_df)
        })
    
    queue_df = pd.DataFrame(shard_stats)
    print("\n--- Queue Statistics by Shard ---")
    print(queue_df)
    
    # 4. 合并队列和补贴数据
    result = queue_df.merge(subsidy_by_dest, on='ShardID', how='left')
    result['SubsidyPerTx'] = result['TotalSubsidy_ETH'] / result['CTX_Count']
    
    print("\n--- Combined Analysis: Queue vs Subsidy ---")
    print(result[['ShardID', 'AvgQueueLength', 'CTX_Count', 
                  'TotalSubsidy_ETH', 'SubsidyPerTx']])
    
    # 5. 计算相关性
    if len(result) > 1:
        corr_total = result['AvgQueueLength'].corr(result['TotalSubsidy_ETH'])
        corr_per_tx = result['AvgQueueLength'].corr(result['SubsidyPerTx'])
        
        print(f"\n*** Correlation Analysis ***")
        print(f"  Queue Length vs Total Subsidy: {corr_total:.3f}")
        print(f"  Queue Length vs Subsidy Per Tx: {corr_per_tx:.3f}")
        
        if corr_total > 0.5:
            print(f"  ✓ STRONG positive correlation - weaker shards get more subsidy!")
        elif corr_total > 0.2:
            print(f"  ~ MODERATE positive correlation")
        else:
            print(f"  ✗ WEAK correlation - may need heterogeneous experiment")
    else:
        corr_total, corr_per_tx = None, None
    
    return result, corr_total

def visualize_fairness(result, exp_name, output_dir='figures'):
    """可视化分片公平性"""
    
    Path(output_dir).mkdir(exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 图1: 各分片获得的总补贴（柱状图）
    ax1 = axes[0, 0]
    bars = ax1.bar(result['ShardID'], result['TotalSubsidy_ETH'], 
                   color=sns.color_palette("husl", len(result)))
    ax1.set_xlabel('Shard ID', fontweight='bold')
    ax1.set_ylabel('Total Subsidy (ETH)', fontweight='bold')
    ax1.set_title('Total Subsidy Allocation Across Shards', fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 在柱顶标注数值
    for bar, val in zip(bars, result['TotalSubsidy_ETH']):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10)
    
    # 图2: 队列长度 vs 总补贴（散点图 + 趋势线）
    ax2 = axes[0, 1]
    ax2.scatter(result['AvgQueueLength'], result['TotalSubsidy_ETH'], 
               s=200, alpha=0.7, color='coral', edgecolors='black', linewidths=2)
    
    # 添加趋势线
    if len(result) > 1:
        z = np.polyfit(result['AvgQueueLength'], result['TotalSubsidy_ETH'], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(result['AvgQueueLength'].min(), 
                             result['AvgQueueLength'].max(), 100)
        ax2.plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2, 
                label=f'Trend: y={z[0]:.4f}x+{z[1]:.2f}')
        ax2.legend()
    
    # 标注分片ID
    for _, row in result.iterrows():
        ax2.annotate(f'S{int(row["ShardID"])}', 
                    (row['AvgQueueLength'], row['TotalSubsidy_ETH']),
                    xytext=(5, 5), textcoords='offset points', fontsize=10)
    
    ax2.set_xlabel('Average Queue Length', fontweight='bold')
    ax2.set_ylabel('Total Subsidy (ETH)', fontweight='bold')
    ax2.set_title('Resource Tilt: Queue Congestion vs Subsidy', fontweight='bold', pad=15)
    ax2.grid(True, alpha=0.3)
    
    # 图3: 每笔交易的平均补贴
    ax3 = axes[1, 0]
    bars2 = ax3.bar(result['ShardID'], result['SubsidyPerTx'], 
                    color=sns.color_palette("muted", len(result)))
    ax3.set_xlabel('Shard ID', fontweight='bold')
    ax3.set_ylabel('Subsidy Per CTX (ETH)', fontweight='bold')
    ax3.set_title('Average Subsidy Per Transaction by Shard', fontweight='bold', pad=15)
    ax3.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars2, result['SubsidyPerTx']):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.4f}', ha='center', va='bottom', fontsize=9)
    
    # 图4: CTX处理量对比
    ax4 = axes[1, 1]
    bars3 = ax4.bar(result['ShardID'], result['CTX_Count'], 
                    color=sns.color_palette("pastel", len(result)))
    ax4.set_xlabel('Shard ID', fontweight='bold')
    ax4.set_ylabel('Number of CTX Processed', fontweight='bold')
    ax4.set_title('CTX Throughput by Destination Shard', fontweight='bold', pad=15)
    ax4.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars3, result['CTX_Count']):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(val):,}', ha='center', va='bottom', fontsize=10)
    
    plt.suptitle(f'{exp_name}: Heterogeneous Shard Fairness Analysis', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    output_file = Path(output_dir) / f'shard_fairness_{exp_name.lower().replace(" ", "_")}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Figure saved: {output_file}")
    
    plt.close()

def main():
    print("\n" + "="*80)
    print("异构分片公平性分析 - Lagrangian Resource Allocation")
    print("="*80)
    
    # 分析 Lagrangian 实验
    lag_dir = '../expTest_Lagrangian_Alpha0.01'
    result, correlation = analyze_subsidy_allocation(lag_dir, 'Lagrangian (α=0.01)')
    
    if result is not None and len(result) > 0:
        visualize_fairness(result, 'Lagrangian_Alpha0.01')
        
        print("\n" + "="*80)
        print("分析完成！")
        print("="*80)
        
        if correlation is not None and correlation > 0.3:
            print("\n✓ 发现正相关性！Lagrangian 机制自动向拥塞分片倾斜补贴。")
        else:
            print("\n注意：当前实验中各分片配置相同（同构），相关性可能不明显。")
            print("建议：运行异构实验（不同分片设置不同BlockSize）以更清晰地展示效果。")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
