#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时延比较图: Monoxide vs R_EB vs PID vs Lagrangian vs Hybrid
Latency Comparison: Monoxide, R_EB, PID, Lagrangian, and Hybrid methods
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置绘图风格
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 11
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配色方案 (5个方案)
COLORS = {
    'Monoxide': '#2ECC71',      # 绿色 (基准，最高延迟)
    'R_EB': '#9B59B6',          # 紫色 (R=E(f_B))
    'PID': '#3498DB',           # 蓝色 (Justitia-PID)
    'Lagrangian': '#E74C3C',    # 红色 (Justitia-Lagrangian)
    'Hybrid': '#F39C12'         # 橙色 (Justitia-Hybrid, 混合PID+Lagrangian)
}

# 实验数据路径配置
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian_Alpha0.01/result/supervisor_measureOutput',
    'Hybrid': '../expTest_Hybrid/result/supervisor_measureOutput'
}

def load_experiment_data(method_name):
    """加载单个实验的数据"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"Warning: Data file not found for {method_name}: {tx_details_file}")
        return None
    
    try:
        df = pd.read_csv(tx_details_file)
        print(f"Loaded {method_name} data: {len(df):,} records")
        return df
    except Exception as e:
        print(f"Error loading {method_name} data: {e}")
        return None

def classify_transactions(df):
    """分类交易类型 (CTX vs ITX)"""
    # CTX: 跨片交易 (IsCrossShard == True)
    if 'IsCrossShard' in df.columns:
        cross_shard_mask = df['IsCrossShard'] == True
    else:
        # 备用方法: 有relay时间戳
        cross_shard_mask = (df['Relay1 Tx commit timestamp (not a relay tx -> nil)'].notna()) | \
                          (df['Relay2 Tx commit timestamp (not a relay tx -> nil)'].notna())
    
    inner_shard_mask = ~cross_shard_mask
    return cross_shard_mask, inner_shard_mask

def extract_latency_metrics(df, method_name):
    """提取时延指标"""
    cross_shard_mask, inner_shard_mask = classify_transactions(df)
    
    latency_column = 'Confirmed latency of this tx (ms)'
    
    # 提取CTX和ITX的时延数据
    ctx_latency = df[cross_shard_mask][latency_column].dropna()
    itx_latency = df[inner_shard_mask][latency_column].dropna()
    
    if len(ctx_latency) == 0 or len(itx_latency) == 0:
        print(f"Warning: {method_name} missing CTX or ITX data")
        return None
    
    metrics = {
        'method': method_name,
        'ctx_mean': ctx_latency.mean(),
        'ctx_median': ctx_latency.median(),
        'ctx_std': ctx_latency.std(),
        'ctx_p25': ctx_latency.quantile(0.25),
        'ctx_p75': ctx_latency.quantile(0.75),
        'ctx_p95': ctx_latency.quantile(0.95),
        'ctx_p99': ctx_latency.quantile(0.99),
        'itx_mean': itx_latency.mean(),
        'itx_median': itx_latency.median(),
        'latency_ratio': ctx_latency.mean() / itx_latency.mean() if itx_latency.mean() > 0 else 0,
        'ctx_latency_data': ctx_latency,
        'itx_latency_data': itx_latency,
        'ctx_count': len(ctx_latency),
        'itx_count': len(itx_latency)
    }
    
    return metrics

def plot_latency_comparison(all_metrics):
    """绘制时延比较图"""
    print("\n" + "="*60)
    print("Generating Latency Comparison Plots")
    print("="*60)
    
    methods = [m['method'] for m in all_metrics]
    colors = [COLORS[m] for m in methods]
    
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    
    # ========== 图1: CTX平均时延柱状图 ==========
    print("\nGenerating Figure 1: CTX Mean Latency Bar Chart...")
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    
    ctx_means = [m['ctx_mean'] for m in all_metrics]
    bars1 = ax1.bar(methods, ctx_means, color=colors, alpha=0.85, 
                    edgecolor='black', linewidth=1.5, width=0.6)
    
    # 添加数值标签
    for bar, val in zip(bars1, ctx_means):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.2f} ms',
                ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax1.set_ylabel('Mean CTX Latency (ms)', fontweight='bold', fontsize=14)
    ax1.set_xlabel('Mechanisms', fontweight='bold', fontsize=14)
    ax1.set_title('Cross-Shard Transaction (CTX) Mean Latency Comparison', 
                  fontweight='bold', fontsize=16, pad=20)
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.set_axisbelow(True)
    ax1.set_ylim([0, max(ctx_means) * 1.15])
    
    output_file1 = output_dir / "latency_comparison_mean.png"
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file1}")
    plt.close()
    
    # ========== 图2: P95/P99 Tail Latency对比 ==========
    print("Generating Figure 2: Tail Latency (P95, P99)...")
    fig2, ax2 = plt.subplots(figsize=(13, 8))
    
    x = np.arange(len(methods))
    width = 0.35
    
    p95_values = [m['ctx_p95'] for m in all_metrics]
    p99_values = [m['ctx_p99'] for m in all_metrics]
    
    bars_p95 = ax2.bar(x - width/2, p95_values, width, 
                       label='P95 Latency', alpha=0.8, edgecolor='black', linewidth=1.5,
                       color='#3498DB')
    bars_p99 = ax2.bar(x + width/2, p99_values, width,
                       label='P99 Latency', alpha=0.8, edgecolor='black', linewidth=1.5,
                       color='#E74C3C')
    
    # 添加数值标签
    for bar, val in zip(bars_p95, p95_values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.1f}',
                ha='center', va='bottom', fontsize=9)
    
    for bar, val in zip(bars_p99, p99_values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.1f}',
                ha='center', va='bottom', fontsize=9)
    
    ax2.set_ylabel('Tail Latency (ms)', fontweight='bold', fontsize=14)
    ax2.set_xlabel('Mechanisms', fontweight='bold', fontsize=14)
    ax2.set_title('CTX Tail Latency: P95 and P99', 
                  fontweight='bold', fontsize=16, pad=20)
    ax2.set_xticks(x)
    ax2.set_xticklabels(methods)
    ax2.legend(fontsize=12, loc='upper right')
    ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax2.set_axisbelow(True)
    
    output_file2 = output_dir / "latency_comparison_tail.png"
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file2}")
    plt.close()
    
    # ========== 图3: Latency Reduction相对于Monoxide ==========
    print("Generating Figure 3: Latency Reduction vs Monoxide...")
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    
    # 计算相对Monoxide的延迟降低百分比
    monoxide_mean = next((m['ctx_mean'] for m in all_metrics if m['method'] == 'Monoxide'), None)
    
    if monoxide_mean:
        reductions = []
        for m in all_metrics:
            reduction = ((monoxide_mean - m['ctx_mean']) / monoxide_mean) * 100
            reductions.append(reduction)
        
        bars3 = ax3.bar(methods, reductions, 
                       color=[COLORS[m] for m in methods], 
                       alpha=0.85, edgecolor='black', linewidth=1.5, width=0.6)
        
        # 添加0基准线
        ax3.axhline(y=0, color='gray', linestyle='-', linewidth=2, alpha=0.5)
        
        # 添加数值标签
        for bar, val in zip(bars3, reductions):
            height = bar.get_height()
            label_y = height + 1 if height >= 0 else height - 1
            ax3.text(bar.get_x() + bar.get_width()/2., label_y,
                    f'{val:.1f}%',
                    ha='center', va='bottom' if height >= 0 else 'top', 
                    fontweight='bold', fontsize=11)
        
        ax3.set_ylabel('Latency Reduction (%)', fontweight='bold', fontsize=14)
        ax3.set_xlabel('Mechanisms', fontweight='bold', fontsize=14)
        ax3.set_title('CTX Latency Reduction Relative to Monoxide Baseline', 
                      fontweight='bold', fontsize=16, pad=20)
        ax3.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax3.set_axisbelow(True)
        
        output_file3 = output_dir / "latency_comparison_reduction.png"
        plt.savefig(output_file3, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_file3}")
        plt.close()
    
    # ========== 图4: CTX/ITX Latency Ratio (Fairness指标) ==========
    print("Generating Figure 4: CTX/ITX Latency Ratio...")
    fig4, ax4 = plt.subplots(figsize=(12, 8))
    
    latency_ratios = [m['latency_ratio'] for m in all_metrics]
    bars4 = ax4.bar(methods, latency_ratios, 
                   color=[COLORS[m] for m in methods], 
                   alpha=0.85, edgecolor='black', linewidth=1.5, width=0.6)
    
    # 添加公平线 (理想值 = 1.0, CTX = ITX)
    ax4.axhline(y=1.0, color='green', linestyle='--', linewidth=2.5, 
                label='Perfect Fairness (CTX = ITX)', alpha=0.8)
    
    # 添加数值标签
    for bar, val in zip(bars4, latency_ratios):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.2f}×',
                ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax4.set_ylabel('Average Latency Ratio ($W_{CTX} / W_{ITX}$)', 
                   fontweight='bold', fontsize=14)
    ax4.set_xlabel('Mechanisms', fontweight='bold', fontsize=14)
    ax4.set_title('CTX to ITX Latency Ratio (Lower is Fairer)', 
                  fontweight='bold', fontsize=16, pad=20)
    ax4.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax4.set_axisbelow(True)
    ax4.legend(fontsize=12, loc='upper right')
    ax4.set_ylim([0, max(latency_ratios) * 1.15])
    
    output_file4 = output_dir / "latency_comparison_ratio.png"
    plt.savefig(output_file4, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_file4}")
    plt.close()
    
    return True

def print_statistics_table(all_metrics):
    """打印统计表格"""
    print("\n" + "="*120)
    print("Latency Statistics Comparison Table")
    print("="*120)
    
    print(f"\n{'Method':<15} {'CTX Mean':<12} {'CTX Median':<12} {'CTX P95':<10} "
          f"{'CTX P99':<10} {'Ratio(CTX/ITX)':<15} {'Rating':<10}")
    print("-" * 120)
    
    for metrics in all_metrics:
        ratio = metrics['latency_ratio']
        if ratio < 1.5:
            rating = "Excellent"
        elif ratio < 2.0:
            rating = "Good"
        elif ratio < 3.0:
            rating = "Fair"
        else:
            rating = "Poor"
        
        print(f"{metrics['method']:<15} {metrics['ctx_mean']:<12.2f} "
              f"{metrics['ctx_median']:<12.2f} {metrics['ctx_p95']:<10.2f} "
              f"{metrics['ctx_p99']:<10.2f} {ratio:<15.2f} {rating:<10}")
    
    # 计算改进百分比
    monoxide_mean = next((m['ctx_mean'] for m in all_metrics if m['method'] == 'Monoxide'), None)
    
    if monoxide_mean:
        print("\n" + "="*120)
        print("Latency Reduction vs Monoxide Baseline")
        print("="*120)
        print(f"\n{'Method':<15} {'Mean Latency (ms)':<20} {'Reduction (%)':<20}")
        print("-" * 60)
        
        for m in all_metrics:
            reduction = ((monoxide_mean - m['ctx_mean']) / monoxide_mean) * 100
            print(f"{m['method']:<15} {m['ctx_mean']:<20.2f} {reduction:<20.2f}")
    
    print("\n" + "="*120)
    print("Transaction Count Statistics")
    print("="*120)
    
    print(f"\n{'Method':<15} {'CTX Count':<15} {'ITX Count':<15} {'Total':<15} {'CTX Ratio':<15}")
    print("-" * 90)
    
    for metrics in all_metrics:
        total = metrics['ctx_count'] + metrics['itx_count']
        ctx_percentage = (metrics['ctx_count'] / total * 100) if total > 0 else 0
        print(f"{metrics['method']:<15} {metrics['ctx_count']:<15,} "
              f"{metrics['itx_count']:<15,} {total:<15,} {ctx_percentage:<15.2f}%")

def main():
    """主函数"""
    print("\n" + "="*60)
    print("Justitia Latency Comparison Tool")
    print("Comparing: Monoxide, R_EB, PID, Lagrangian, Hybrid")
    print("="*60)
    
    # 加载所有方法的数据
    all_metrics = []
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'Hybrid']:
        print(f"\nLoading {method} data...")
        df = load_experiment_data(method)
        
        if df is not None:
            metrics = extract_latency_metrics(df, method)
            if metrics is not None:
                all_metrics.append(metrics)
    
    # 检查是否有足够的数据
    if len(all_metrics) == 0:
        print("\nError: No valid experiment data found")
        print("\nPlease ensure the following directories exist with Tx_Details.csv:")
        for method, path in EXPERIMENT_PATHS.items():
            print(f"  - {path}")
        return 1
    
    if len(all_metrics) < 5:
        print(f"\nWarning: Only found data for {len(all_metrics)} methods")
        print(f"Found: {[m['method'] for m in all_metrics]}")
        print("Will generate plots with available data")
    
    # 打印统计表格
    print_statistics_table(all_metrics)
    
    # 绘制对比图表
    success = plot_latency_comparison(all_metrics)
    
    if success:
        print("\n" + "="*60)
        print("Latency comparison plots generated successfully!")
        print("="*60)
        return 0
    else:
        print("\nError generating latency comparison plots")
        return 1

if __name__ == "__main__":
    sys.exit(main())
