#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时延比较图: Monoxide vs R_EB vs PID vs Lagrangian vs R_EA_EB
Latency Comparison: Monoxide, R_EB, PID, Lagrangian, and R_EA_EB methods
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

# 配色方案
COLORS = {
    'Monoxide': '#27AE60',      # 绿色 (基准)
    'R_EB': '#9B59B6',          # 紫色 (R=E(f_B))
    'PID': '#3498DB',           # 蓝色
    'Lagrangian': '#E74C3C',    # 红色
    'R_EA_EB': '#F39C12'        # 橙色 (R=E(f_A)+E(f_B))
}

# 实验数据路径配置（5个方案）
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian/result/supervisor_measureOutput',
    'R_EA_EB': '../expTest_R_EA_EB/result/supervisor_measureOutput'
}

def load_experiment_data(method_name):
    """加载单个实验的数据"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"⚠️  警告: 找不到 {method_name} 的数据文件: {tx_details_file}")
        return None
    
    try:
        df = pd.read_csv(tx_details_file)
        print(f"✓ 成功加载 {method_name} 数据: {len(df)} 条记录")
        return df
    except Exception as e:
        print(f"❌ 加载 {method_name} 数据失败: {e}")
        return None

def classify_transactions(df):
    """分类交易类型 (CTX vs ITX)"""
    # CTX: 跨片交易 (有relay交易时间戳)
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
        print(f"⚠️  警告: {method_name} 缺少CTX或ITX数据")
        return None
    
    metrics = {
        'method': method_name,
        'ctx_mean': ctx_latency.mean(),
        'ctx_median': ctx_latency.median(),
        'ctx_std': ctx_latency.std(),
        'ctx_p25': ctx_latency.quantile(0.25),
        'ctx_p75': ctx_latency.quantile(0.75),
        'ctx_p95': ctx_latency.quantile(0.95),
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
    """绘制时延比较图（分别生成3张独立图片）"""
    print("\n" + "="*60)
    print("生成时延比较图")
    print("="*60)
    
    methods = [m['method'] for m in all_metrics]
    colors = [COLORS[m] for m in methods]
    
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    
    # ========== 图1: CTX平均时延柱状图 ==========
    print("\n正在生成图1: CTX平均时延柱状图...")
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    
    ctx_means = [m['ctx_mean'] for m in all_metrics]
    bars1 = ax1.bar(methods, ctx_means, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 添加数值标签
    for bar, val in zip(bars1, ctx_means):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}',
                ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax1.set_ylabel('Mean Latency (ms)', fontweight='bold', fontsize=14)
    ax1.set_xlabel('Methods', fontweight='bold', fontsize=14)
    ax1.set_title('CTX Mean Latency Comparison', fontweight='bold', fontsize=16, pad=20)
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.set_axisbelow(True)
    
    output_file1 = output_dir / "latency_comparison_1_mean.png"
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    print(f"✓ 图1已保存: {output_file1}")
    plt.close()
    
    # ========== 图2: CTX/ITX时延比率 ==========
    print("正在生成图2: CTX/ITX时延比率...")
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    
    latency_ratios = [m['latency_ratio'] for m in all_metrics]
    bars2 = ax2.bar(methods, latency_ratios, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 添加公平线
    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=2, 
                label='Fairness Line (CTX = ITX)', alpha=0.7)
    
    # 添加数值标签
    for bar, val in zip(bars2, latency_ratios):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}x',
                ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax2.set_ylabel('Latency Ratio (CTX/ITX)', fontweight='bold', fontsize=14)
    ax2.set_xlabel('Methods', fontweight='bold', fontsize=14)
    ax2.set_title('CTX to ITX Latency Ratio', fontweight='bold', fontsize=16, pad=20)
    ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax2.set_axisbelow(True)
    ax2.legend(loc='upper right', fontsize=12)
    
    output_file2 = output_dir / "latency_comparison_2_ratio.png"
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"✓ 图2已保存: {output_file2}")
    plt.close()
    
    # ========== 图3: 箱线图对比 ==========
    print("正在生成图3: CTX时延分布箱线图...")
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    
    # 准备箱线图数据
    ctx_data = [m['ctx_latency_data'] for m in all_metrics]
    bp = ax3.boxplot(ctx_data, 
                     labels=methods,
                     patch_artist=True,
                     widths=0.6,
                     showmeans=True,
                     meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    
    # 设置颜色
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax3.set_ylabel('CTX Latency (ms)', fontweight='bold', fontsize=14)
    ax3.set_xlabel('Methods', fontweight='bold', fontsize=14)
    ax3.set_title('CTX Latency Distribution (Boxplot)', fontweight='bold', fontsize=16, pad=20)
    ax3.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax3.set_axisbelow(True)
    
    output_file3 = output_dir / "latency_comparison_3_boxplot.png"
    plt.savefig(output_file3, dpi=300, bbox_inches='tight')
    print(f"✓ 图3已保存: {output_file3}")
    plt.close()
    
    return True

def print_statistics_table(all_metrics):
    """打印统计表格"""
    print("\n" + "="*100)
    print("时延统计对比表")
    print("="*100)
    
    print(f"\n{'方法':<15} {'CTX平均(ms)':<15} {'CTX中位数(ms)':<15} {'CTX标准差(ms)':<15} {'时延比率':<15} {'评级':<15}")
    print("-" * 100)
    
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
        
        print(f"{metrics['method']:<15} {metrics['ctx_mean']:<15.2f} "
              f"{metrics['ctx_median']:<15.2f} {metrics['ctx_std']:<15.2f} "
              f"{ratio:<15.2f} {rating:<15}")
    
    print("\n" + "="*100)
    print("交易数量统计")
    print("="*100)
    
    print(f"\n{'方法':<15} {'CTX数量':<15} {'ITX数量':<15} {'总数':<15} {'CTX占比':<15}")
    print("-" * 75)
    
    for metrics in all_metrics:
        total = metrics['ctx_count'] + metrics['itx_count']
        ctx_percentage = (metrics['ctx_count'] / total * 100) if total > 0 else 0
        print(f"{metrics['method']:<15} {metrics['ctx_count']:<15,} "
              f"{metrics['itx_count']:<15,} {total:<15,} {ctx_percentage:<15.2f}%")

def main():
    """主函数"""
    print("\n" + "="*60)
    print("Justitia 时延比较图生成器")
    print("Monoxide vs R_EB vs PID vs Lagrangian vs R_EA_EB")
    print("="*60)
    
    # 加载所有方法的数据（5个方案）
    all_metrics = []
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在加载 {method} 数据...")
        df = load_experiment_data(method)
        
        if df is not None:
            metrics = extract_latency_metrics(df, method)
            if metrics is not None:
                all_metrics.append(metrics)
    
    # 检查是否有足够的数据
    if len(all_metrics) == 0:
        print("\n❌ 错误: 没有找到任何有效的实验数据")
        print("\n请确保以下目录存在并包含 Tx_Details.csv 文件:")
        for method, path in EXPERIMENT_PATHS.items():
            print(f"  - {path}")
        return 1
    
    if len(all_metrics) < 4:
        print(f"\n⚠️  警告: 只找到 {len(all_metrics)} 个方法的数据")
        print(f"已找到的方法: {[m['method'] for m in all_metrics]}")
        print("将使用现有数据生成图表")
    
    # 打印统计表格
    print_statistics_table(all_metrics)
    
    # 绘制对比图表
    success = plot_latency_comparison(all_metrics)
    
    if success:
        print("\n" + "="*60)
        print("✓ 时延比较图生成成功！")
        print("="*60)
        return 0
    else:
        print("\n❌ 时延比较图生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
