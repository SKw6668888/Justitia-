#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图8: 矿工利润公平性对比 - 5个方案对比
Proposer's profit CDF: Monoxide, R_EB, PID, Lagrangian, R_EA_EB
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
    'ITX_only': '#3498DB',      # 蓝色
    'Monoxide': '#F39C12',      # 橙色
    'R_EB': '#E74C3C',          # 红色
    'PID': '#9B59B6',           # 紫色
    'Lagrangian': '#27AE60',    # 绿色
    'R_EA_EB': '#8B4513'        # 棕色
}

MARKERS = {
    'ITX_only': 'd',
    'Monoxide': 's',
    'R_EB': 'o',
    'PID': '^',
    'Lagrangian': 's',
    'R_EA_EB': 'p'
}

# 实验数据路径配置
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian/result/supervisor_measureOutput',
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
        itx_profit = confirmed_df[confirmed_df['IsCrossShard'] == False]['ProfitGwei'].values
        
        ctx_profit = ctx_profit[ctx_profit > 0]
        itx_profit = itx_profit[itx_profit > 0]
        
        print(f"[OK] {method_name}:")
        print(f"  - CTX数量: {len(ctx_profit):,}")
        print(f"  - ITX数量: {len(itx_profit):,}")
        print(f"  - CTX平均利润: {np.mean(ctx_profit):.2f} Gwei")
        print(f"  - ITX平均利润: {np.mean(itx_profit):.2f} Gwei")
        
        return {
            'ctx_profit': ctx_profit,
            'itx_profit': itx_profit
        }
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def plot_profit_cdf_all_schemes(profit_data):
    """绘制所有方案的矿工利润CDF对比图"""
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 首先绘制ITX only基准线（使用R_EB的ITX数据）
    if 'R_EB' in profit_data and profit_data['R_EB'] is not None:
        itx_profit = profit_data['R_EB']['itx_profit']
        sorted_itx = np.sort(itx_profit)
        cdf_itx = np.arange(1, len(sorted_itx) + 1) / len(sorted_itx)
        
        ax.plot(sorted_itx, cdf_itx,
                label='ITX only',
                color=COLORS['ITX_only'],
                linewidth=3.0,
                alpha=0.9,
                linestyle='-')
        
        marker_step = max(1, len(sorted_itx) // 10)
        marker_indices = range(0, len(sorted_itx), marker_step)
        ax.plot(sorted_itx[marker_indices], cdf_itx[marker_indices],
                marker=MARKERS['ITX_only'],
                color=COLORS['ITX_only'],
                markersize=8,
                linestyle='None',
                markeredgewidth=1.5,
                markerfacecolor='none')
    
    # 绘制5个方案的CTX利润CDF
    methods_order = ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']
    
    for method in methods_order:
        if method not in profit_data or profit_data[method] is None:
            continue
        
        ctx_profit = profit_data[method]['ctx_profit']
        
        sorted_ctx = np.sort(ctx_profit)
        cdf_ctx = np.arange(1, len(sorted_ctx) + 1) / len(sorted_ctx)
        
        ax.plot(sorted_ctx, cdf_ctx,
                label=method,
                color=COLORS[method],
                linewidth=2.5,
                alpha=0.85,
                linestyle='-')
        
        marker_step = max(1, len(sorted_ctx) // 10)
        marker_indices = range(0, len(sorted_ctx), marker_step)
        ax.plot(sorted_ctx[marker_indices], cdf_ctx[marker_indices],
                marker=MARKERS[method],
                color=COLORS[method],
                markersize=8,
                linestyle='None',
                markeredgewidth=1.5,
                markerfacecolor='none')
        
        print(f"  - {method}: 中位数={np.median(ctx_profit):.2f} Gwei")
    
    ax.set_xlabel("Proposer's profit (Gwei)", fontsize=14, fontweight='bold')
    ax.set_ylabel('CDF', fontsize=14, fontweight='bold')
    ax.set_title("Proposer's Profit CDF: Monoxide, R_EB, PID, Lagrangian, R_EA_EB\nDemonstrating Fairness with R_AB = E(f_B)", 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 自动设置X轴范围（根据实际数据）
    all_profits = []
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        if method in profit_data and profit_data[method] is not None:
            all_profits.extend(profit_data[method]['ctx_profit'])
    if 'R_EB' in profit_data and profit_data['R_EB'] is not None:
        all_profits.extend(profit_data['R_EB']['itx_profit'])
    
    if len(all_profits) > 0:
        max_profit = np.percentile(all_profits, 99)  # 使用99分位数避免极端值
        ax.set_xlim([0, max_profit * 1.1])
    else:
        ax.set_xlim([0, 300000])  # 默认范围
    ax.set_ylim([0, 1.05])
    
    ax.grid(True, alpha=0.3, linestyle='--', which='both')
    ax.legend(loc='lower right', framealpha=0.95, fontsize=11)
    
    plt.tight_layout()
    
    output_file = Path('figures/8_proposer_profit_fairness_all.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图8: 矿工利润公平性对比（5个方案）")
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
    
    success = plot_profit_cdf_all_schemes(profit_data)
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] 矿工利润公平性对比图生成成功！")
        print("="*60)
        print("\n说明:")
        print("- 对比5个方案: Monoxide, R_EB, PID, Lagrangian, R_EA_EB")
        print("- ITX only: 仅ITX交易的利润分布（基准）")
        print("- R_EB: 与ITX曲线最接近，实现了矿工公平性")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
