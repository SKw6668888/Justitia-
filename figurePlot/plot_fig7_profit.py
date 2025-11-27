#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图7: 提议者利润分布CDF（对数坐标）
CDF of proposer profit per transaction under R=E(f_B) (log scale)
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

def plot_fig7():
    """生成图7: 提议者利润分布CDF"""
    print("\n" + "="*60)
    print("图7: 提议者利润分布CDF（对数坐标）")
    print("="*60)
    
    # 读取数据
    data_file = Path("data/fig7_proposer_profit_cdf.json")
    if not data_file.exists():
        print(f"❌ 错误: 找不到数据文件 {data_file}")
        print("请先运行 justitia_data_analyzer.py 生成数据")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ 成功加载数据")
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 绘制CTX和ITX的CDF
    colors = {'CTX': '#E74C3C', 'ITX': '#3498DB'}
    
    for tx_type in ['CTX', 'ITX']:
        if tx_type not in data or len(data[tx_type]) == 0:
            print(f"  ⚠️  {tx_type}: 无数据")
            continue
        
        profits = data[tx_type]
        
        # 转换为ETH单位
        profits_eth = [p / 1e18 for p in profits if p > 0]  # 只保留正值用于对数坐标
        
        if len(profits_eth) == 0:
            print(f"  ⚠️  {tx_type}: 无正值数据")
            continue
        
        # 排序并计算CDF
        sorted_profits = np.sort(profits_eth)
        cdf = np.arange(1, len(sorted_profits) + 1) / len(sorted_profits)
        
        ax.plot(sorted_profits, cdf, label=tx_type, color=colors[tx_type], 
                linewidth=2.5, alpha=0.8)
        
        median = np.median(profits_eth)
        print(f"  ✓ {tx_type}: {len(profits_eth)} 个数据点, 中位数={median:.6f} ETH")
    
    # 设置标签
    ax.set_xlabel('Proposer Profit per Transaction (ETH)', fontweight='bold')
    ax.set_ylabel('Cumulative Probability', fontweight='bold')
    ax.set_title("Proposer's Profit with R_AB = E(f_B) (Ensuring Fairness)", 
                 fontweight='bold', pad=20)
    
    # 设置对数坐标
    ax.set_xscale('log')
    
    # 设置范围
    ax.set_ylim(0, 1)
    
    # 网格和图例
    ax.grid(True, alpha=0.3, linestyle='--', which='both')
    ax.set_axisbelow(True)
    ax.legend(loc='lower right', framealpha=0.9, fontsize=12)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "fig7_proposer_profit_cdf.png"
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {output_file}")
    
    plt.close()
    return True

def main():
    print("\n" + "="*60)
    print("Justitia 图表生成器 - 图7")
    print("="*60)
    
    success = plot_fig7()
    
    if success:
        print("\n✓ 图7生成成功！")
        return 0
    else:
        print("\n❌ 图7生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
