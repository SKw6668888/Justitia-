#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图11: P95/P99尾部延迟柱状图 - 直观数值对比
Bar Chart of P95/P99 Tail Latency - Quantifying Improvement
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

# 配色方案 (与8.py保持一致)
COLORS = {
    'Monoxide': '#F39C12',      # 橙色
    'R_EB': '#E74C3C',          # 红色
    'PID': '#9B59B6',           # 紫色
    'Lagrangian': '#27AE60',    # 绿色
    'R_EA_EB': '#8B4513'        # 棕色
}

# 实验数据路径配置
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian_Alpha0.01/result/supervisor_measureOutput',
    'R_EA_EB': '../expTest_R_EA_EB/result/supervisor_measureOutput'
}

def load_proposer_profit(method_name):
    """加载矿工利润数据"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING] 文件不存在: {tx_details_file}")
        return None
    
    try:
        df = pd.read_csv(tx_details_file)
        confirmed_col = 'Tx finally commit timestamp'
        confirmed_df = df[df[confirmed_col].notna()].copy()
        
        if len(confirmed_df) == 0:
            print(f"[WARNING] {method_name} 没有已确认的交易")
            return None
        
        fee_col = 'FeeToProposer (wei)'
        subsidy_col = 'SubsidyR (wei)'
        
        if fee_col not in confirmed_df.columns:
            print(f"[WARNING] {method_name} 缺少{fee_col}字段")
            return None
        
        confirmed_df[fee_col] = confirmed_df[fee_col].fillna(0)
        
        if subsidy_col in confirmed_df.columns:
            confirmed_df[subsidy_col] = confirmed_df[subsidy_col].fillna(0)
        else:
            confirmed_df[subsidy_col] = 0
        
        confirmed_df['TotalProfit'] = confirmed_df[fee_col].copy()
        
        ctx_mask = confirmed_df['IsCrossShard'] == True
        confirmed_df.loc[ctx_mask, 'TotalProfit'] = (
            confirmed_df.loc[ctx_mask, fee_col] + 
            confirmed_df.loc[ctx_mask, subsidy_col]
        )
        
        # 转换为Gwei
        confirmed_df['ProfitGwei'] = confirmed_df['TotalProfit'] / 1e9
        
        ctx_profit = confirmed_df[confirmed_df['IsCrossShard'] == True]['ProfitGwei'].values
        
        ctx_profit = ctx_profit[ctx_profit > 0]
        
        if len(ctx_profit) == 0:
            return None
        
        # 计算关键统计量
        stats = {
            'median': np.median(ctx_profit),
            'p95': np.percentile(ctx_profit, 95),
            'p99': np.percentile(ctx_profit, 99),
            'p99_9': np.percentile(ctx_profit, 99.9),
            'max': np.max(ctx_profit),
            'count': len(ctx_profit)
        }
        
        print(f"[OK] {method_name}:")
        print(f"  - CTX数量: {stats['count']:,}")
        print(f"  - 中位数: {stats['median']:.2f} Gwei")
        print(f"  - P95: {stats['p95']:.2f} Gwei")
        print(f"  - P99: {stats['p99']:.2f} Gwei")
        print(f"  - P99.9: {stats['p99_9']:.2f} Gwei")
        
        return stats
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def plot_tail_latency_bar(profit_stats):
    """绘制P95/P99尾部延迟柱状图"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    methods_order = ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']
    
    # 准备数据
    methods_labels = []
    p95_values = []
    p99_values = []
    colors_list = []
    
    for method in methods_order:
        if method in profit_stats and profit_stats[method] is not None:
            methods_labels.append(method)
            p95_values.append(profit_stats[method]['p95'])
            p99_values.append(profit_stats[method]['p99'])
            colors_list.append(COLORS[method])
    
    if len(methods_labels) == 0:
        print("[ERROR] 没有可绘制的数据")
        return False
    
    x_pos = np.arange(len(methods_labels))
    bar_width = 0.6
    
    # 绘制P95柱状图
    bars1 = ax1.bar(x_pos, p95_values, bar_width, 
                    color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 在柱顶标注具体数值
    for i, (bar, val) in enumerate(zip(bars1, p95_values)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax1.set_xlabel('Incentive Mechanism', fontsize=14, fontweight='bold')
    ax1.set_ylabel("P95 Proposer's Profit (Gwei)", fontsize=14, fontweight='bold')
    ax1.set_title('P95 Tail Latency Comparison', fontsize=16, fontweight='bold', pad=15)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(methods_labels, rotation=15, ha='right')
    ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax1.set_axisbelow(True)
    
    # 绘制P99柱状图
    bars2 = ax2.bar(x_pos, p99_values, bar_width,
                    color=colors_list, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # 在柱顶标注具体数值
    for i, (bar, val) in enumerate(zip(bars2, p99_values)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax2.set_xlabel('Incentive Mechanism', fontsize=14, fontweight='bold')
    ax2.set_ylabel("P99 Proposer's Profit (Gwei)", fontsize=14, fontweight='bold')
    ax2.set_title('P99 Tail Latency Comparison', fontsize=16, fontweight='bold', pad=15)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(methods_labels, rotation=15, ha='right')
    ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax2.set_axisbelow(True)
    
    # 计算改进百分比（相对于Monoxide基准）
    if 'Monoxide' in profit_stats and 'Lagrangian' in profit_stats:
        base_p95 = profit_stats['Monoxide']['p95']
        base_p99 = profit_stats['Monoxide']['p99']
        lag_p95 = profit_stats['Lagrangian']['p95']
        lag_p99 = profit_stats['Lagrangian']['p99']
        
        improvement_p95 = (base_p95 - lag_p95) / base_p95 * 100
        improvement_p99 = (base_p99 - lag_p99) / base_p99 * 100
        
        # 添加改进说明
        textstr = f'Lagrangian Improvement:\nP95: {improvement_p95:.1f}% reduction\nP99: {improvement_p99:.1f}% reduction'
        props = dict(boxstyle='round', facecolor='lightgreen', alpha=0.7)
        fig.text(0.5, 0.02, textstr, transform=fig.transFigure, fontsize=12,
                verticalalignment='bottom', horizontalalignment='center',
                bbox=props, fontweight='bold')
    
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    
    output_file = Path('figures/11_tail_latency_p95_p99.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图11: P95/P99尾部延迟柱状图（直观数值对比）")
    print("="*60)
    
    profit_stats = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在加载 {method} 数据...")
        stats = load_proposer_profit(method)
        if stats is not None:
            profit_stats[method] = stats
    
    if len(profit_stats) == 0:
        print("\n[ERROR] 数据加载失败")
        return 1
    
    success = plot_tail_latency_bar(profit_stats)
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] P95/P99柱状图生成成功！")
        print("="*60)
        print("\n说明:")
        print("- P95: 95%的交易利润低于此值")
        print("- P99: 99%的交易利润低于此值")
        print("- 越低越好（表示利润分布更集中、更公平）")
        print("- Lagrangian应显示显著更低的P95/P99值")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
