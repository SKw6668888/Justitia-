#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图3: CTX延迟KDE分布
KDE plot of CTX latency distribution (0-50s)
"""

import json
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path
from scipy import stats

# 设置绘图风格
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16

# 配色方案（蓝、橙、绿、红、紫）
COLORS = {
    'Monoxide': '#3498DB',        # 蓝色
    'R=0': '#F39C12',             # 橙色
    'R=E(f_B)': '#27AE60',        # 绿色
    'R=E(f_A)+E(f_B)': '#E74C3C', # 红色
    'R=1 ETH/CTX': '#9B59B6'      # 紫色
}

def plot_fig3():
    """生成图3: CTX延迟KDE分布"""
    print("\n" + "="*60)
    print("图3: CTX延迟KDE分布")
    print("="*60)
    
    # 读取数据
    data_file = Path("data/fig3_kde_distribution.json")
    if not data_file.exists():
        print(f"❌ 错误: 找不到数据文件 {data_file}")
        print("请先运行 justitia_data_analyzer.py 生成数据")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ 成功加载数据，包含 {len(data)} 种机制")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 绘制KDE曲线
    for mechanism, latencies in data.items():
        if len(latencies) == 0:
            print(f"  ⚠️  {mechanism}: 无数据")
            continue
        
        # 过滤0-50秒范围
        filtered = [l for l in latencies if 0 <= l <= 50]
        
        if len(filtered) < 2:
            print(f"  ⚠️  {mechanism}: 数据点不足")
            continue
        
        # 计算KDE
        try:
            kde = stats.gaussian_kde(filtered)
            x_range = np.linspace(0, 50, 500)
            density = kde(x_range)
            
            color = COLORS.get(mechanism, '#95A5A6')
            ax.plot(x_range, density, label=mechanism, color=color, linewidth=2.5, alpha=0.8)
            
            print(f"  ✓ {mechanism}: {len(filtered)} 个数据点")
        except Exception as e:
            print(f"  ❌ {mechanism}: KDE计算失败 - {e}")
    
    # 设置标签
    ax.set_xlabel('Queueing Latency (seconds)', fontweight='bold')
    ax.set_ylabel('Probability Density', fontweight='bold')
    ax.set_title('The Queueing Latency Distribution of Confirmed CTXs (KDE)', 
                 fontweight='bold', pad=20)
    
    # 设置范围
    ax.set_xlim(0, 50)
    ax.set_ylim(bottom=0)
    
    # 网格和图例
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend(loc='upper right', framealpha=0.9)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "fig3_latency_kde.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {output_file}")
    
    plt.close()
    return True

def main():
    print("\n" + "="*60)
    print("Justitia 图表生成器 - 图3")
    print("="*60)
    
    success = plot_fig3()
    
    if success:
        print("\n✓ 图3生成成功！")
        return 0
    else:
        print("\n❌ 图3生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
