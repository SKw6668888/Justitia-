#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图9: 矿工利润分布箱线图 - 展示离群值
Box Plot of Proposer's Profit - Demonstrating Outlier Reduction
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
        
        print(f"[OK] {method_name}:")
        print(f"  - CTX数量: {len(ctx_profit):,}")
        print(f"  - 中位数: {np.median(ctx_profit):.2f} Gwei")
        print(f"  - P95: {np.percentile(ctx_profit, 95):.2f} Gwei")
        print(f"  - P99: {np.percentile(ctx_profit, 99):.2f} Gwei")
        print(f"  - 最大值: {np.max(ctx_profit):.2f} Gwei")
        
        return ctx_profit
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def plot_boxplot_all_schemes(profit_data):
    """绘制所有方案的箱线图对比"""
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    methods_order = ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']
    
    # 准备数据
    data_to_plot = []
    labels = []
    colors_list = []
    
    for method in methods_order:
        if method in profit_data and profit_data[method] is not None:
            data_to_plot.append(profit_data[method])
            labels.append(method)
            colors_list.append(COLORS[method])
    
    if len(data_to_plot) == 0:
        print("[ERROR] 没有可绘制的数据")
        return False
    
    # 绘制箱线图
    bp = ax.boxplot(data_to_plot, 
                     labels=labels,
                     patch_artist=True,
                     showfliers=True,  # 显示离群点
                     flierprops=dict(marker='o', 
                                   markerfacecolor='red', 
                                   markersize=3, 
                                   alpha=0.3,
                                   markeredgecolor='none'),
                     medianprops=dict(color='black', linewidth=2.5),
                     whiskerprops=dict(linewidth=1.5),
                     capprops=dict(linewidth=1.5),
                     boxprops=dict(linewidth=1.5))
    
    # 为每个箱子设置颜色
    for patch, color in zip(bp['boxes'], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 添加统计信息标注
    for i, method in enumerate(labels, 1):
        data = profit_data[method]
        median = np.median(data)
        p95 = np.percentile(data, 95)
        p99 = np.percentile(data, 99)
        
        # 在箱体上方标注P99值
        ax.text(i, p99, f'P99={p99:.0f}', 
               ha='center', va='bottom', fontsize=9, 
               fontweight='bold', color='darkred')
    
    ax.set_xlabel('Incentive Mechanism', fontsize=14, fontweight='bold')
    ax.set_ylabel("Proposer's Profit (Gwei)", fontsize=14, fontweight='bold')
    ax.set_title("Box Plot: Proposer's Profit Distribution Across Schemes\nDemonstrating Outlier Reduction by Justitia-Lagrangian", 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置Y轴范围（避免极端离群点压缩主体）
    all_data = np.concatenate(data_to_plot)
    y_max = np.percentile(all_data, 99.5)  # 使用99.5分位数作为上限
    ax.set_ylim([0, y_max * 1.15])
    
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    output_file = Path('figures/9_proposer_profit_boxplot.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图9: 矿工利润分布箱线图（展示离群值）")
    print("="*60)
    
    profit_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在加载 {method} 数据...")
        data = load_proposer_profit(method)
        if data is not None:
            profit_data[method] = data
    
    if len(profit_data) == 0:
        print("\n[ERROR] 数据加载失败")
        return 1
    
    success = plot_boxplot_all_schemes(profit_data)
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] 箱线图生成成功！")
        print("="*60)
        print("\n说明:")
        print("- 箱体: 25%-75%分位数范围（IQR）")
        print("- 中线: 中位数")
        print("- 胡须: 1.5×IQR范围")
        print("- 红点: 离群值（Outliers）")
        print("- Lagrangian应显示更少、更低的离群点")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
