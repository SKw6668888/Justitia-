#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图6: CTX排队延迟的KDE概率密度分布
The queueing latency distribution of confirmed CTXs under various subsidy parameters R_AB, measured by KDE
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path
from scipy.stats import gaussian_kde
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

# 配色方案和标记样式
COLORS = {
    'Monoxide': '#3498DB',      # 蓝色
    'R_EB': '#27AE60',          # 绿色
    'PID': '#E74C3C',           # 红色（对应图中的R_EA_EB）
    'Lagrangian': '#F39C12',    # 橙色（对应图中的R=0）
    'R_EA_EB': '#9B59B6'        # 紫色（对应图中的1 ETH/CTX）
}

MARKERS = {
    'Monoxide': 'x',
    'R_EB': 'o',
    'PID': '^',
    'Lagrangian': 's',
    'R_EA_EB': 'p'
}

LINESTYLES = {
    'Monoxide': '-',
    'R_EB': '-',
    'PID': '-',
    'Lagrangian': '-',
    'R_EA_EB': '-'
}

# 实验数据路径配置
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian/result/supervisor_measureOutput',
    'R_EA_EB': '../expTest_R_EA_EB/result/supervisor_measureOutput'
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
        time_col = 'Tx propose timestamp'
        confirmed_col = 'Tx finally commit timestamp'
        
        if time_col in ctx_df.columns and confirmed_col in ctx_df.columns:
            ctx_df['QueueingLatency'] = (ctx_df[confirmed_col] - ctx_df[time_col]) / 1000.0
        else:
            print(f"[WARNING] {method_name} 缺少时间字段")
            return None
        
        # 过滤异常值（负延迟或过大延迟）
        # 限制在0-50秒范围内，符合图表要求
        ctx_df = ctx_df[(ctx_df['QueueingLatency'] >= 0) & (ctx_df['QueueingLatency'] <= 50)]
        
        latency = ctx_df['QueueingLatency'].values
        
        print(f"[OK] {method_name}: 加载 {len(latency)} 条CTX延迟数据")
        print(f"  - 平均延迟: {np.mean(latency):.2f}s")
        print(f"  - 中位数延迟: {np.median(latency):.2f}s")
        print(f"  - 延迟范围: [{np.min(latency):.2f}s, {np.max(latency):.2f}s]")
        
        return latency
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def plot_kde_distribution(latency_data):
    """绘制CTX排队延迟的KDE概率密度分布图"""
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # X轴范围：0-50秒
    x_range = np.linspace(0, 50, 500)
    
    # 为每个方案绘制KDE曲线
    for method in ['Monoxide', 'Lagrangian', 'R_EB', 'PID', 'R_EA_EB']:
        if method not in latency_data or latency_data[method] is None:
            continue
        
        latency = latency_data[method]
        
        # 如果数据点太少，跳过
        if len(latency) < 10:
            print(f"[WARNING] {method} 数据点太少，跳过KDE")
            continue
        
        try:
            # 使用高斯核密度估计
            kde = gaussian_kde(latency, bw_method='scott')
            density = kde(x_range)
            
            # 绘制平滑曲线
            ax.plot(x_range, density,
                    label=method,
                    color=COLORS[method],
                    linewidth=2.5,
                    linestyle=LINESTYLES[method],
                    alpha=0.85)
            
            # 添加标记点（每隔一定间隔）
            marker_indices = np.linspace(0, len(x_range)-1, 8, dtype=int)
            ax.plot(x_range[marker_indices], density[marker_indices],
                    marker=MARKERS[method],
                    color=COLORS[method],
                    markersize=8,
                    linestyle='None',
                    markeredgewidth=1.5,
                    markerfacecolor='none')
            
            print(f"[OK] {method}: KDE峰值密度 = {np.max(density):.4f}")
            
        except Exception as e:
            print(f"[ERROR] {method} KDE计算失败: {e}")
            continue
    
    # 设置坐标轴
    ax.set_xlabel('Queueing latency (sec.)', fontsize=14, fontweight='bold')
    ax.set_ylabel('KDE', fontsize=14, fontweight='bold')
    ax.set_title('The Queueing Latency Distribution of Confirmed CTXs\nUnder Various Subsidy Parameters R_AB, Measured by KDE', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置X轴范围：0-50秒
    ax.set_xlim([0, 50])
    
    # 设置Y轴范围（根据数据自动调整，但确保从0开始）
    ax.set_ylim(bottom=0)
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 添加图例（右上角）
    ax.legend(loc='upper right', framealpha=0.95, fontsize=11)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/6_ctx_latency_kde.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] KDE图片已保存: {output_file}")
    
    return True

def plot_cdf_distribution(latency_data):
    """绘制CTX排队延迟的CDF累积分布函数图"""
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # 为每个方案绘制CDF曲线
    for method in ['Monoxide', 'Lagrangian', 'R_EB', 'PID', 'R_EA_EB']:
        if method not in latency_data or latency_data[method] is None:
            continue
        
        latency = latency_data[method]
        
        # 排序数据
        sorted_latency = np.sort(latency)
        
        # 计算CDF
        cdf = np.arange(1, len(sorted_latency) + 1) / len(sorted_latency)
        
        # 绘制CDF曲线
        ax.plot(sorted_latency, cdf,
                label=method,
                color=COLORS[method],
                linewidth=2.5,
                linestyle=LINESTYLES[method],
                alpha=0.85)
        
        # 添加标记点（每隔一定间隔）
        marker_step = max(1, len(sorted_latency) // 10)
        marker_indices = range(0, len(sorted_latency), marker_step)
        ax.plot(sorted_latency[marker_indices], cdf[marker_indices],
                marker=MARKERS[method],
                color=COLORS[method],
                markersize=8,
                linestyle='None',
                markeredgewidth=1.5,
                markerfacecolor='none')
        
        # 计算并打印关键统计量
        p50 = np.percentile(latency, 50)
        p90 = np.percentile(latency, 90)
        p99 = np.percentile(latency, 99)
        print(f"[OK] {method}: P50={p50:.2f}s, P90={p90:.2f}s, P99={p99:.2f}s")
    
    # 设置坐标轴
    ax.set_xlabel('Queueing latency (sec.)', fontsize=14, fontweight='bold')
    ax.set_ylabel('CDF', fontsize=14, fontweight='bold')
    ax.set_title('Cumulative Distribution Function (CDF) of the Queueing Latency\nof Confirmed CTXs, Under Various Subsidy Parameter R_AB', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置X轴范围：0-100秒（与参考图一致）
    ax.set_xlim([0, 100])
    
    # 设置Y轴范围：0-1.05
    ax.set_ylim([0, 1.05])
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 添加图例（右下角，与参考图一致）
    ax.legend(loc='lower right', framealpha=0.95, fontsize=11)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/6_ctx_latency_cdf.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] CDF图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图6: CTX排队延迟KDE概率密度分布生成器")
    print("="*60)
    
    # 加载所有方案的延迟数据
    latency_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在加载 {method} 数据...")
        latency = load_ctx_latency(method)
        if latency is not None:
            latency_data[method] = latency
    
    # 检查是否有足够的数据
    if len(latency_data) == 0:
        print("\n[ERROR] 没有可用的数据")
        return 1
    
    # 绘制KDE分布图
    success_kde = plot_kde_distribution(latency_data)
    
    # 绘制CDF分布图
    success_cdf = plot_cdf_distribution(latency_data)
    
    if success_kde and success_cdf:
        print("\n" + "="*60)
        print("[SUCCESS] CTX延迟分布图生成成功!")
        print("="*60)
        print("\n说明:")
        print("- KDE图: 显示延迟的概率密度分布，峰值越高表示该延迟区间的CTX越集中")
        print("- CDF图: 显示延迟的累积分布函数，曲线越靠左表示延迟越低（性能越好）")
        return 0
    else:
        print("\n[ERROR] 分布图生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
