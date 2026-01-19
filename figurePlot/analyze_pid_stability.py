#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PID控制器稳定性分析 - 从现有数据提取时间序列
Extract time-series data to analyze PID controller stability
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 11
sns.set_style("whitegrid")

def extract_timeseries(exp_dir, exp_name):
    """从实验数据提取补贴时间序列"""
    
    print(f"\n{'='*70}")
    print(f"Analyzing: {exp_name}")
    print('='*70)
    
    tx_path = Path(exp_dir) / 'result' / 'supervisor_measureOutput' / 'Tx_Details.csv'
    if not tx_path.exists():
        print(f"Error: {tx_path} not found")
        return None
    
    # 加载数据
    df = pd.read_csv(tx_path)
    ctx = df[(df['IsCrossShard'] == True) & 
             (df['Tx finally commit timestamp'].notna())].copy()
    
    print(f"Total CTX: {len(ctx):,}")
    
    # 按时间窗口聚合（模拟Epoch）
    # 使用Block propose timestamp作为时间轴
    ctx['timestamp_sec'] = ctx['Tx propose timestamp'] / 1000  # 转换为秒
    ctx['epoch'] = (ctx['timestamp_sec'] - ctx['timestamp_sec'].min()) // 2  # 每2秒一个epoch（对应Block_Interval）
    
    # 按epoch和目标分片聚合
    timeseries = ctx.groupby(['epoch', 'ToShard']).agg({
        'SubsidyR (wei)': ['mean', 'std', 'count']
    }).reset_index()
    
    timeseries.columns = ['Epoch', 'ShardID', 'AvgSubsidy_wei', 'StdSubsidy_wei', 'TxCount']
    timeseries['AvgSubsidy_ETH'] = timeseries['AvgSubsidy_wei'] / 1e18
    timeseries['StdSubsidy_ETH'] = timeseries['StdSubsidy_wei'] / 1e18
    
    print(f"Epochs covered: {timeseries['Epoch'].min():.0f} - {timeseries['Epoch'].max():.0f}")
    print(f"Total epochs: {timeseries['Epoch'].nunique()}")
    
    return timeseries

def analyze_stability(timeseries_df, shard_id):
    """分析单个分片的稳定性指标"""
    
    shard_data = timeseries_df[timeseries_df['ShardID'] == shard_id].sort_values('Epoch')
    
    if len(shard_data) < 20:
        return None
    
    subsidy = shard_data['AvgSubsidy_ETH'].values
    epochs = shard_data['Epoch'].values
    
    # 1. 方差（Variance）
    variance = np.var(subsidy)
    
    # 2. 标准差（Std）
    std = np.std(subsidy)
    
    # 3. 变异系数（Coefficient of Variation）
    cv = std / np.mean(subsidy) if np.mean(subsidy) > 0 else 0
    
    # 4. 最大波动幅度
    max_change = np.max(np.abs(np.diff(subsidy)))
    
    # 5. 检测振荡（使用自相关）
    if len(subsidy) > 10:
        autocorr = np.corrcoef(subsidy[:-1], subsidy[1:])[0, 1]
    else:
        autocorr = 0
    
    # 6. 趋势（线性拟合斜率）
    if len(epochs) > 1:
        slope, intercept = np.polyfit(epochs, subsidy, 1)
    else:
        slope = 0
    
    return {
        'shard_id': shard_id,
        'variance': variance,
        'std': std,
        'cv': cv,
        'max_change_ETH': max_change,
        'autocorr': autocorr,
        'trend_slope': slope,
        'mean_subsidy': np.mean(subsidy),
        'epochs': len(subsidy)
    }

def visualize_timeseries(timeseries_df, exp_name, output_dir='figures'):
    """可视化时间序列"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    shards = sorted(timeseries_df['ShardID'].unique())
    colors = sns.color_palette('husl', len(shards))
    
    # 图1: 补贴时间序列
    ax1 = axes[0, 0]
    for shard_id, color in zip(shards, colors):
        shard_data = timeseries_df[timeseries_df['ShardID'] == shard_id].sort_values('Epoch')
        ax1.plot(shard_data['Epoch'], shard_data['AvgSubsidy_ETH'], 
                label=f'Shard {shard_id}', color=color, linewidth=2, alpha=0.8)
        
        # 添加标准差阴影
        ax1.fill_between(shard_data['Epoch'], 
                         shard_data['AvgSubsidy_ETH'] - shard_data['StdSubsidy_ETH']/1e18,
                         shard_data['AvgSubsidy_ETH'] + shard_data['StdSubsidy_ETH']/1e18,
                         color=color, alpha=0.15)
    
    ax1.set_xlabel('Epoch', fontweight='bold')
    ax1.set_ylabel('Average Subsidy (ETH)', fontweight='bold')
    ax1.set_title('Subsidy Time Series (PID Controller Output)', fontweight='bold', pad=10)
    ax1.legend(loc='best', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # 图2: 交易量时间序列
    ax2 = axes[0, 1]
    for shard_id, color in zip(shards, colors):
        shard_data = timeseries_df[timeseries_df['ShardID'] == shard_id].sort_values('Epoch')
        ax2.plot(shard_data['Epoch'], shard_data['TxCount'], 
                label=f'Shard {shard_id}', color=color, linewidth=2, alpha=0.8)
    
    ax2.set_xlabel('Epoch', fontweight='bold')
    ax2.set_ylabel('CTX Count per Epoch', fontweight='bold')
    ax2.set_title('Transaction Throughput', fontweight='bold', pad=10)
    ax2.legend(loc='best', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # 图3: 补贴变化率（一阶差分）
    ax3 = axes[1, 0]
    for shard_id, color in zip(shards, colors):
        shard_data = timeseries_df[timeseries_df['ShardID'] == shard_id].sort_values('Epoch')
        if len(shard_data) > 1:
            diff = np.diff(shard_data['AvgSubsidy_ETH'].values)
            ax3.plot(shard_data['Epoch'].values[1:], diff, 
                    label=f'Shard {shard_id}', color=color, linewidth=1.5, alpha=0.7)
    
    ax3.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax3.set_xlabel('Epoch', fontweight='bold')
    ax3.set_ylabel('Subsidy Change (ETH)', fontweight='bold')
    ax3.set_title('Rate of Change (Derivative) - Detecting Oscillations', fontweight='bold', pad=10)
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # 图4: 稳定性指标总结
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # 计算并显示稳定性指标
    stability_summary = []
    for shard_id in shards:
        stats = analyze_stability(timeseries_df, shard_id)
        if stats:
            stability_summary.append([
                f"S{int(shard_id)}",
                f"{stats['mean_subsidy']:.4f}",
                f"{stats['std']:.5f}",
                f"{stats['cv']*100:.1f}%",
                f"{stats['max_change_ETH']:.5f}"
            ])
    
    table = ax4.table(cellText=stability_summary,
                     colLabels=['Shard', 'Mean (ETH)', 'Std', 'CV', 'Max Δ'],
                     cellLoc='center',
                     loc='center',
                     bbox=[0.1, 0.2, 0.8, 0.6])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    # 标题
    ax4.text(0.5, 0.9, 'Stability Metrics Summary', ha='center', va='top',
            fontsize=14, fontweight='bold', transform=ax4.transAxes)
    
    # 说明文本
    note_text = ("CV (Coefficient of Variation): Lower is more stable\n"
                 "Max Δ: Maximum single-epoch change\n"
                 "Low values indicate robust control without oscillation")
    ax4.text(0.5, 0.05, note_text, ha='center', va='bottom',
            fontsize=8, style='italic', transform=ax4.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.suptitle(f'{exp_name}: PID Controller Stability Analysis', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    Path(output_dir).mkdir(exist_ok=True)
    output_file = Path(output_dir) / f'pid_stability_{exp_name.lower().replace(" ", "_")}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved: {output_file}")
    plt.close()
    
    return stability_summary

def main():
    # 分析PID实验
    pid_dir = '../expTest_PID'
    pid_ts = extract_timeseries(pid_dir, 'PID')
    
    if pid_ts is not None:
        stability_summary = visualize_timeseries(pid_ts, 'PID')
        
        # 打印稳定性分析
        print("\n" + "="*70)
        print("STABILITY ANALYSIS SUMMARY")
        print("="*70)
        
        for shard_id in sorted(pid_ts['ShardID'].unique()):
            stats = analyze_stability(pid_ts, shard_id)
            if stats:
                print(f"\nShard {int(shard_id)}:")
                print(f"  Mean Subsidy: {stats['mean_subsidy']:.6f} ETH")
                print(f"  Std Dev: {stats['std']:.6f} ETH")
                print(f"  CV (lower=better): {stats['cv']*100:.2f}%")
                print(f"  Max Change: {stats['max_change_ETH']:.6f} ETH")
                print(f"  Autocorrelation: {stats['autocorr']:.3f}")
                
                # 判断稳定性
                if stats['cv'] < 0.1:
                    print("  Status: HIGHLY STABLE")
                elif stats['cv'] < 0.2:
                    print("  Status: STABLE")
                else:
                    print("  Status: MODERATE OSCILLATION")
    
    # 可选: 同时分析Lagrangian
    lag_dir = '../expTest_Lagrangian_Alpha0.01'
    lag_ts = extract_timeseries(lag_dir, 'Lagrangian')
    
    if lag_ts is not None:
        visualize_timeseries(lag_ts, 'Lagrangian')
    
    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
