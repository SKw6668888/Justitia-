#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图6: 累计补贴发行量（对数坐标）
Line plot of cumulative subsidy tokens issued (log scale)
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

# 配色方案（排除Monoxide和R=0，因为它们没有补贴）
COLORS = {
    'R=E(f_B)': '#27AE60',        # 绿色
    'R=E(f_A)+E(f_B)': '#E74C3C', # 红色
    'R=1 ETH/CTX': '#9B59B6'      # 紫色
}

def plot_fig6():
    """生成图6: 累计补贴发行量"""
    print("\n" + "="*60)
    print("图6: 累计补贴发行量（对数坐标）")
    print("="*60)
    
    # 读取数据
    data_file = Path("data/fig6_cumulative_subsidy.json")
    if not data_file.exists():
        print(f"❌ 错误: 找不到数据文件 {data_file}")
        print("请先运行 justitia_data_analyzer.py 生成数据")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ 成功加载数据，包含 {len(data)} 种机制")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 绘制折线图
    for mechanism, series_data in data.items():
        # 兼容 'block_heights' 和 'epochs' 两种字段名
        if 'block_heights' in series_data:
            x_values = series_data['block_heights']
        elif 'epochs' in series_data:
            x_values = series_data['epochs']
        else:
            print(f"  ⚠️  {mechanism}: 数据格式错误")
            continue
        
        if len(x_values) == 0:
            print(f"  ⚠️  {mechanism}: 无数据")
            continue
        
        block_heights = x_values
        
        # 兼容两种字段名
        if 'cumulative_subsidy_eth' in series_data:
            cumulative_subsidy_eth = series_data['cumulative_subsidy_eth']
        elif 'cumulative_subsidy' in series_data:
            # 转换为ETH单位（假设原始单位是Wei）
            cumulative_subsidy_eth = [s / 1e18 for s in series_data['cumulative_subsidy']]
        else:
            print(f"  ⚠️  {mechanism}: 缺少补贴数据字段")
            continue
        
        color = COLORS.get(mechanism, '#95A5A6')
        ax.plot(block_heights, cumulative_subsidy_eth, 
                label=mechanism, color=color, linewidth=2.5, alpha=0.8, marker='o', markersize=4, markevery=max(1, len(block_heights)//20))
        
        final_subsidy = cumulative_subsidy_eth[-1] if cumulative_subsidy_eth else 0
        print(f"  ✓ {mechanism}: 最终累计补贴 = {final_subsidy:.2f} ETH")
    
    # 设置标签
    ax.set_xlabel('Block Height', fontweight='bold')
    ax.set_ylabel('Cumulative Subsidy Tokens Issued (ETH)', fontweight='bold')
    ax.set_title('The Cumulative Tokens Issued', 
                 fontweight='bold', pad=20)
    
    # 设置对数坐标
    ax.set_yscale('log')
    
    # 网格和图例
    ax.grid(True, alpha=0.3, linestyle='--', which='both')
    ax.set_axisbelow(True)
    ax.legend(loc='upper left', framealpha=0.9)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "fig6_cumulative_subsidy.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {output_file}")
    
    plt.close()
    return True

def main():
    print("\n" + "="*60)
    print("Justitia 图表生成器 - 图6")
    print("="*60)
    
    success = plot_fig6()
    
    if success:
        print("\n✓ 图6生成成功！")
        return 0
    else:
        print("\n❌ 图6生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
