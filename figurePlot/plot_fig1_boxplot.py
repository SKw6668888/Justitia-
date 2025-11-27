#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图1: CTX排队延迟箱线图
Boxplot of CTX queueing latency under various subsidy solutions
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from pathlib import Path

# 设置绘图风格
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 11

# 配色方案（蓝、橙、绿、红、紫）
COLORS = {
    'Monoxide': '#3498DB',        # 蓝色
    'R=0': '#F39C12',             # 橙色
    'R=E(f_B)': '#27AE60',        # 绿色
    'R=E(f_A)+E(f_B)': '#E74C3C', # 红色
    'R=1 ETH/CTX': '#9B59B6'      # 紫色
}

def plot_fig1():
    """生成图1: CTX排队延迟箱线图"""
    print("\n" + "="*60)
    print("图1: CTX排队延迟箱线图")
    print("="*60)
    
    # 读取数据
    data_file = Path("data/fig1_queueing_latency_boxplot.json")
    if not data_file.exists():
        print(f"❌ 错误: 找不到数据文件 {data_file}")
        print("请先运行 justitia_data_analyzer.py 生成数据")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查数据
    if not data or all(len(v) == 0 for v in data.values()):
        print("❌ 错误: 数据为空")
        return False
    
    print(f"✓ 成功加载数据，包含 {len(data)} 种机制")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 准备数据
    mechanisms = list(data.keys())
    latencies = [data[m] for m in mechanisms]
    colors = [COLORS.get(m, '#95A5A6') for m in mechanisms]
    
    # 绘制箱线图
    bp = ax.boxplot(latencies, 
                    labels=mechanisms,
                    patch_artist=True,
                    widths=0.6,
                    showmeans=True,
                    meanprops=dict(marker='D', markerfacecolor='red', markersize=6))
    
    # 设置颜色
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 设置标签
    ax.set_xlabel('Subsidy Mechanism', fontweight='bold')
    ax.set_ylabel('Queueing Latency (seconds)', fontweight='bold')
    ax.set_title('Queueing Latency of CTXs under Various Subsidy Solutions', 
                 fontweight='bold', pad=20)
    
    # 网格
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.set_axisbelow(True)
    
    # 旋转x轴标签
    plt.xticks(rotation=15, ha='right')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "fig1_ctx_latency_boxplot.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {output_file}")
    
    # 显示统计信息
    print("\n统计信息:")
    for mechanism in mechanisms:
        if len(data[mechanism]) > 0:
            import numpy as np
            values = data[mechanism]
            print(f"  {mechanism}:")
            print(f"    中位数: {np.median(values):.2f}s")
            print(f"    平均值: {np.mean(values):.2f}s")
            print(f"    标准差: {np.std(values):.2f}s")
    
    plt.close()
    return True

def main():
    print("\n" + "="*60)
    print("Justitia 图表生成器 - 图1")
    print("="*60)
    
    success = plot_fig1()
    
    if success:
        print("\n✓ 图1生成成功！")
        return 0
    else:
        print("\n❌ 图1生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
