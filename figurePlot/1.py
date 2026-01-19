#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图1: CTX排队延迟的累积分布函数 (CDF)
Cumulative Distribution Function (CDF) of the queueing latency of confirmed CTXs
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
    'Hybrid': '#F39C12'         # 橙色 (Justitia-L)
}

# 显示名称映射
DISPLAY_NAMES = {
    'Monoxide': 'Monoxide',
    'R_EB': 'Justitia',
    'PID': 'PID',
    'Lagrangian': 'Lagrangian',
    'Hybrid': 'Justitia-L'
}

# 实验数据路径配置（5个方案）
# 注意：这些路径是相对于figurePlot目录的
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian_Alpha0.01/result/supervisor_measureOutput',
    'Hybrid': '../expTest_Hybrid/result/supervisor_measureOutput'
}

def load_ctx_latency(method_name):
    """加载CTX的排队延迟数据"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING] 文件不存在: {tx_details_file}")
        return None
    
    try:
        # 读取交易详情
        df = pd.read_csv(tx_details_file)
        
        # 筛选CTX (IsCrossShard == True)
        ctx_df = df[df['IsCrossShard'] == True].copy()
        
        if len(ctx_df) == 0:
            print(f"[WARNING] {method_name} 没有CTX数据")
            return None
        
        # 计算排队延迟（秒）
        # QueueingLatency = 确认时间 - 提交时间
        time_col = 'Tx propose timestamp'
        confirmed_col = 'Tx finally commit timestamp'
        
        if time_col in ctx_df.columns and confirmed_col in ctx_df.columns:
            ctx_df['QueueingLatency'] = (ctx_df[confirmed_col] - ctx_df[time_col]) / 1000.0  # 转换为秒
        else:
            print(f"[WARNING] {method_name} 缺少时间字段")
            print(f"  可用列: {list(ctx_df.columns)}")
            return None
        
        # 过滤异常值（负延迟或过大延迟）
        ctx_df = ctx_df[(ctx_df['QueueingLatency'] >= 0) & (ctx_df['QueueingLatency'] < 1000)]
        
        latency = ctx_df['QueueingLatency'].values
        
        print(f"[OK] {method_name}: 加载 {len(latency)} 条CTX延迟数据")
        print(f"  - 平均延迟: {np.mean(latency):.2f}s")
        print(f"  - 中位数延迟: {np.median(latency):.2f}s")
        print(f"  - 最大延迟: {np.max(latency):.2f}s")
        
        return latency
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def plot_ctx_latency_cdf(latency_data):
    """绘制CTX排队延迟的CDF图（0-50秒范围）"""
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 标记样式
    MARKERS = {
        'Monoxide': 'x',
        'R_EB': 'o',
        'PID': '^',
        'Lagrangian': 's',
        'Hybrid': 'D'
    }
    
    # 线型样式（增加区分度）
    LINESTYLES = {
        'Monoxide': '-',      # 实线
        'R_EB': '--',         # 虚线
        'PID': '-.',          # 点划线
        'Lagrangian': ':',    # 点线
        'Hybrid': '-'         # 实线
    }
    
    # 为每个方案绘制CDF（只保留0-50秒的数据）
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'Hybrid']:
        if method not in latency_data or latency_data[method] is None:
            continue
        
        latency = latency_data[method]
        
        # 排序数据
        sorted_latency = np.sort(latency)
        
        # 计算CDF
        cdf = np.arange(1, len(sorted_latency) + 1) / len(sorted_latency)
        
        # 只保留0-50秒范围内的数据点
        mask = sorted_latency <= 50
        sorted_latency_filtered = sorted_latency[mask]
        cdf_filtered = cdf[mask]
        
        # 绘制CDF曲线（使用显示名称）
        display_name = DISPLAY_NAMES[method]
        ax.plot(sorted_latency_filtered, cdf_filtered, 
                label=display_name, 
                color=COLORS[method],
                linestyle=LINESTYLES[method],
                linewidth=2.8,
                alpha=0.9)
        
        # 添加标记点（减少数量，避免过于密集）
        if len(sorted_latency_filtered) > 0:
            marker_step = max(1, len(sorted_latency_filtered) // 4)  # 减少到约4个标记
            marker_indices = range(0, len(sorted_latency_filtered), marker_step)
            ax.plot(sorted_latency_filtered[marker_indices], cdf_filtered[marker_indices],
                    marker=MARKERS[method],
                    color=COLORS[method],
                    markersize=6,  # 缩小标记尺寸
                    linestyle='None',
                    markeredgewidth=1.5,  # 同时减细边框
                    markerfacecolor='none',
                    alpha=0.9)
        
        # 打印关键统计量
        p50 = np.percentile(latency, 50)
        p90 = np.percentile(latency, 90)
        p99 = np.percentile(latency, 99)
        print(f"  - {display_name}: P50={p50:.2f}s, P90={p90:.2f}s, P99={p99:.2f}s")
    
    # 设置坐标轴
    ax.set_xlabel('CTX Queueing Latency (seconds)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Probability (CDF)', fontsize=14, fontweight='bold')
    ax.set_title('CDF of CTX Queueing Latency\nAcross Different Subsidy Schemes', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置网格
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    
    # 设置X轴范围为0-50秒
    ax.set_xlim([0, 50])
    
    # 设置Y轴范围为0-0.6，每0.1一格
    ax.set_ylim([0, 0.6])
    ax.set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    
    # 添加图例（清晰标明各方法）
    ax.legend(loc='lower right', framealpha=0.95, fontsize=12, 
              edgecolor='black', fancybox=True, shadow=True,
              title='Mechanisms', title_fontsize=13)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/1_ctx_latency_cdf.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    plt.close()
    
    # === 绘制对数X轴版本（更好地展示差异）===
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'Hybrid']:
        if method not in latency_data or latency_data[method] is None:
            continue
        
        latency = latency_data[method]
        sorted_latency = np.sort(latency)
        cdf = np.arange(1, len(sorted_latency) + 1) / len(sorted_latency)
        
        display_name = DISPLAY_NAMES[method]
        ax2.plot(sorted_latency, cdf, 
                 label=display_name, 
                 color=COLORS[method],
                 linestyle=LINESTYLES[method],
                 linewidth=2.8,
                 alpha=0.9)
        
        # 添加标记点
        marker_step = max(1, len(sorted_latency) // 8)
        marker_indices = range(0, len(sorted_latency), marker_step)
        ax2.plot(sorted_latency[marker_indices], cdf[marker_indices],
                 marker=MARKERS[method],
                 color=COLORS[method],
                 markersize=9,
                 linestyle='None',
                 markeredgewidth=2,
                 markerfacecolor='none',
                 alpha=0.9)
    
    # 使用对数X轴
    ax2.set_xscale('log')
    ax2.set_xlabel('CTX Queueing Latency (seconds, log scale)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Cumulative Probability (CDF)', fontsize=14, fontweight='bold')
    ax2.set_title('CDF of CTX Queueing Latency (Log Scale)\nAcross Different Subsidy Schemes', 
                  fontsize=16, fontweight='bold', pad=20)
    
    ax2.grid(True, alpha=0.3, linestyle='--', linewidth=0.8, which='both')
    ax2.set_ylim([0, 1.05])
    ax2.legend(loc='lower right', framealpha=0.95, fontsize=12,
               edgecolor='black', fancybox=True, shadow=True)
    
    plt.tight_layout()
    
    output_file_log = Path('figures/1_ctx_latency_cdf_log.png')
    plt.savefig(output_file_log, dpi=300, bbox_inches='tight')
    print(f"[OK] 对数版本已保存: {output_file_log}")
    
    plt.close()
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图1: CTX排队延迟CDF生成器")
    print("="*60)
    
    # 加载所有方案的延迟数据
    latency_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'Hybrid']:
        display_name = DISPLAY_NAMES[method]
        print(f"\n正在加载 {display_name} ({method}) 数据...")
        latency = load_ctx_latency(method)
        if latency is not None:
            latency_data[method] = latency
    
    # 检查是否有足够的数据
    if len(latency_data) == 0:
        print("\n[ERROR] 没有可用的数据")
        return 1
    
    # 绘制CDF图
    success = plot_ctx_latency_cdf(latency_data)
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] CTX延迟CDF图生成成功!")
        print("="*60)
        return 0
    else:
        print("\n[ERROR] CDF图生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
