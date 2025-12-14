#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图2: 打包区块中CTX占比
The ratio of CTXs out of all TXs in packaged blocks
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

def calculate_ctx_ratio(method_name):
    """计算CTX在打包交易中的占比"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING] 文件不存在: {tx_details_file}")
        return None
    
    try:
        # 读取交易详情
        df = pd.read_csv(tx_details_file)
        
        # 只统计已确认的交易（有确认时间戳）
        confirmed_col = 'Tx finally commit timestamp'
        confirmed_df = df[df[confirmed_col].notna()].copy()
        
        if len(confirmed_df) == 0:
            print(f"[WARNING]  警告: {method_name} 没有已确认的交易")
            return None
        
        # 统计CTX和ITX数量
        ctx_count = len(confirmed_df[confirmed_df['IsCrossShard'] == True])
        itx_count = len(confirmed_df[confirmed_df['IsCrossShard'] == False])
        total_count = len(confirmed_df)
        
        # 计算占比
        ctx_ratio = (ctx_count / total_count * 100) if total_count > 0 else 0
        
        print(f"[OK] {method_name}:")
        print(f"  - CTX数量: {ctx_count:,}")
        print(f"  - ITX数量: {itx_count:,}")
        print(f"  - 总交易数: {total_count:,}")
        print(f"  - CTX占比: {ctx_ratio:.2f}%")
        
        return {
            'ctx_count': ctx_count,
            'itx_count': itx_count,
            'total_count': total_count,
            'ctx_ratio': ctx_ratio
        }
        
    except Exception as e:
        print(f"[ERROR] 错误: 加载 {method_name} 数据失败: {e}")
        return None

def plot_ctx_ratio(ratio_data):
    """绘制CTX占比柱状图"""
    
    # 准备数据
    methods = []
    ratios = []
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        if method in ratio_data and ratio_data[method] is not None:
            methods.append(method)
            ratios.append(ratio_data[method]['ctx_ratio'])
    
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
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{ratio:.2f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # 设置坐标轴
    ax.set_xlabel('Subsidy Schemes', fontsize=14, fontweight='bold')
    ax.set_ylabel('CTX Ratio in Packaged Blocks (%)', fontsize=14, fontweight='bold')
    ax.set_title('Ratio of CTXs Out of All Transactions\nin Packaged Blocks', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置X轴刻度
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, fontsize=12)
    
    # 设置Y轴范围
    ax.set_ylim([0, max(ratios) * 1.15])
    
    # 添加网格
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/2_ctx_ratio.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图2: CTX占比统计生成器")
    print("="*60)
    
    # 计算所有方案的CTX占比
    ratio_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在分析 {method} 数据...")
        result = calculate_ctx_ratio(method)
        if result is not None:
            ratio_data[method] = result
    
    # 检查是否有足够的数据
    if len(ratio_data) == 0:
        print("\n[ERROR] 错误: 没有可用的数据")
        return 1
    
    # 绘制柱状图
    success = plot_ctx_ratio(ratio_data)
    
    if success:
        print("\n" + "="*60)
        print("[OK] CTX占比图生成成功！")
        print("="*60)
        return 0
    else:
        print("\n[ERROR] CTX占比图生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
