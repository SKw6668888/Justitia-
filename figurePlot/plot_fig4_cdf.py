#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图4: CTX延迟CDF
Cumulative Distribution Function of CTX latency
"""

import json
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

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

def plot_fig4():
    """生成图4: CTX延迟CDF"""
    print("\n" + "="*60)
    print("图4: CTX延迟CDF")
    print("="*60)
    
    # 读取数据
    data_file = Path("data/fig4_cdf.json")
    if not data_file.exists():
        print(f"❌ 错误: 找不到数据文件 {data_file}")
        print("请先运行 justitia_data_analyzer.py 生成数据")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ 成功加载数据，包含 {len(data)} 种机制")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 绘制CDF曲线
    for mechanism, latencies in data.items():
        if len(latencies) == 0:
            print(f"  ⚠️  {mechanism}: 无数据")
            continue
        
        # 排序数据
        sorted_data = np.sort(latencies)
        # 计算CDF
        cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        
        color = COLORS.get(mechanism, '#95A5A6')
        ax.plot(sorted_data, cdf, label=mechanism, color=color, linewidth=2.5, alpha=0.8)
        
        # 计算中位数
        median = np.median(latencies)
        print(f"  ✓ {mechanism}: {len(latencies)} 个数据点, 中位数={median:.2f}s")
    
    # 设置标签
    ax.set_xlabel('Queueing Latency (seconds)', fontweight='bold')
    ax.set_ylabel('Cumulative Probability', fontweight='bold')
    ax.set_title('Cumulative Distribution Function (CDF) of the Queueing Latency', 
                 fontweight='bold', pad=20)
    
    # 设置范围
    ax.set_ylim(0, 1)
    ax.set_xlim(left=0)
    
    # 网格和图例
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend(loc='lower right', framealpha=0.9)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "fig4_latency_cdf.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {output_file}")
    
    plt.close()
    return True

def main():
    print("\n" + "="*60)
    print("Justitia 图表生成器 - 图4")
    print("="*60)
    
    success = plot_fig4()
    
    if success:
        print("\n✓ 图4生成成功！")
        return 0
    else:
        print("\n❌ 图4生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
