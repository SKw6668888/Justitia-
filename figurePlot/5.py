#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图5: CTX与ITX延迟比值对比
Ratio of CTX to ITX average queueing latency across different subsidy schemes
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

def calculate_latency_ratio(method_name):
    """计算CTX与ITX的平均延迟比值"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING] 文件不存在: {tx_details_file}")
        return None
    
    try:
        # 读取交易详情
        df = pd.read_csv(tx_details_file)
        
        # 只统计已确认的交易
        confirmed_col = 'Tx finally commit timestamp'
        confirmed_df = df[df[confirmed_col].notna()].copy()
        
        if len(confirmed_df) == 0:
            print(f"[WARNING] {method_name} 没有已确认的交易")
            return None
        
        # 计算排队延迟（秒）
        time_col = 'Tx propose timestamp'
        
        if time_col not in confirmed_df.columns or confirmed_col not in confirmed_df.columns:
            print(f"[WARNING] {method_name} 缺少时间字段")
            return None
        
        confirmed_df['QueueingLatency'] = (confirmed_df[confirmed_col] - confirmed_df[time_col]) / 1000.0
        
        # 过滤异常值
        confirmed_df = confirmed_df[(confirmed_df['QueueingLatency'] >= 0) & (confirmed_df['QueueingLatency'] < 1000)]
        
        # 分离CTX和ITX
        ctx_df = confirmed_df[confirmed_df['IsCrossShard'] == True]
        itx_df = confirmed_df[confirmed_df['IsCrossShard'] == False]
        
        if len(ctx_df) == 0 or len(itx_df) == 0:
            print(f"[WARNING] {method_name} CTX或ITX数据不足")
            return None
        
        # 计算平均延迟
        ctx_avg_latency = ctx_df['QueueingLatency'].mean()
        itx_avg_latency = itx_df['QueueingLatency'].mean()
        
        # 计算比值
        latency_ratio = ctx_avg_latency / itx_avg_latency if itx_avg_latency > 0 else 0
        
        print(f"[OK] {method_name}:")
        print(f"  - CTX平均延迟: {ctx_avg_latency:.2f}s")
        print(f"  - ITX平均延迟: {itx_avg_latency:.2f}s")
        print(f"  - CTX/ITX延迟比值: {latency_ratio:.3f}")
        
        return {
            'ctx_avg_latency': ctx_avg_latency,
            'itx_avg_latency': itx_avg_latency,
            'latency_ratio': latency_ratio
        }
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def plot_latency_ratio(ratio_data):
    """绘制CTX/ITX延迟比值柱状图"""
    
    # 准备数据
    methods = []
    ratios = []
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        if method in ratio_data and ratio_data[method] is not None:
            methods.append(method)
            ratios.append(ratio_data[method]['latency_ratio'])
    
    if len(methods) == 0:
        print("[ERROR] 没有可用的数据")
        return False
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 绘制柱状图
    x_pos = np.arange(len(methods))
    bars = ax.bar(x_pos, ratios, 
                   color=[COLORS[m] for m in methods],
                   alpha=0.85,
                   edgecolor='black',
                   linewidth=1.5)
    
    # 在柱子上方添加数值标签
    for i, (bar, ratio) in enumerate(zip(bars, ratios)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{ratio:.3f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # 添加参考线 y=1 (表示CTX和ITX延迟相等)
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Equal Latency (Ratio = 1)')
    
    # 设置坐标轴
    ax.set_xlabel('Subsidy Schemes', fontsize=14, fontweight='bold')
    ax.set_ylabel('CTX / ITX Latency Ratio', fontsize=14, fontweight='bold')
    ax.set_title('Ratio of CTX to ITX Average Queueing Latency\nAcross Different Subsidy Schemes', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置X轴刻度
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, fontsize=12)
    
    # 设置Y轴范围
    ax.set_ylim([0, max(ratios) * 1.2])
    
    # 添加网格
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 添加图例
    ax.legend(loc='upper right', framealpha=0.95, fontsize=10)
    
    # 添加说明文本
    textstr = 'Ratio < 1: CTX faster than ITX\n'
    textstr += 'Ratio = 1: Equal latency\n'
    textstr += 'Ratio > 1: CTX slower than ITX'
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=props)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/5_ctx_itx_latency_ratio.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图5: CTX/ITX延迟比值分析")
    print("="*60)
    
    # 计算所有方案的延迟比值
    ratio_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在分析 {method} 数据...")
        result = calculate_latency_ratio(method)
        if result is not None:
            ratio_data[method] = result
    
    # 检查是否有足够的数据
    if len(ratio_data) == 0:
        print("\n[ERROR] 没有可用的数据")
        return 1
    
    # 绘制柱状图
    success = plot_latency_ratio(ratio_data)
    
    if success:
        print("\n" + "="*60)
        print("[OK] CTX/ITX延迟比值图生成成功！")
        print("="*60)
        print("\n说明:")
        print("- 比值 < 1: CTX延迟小于ITX（补贴方案有效降低CTX延迟）")
        print("- 比值 = 1: CTX和ITX延迟相等（完全公平）")
        print("- 比值 > 1: CTX延迟大于ITX（补贴不足或无补贴）")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
