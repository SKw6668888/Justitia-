#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图5: 区块中CTX占比柱状图
Bar chart of CTX ratio in packaged blocks
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

def plot_fig5():
    """生成图5: 区块中CTX占比"""
    print("\n" + "="*60)
    print("图5: 区块中CTX占比")
    print("="*60)
    
    # 读取数据
    data_file = Path("data/fig5_ctx_ratio.json")
    if not data_file.exists():
        print(f"❌ 错误: 找不到数据文件 {data_file}")
        print("请先运行 justitia_data_analyzer.py 生成数据")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ 成功加载数据，包含 {len(data)} 种机制")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 准备数据
    mechanisms = list(data.keys())
    ratios = [data[m] * 100 for m in mechanisms]  # 转换为百分比
    colors = [COLORS.get(m, '#95A5A6') for m in mechanisms]
    
    # 绘制柱状图
    x = np.arange(len(mechanisms))
    bars = ax.bar(x, ratios, color=colors, alpha=0.8, width=0.6, edgecolor='black', linewidth=1.5)
    
    # 添加数值标签
    for i, (bar, ratio) in enumerate(zip(bars, ratios)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{ratio:.1f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    # 设置标签
    ax.set_xlabel('Subsidy Mechanism', fontweight='bold')
    ax.set_ylabel('CTX Ratio in Packaged Blocks (%)', fontweight='bold')
    ax.set_title('The Ratio of CTXs out of All TXs in Packaged Blocks', 
                 fontweight='bold', pad=20)
    
    # 设置x轴
    ax.set_xticks(x)
    ax.set_xticklabels(mechanisms, rotation=15, ha='right')
    
    # 网格
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.set_axisbelow(True)
    
    # 设置y轴范围
    ax.set_ylim(0, 100)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "fig5_ctx_ratio.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {output_file}")
    
    # 显示统计信息
    print("\nCTX占比:")
    for mechanism, ratio in zip(mechanisms, ratios):
        print(f"  {mechanism}: {ratio:.1f}%")
    
    plt.close()
    return True

def main():
    print("\n" + "="*60)
    print("Justitia 图表生成器 - 图5")
    print("="*60)
    
    success = plot_fig5()
    
    if success:
        print("\n✓ 图5生成成功！")
        return 0
    else:
        print("\n❌ 图5生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
