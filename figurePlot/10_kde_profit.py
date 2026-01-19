#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图10: 矿工利润概率密度函数 - 展示长尾形态
KDE/PDF Plot of Proposer's Profit - Demonstrating Long-tail Reduction
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path
from scipy.stats import gaussian_kde
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

LINE_STYLES = {
    'Monoxide': '--',
    'R_EB': '-.',
    'PID': ':',
    'Lagrangian': '-',      # 实线突出Lagrangian
    'R_EA_EB': '--'
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
        
        print(f"[OK] {method_name}: {len(ctx_profit):,} CTX")
        
        return ctx_profit
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def plot_kde_all_schemes(profit_data):
    """绘制所有方案的KDE概率密度图"""
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    methods_order = ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']
    
    # 确定X轴范围（使用所有数据的99.5分位数）
    all_data = []
    for method in methods_order:
        if method in profit_data and profit_data[method] is not None:
            all_data.extend(profit_data[method])
    
    if len(all_data) == 0:
        print("[ERROR] 没有可绘制的数据")
        return False
    
    x_max = np.percentile(all_data, 99.5)
    x_range = np.linspace(0, x_max, 1000)
    
    # 绘制每个方案的KDE曲线
    for method in methods_order:
        if method not in profit_data or profit_data[method] is None:
            continue
        
        data = profit_data[method]
        
        # 使用高斯核密度估计
        kde = gaussian_kde(data, bw_method='scott')
        density = kde(x_range)
        
        # 绘制KDE曲线
        linewidth = 3.5 if method == 'Lagrangian' else 2.5
        alpha = 0.9 if method == 'Lagrangian' else 0.7
        
        ax.plot(x_range, density,
               label=method,
               color=COLORS[method],
               linestyle=LINE_STYLES[method],
               linewidth=linewidth,
               alpha=alpha)
        
        # 填充曲线下面积（仅Lagrangian）
        if method == 'Lagrangian':
            ax.fill_between(x_range, density, alpha=0.2, color=COLORS[method])
        
        # 计算并标注峰值位置
        peak_idx = np.argmax(density)
        peak_x = x_range[peak_idx]
        peak_y = density[peak_idx]
        
        print(f"  - {method}: 峰值位置={peak_x:.1f} Gwei, 峰值密度={peak_y:.6f}")
    
    ax.set_xlabel("Proposer's Profit (Gwei)", fontsize=14, fontweight='bold')
    ax.set_ylabel('Probability Density', fontsize=14, fontweight='bold')
    ax.set_title("Probability Density (KDE): Proposer's Profit Distribution\nDemonstrating Long-tail Reduction by Justitia-Lagrangian", 
                 fontsize=16, fontweight='bold', pad=20)
    
    ax.set_xlim([0, x_max])
    ax.set_ylim(bottom=0)
    
    ax.grid(True, alpha=0.3, linestyle='--', axis='both')
    ax.set_axisbelow(True)
    ax.legend(loc='upper right', framealpha=0.95, fontsize=12)
    
    # 添加说明文本
    textstr = 'Desirable: Sharp peak + Short tail\n(Lagrangian should show this pattern)'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
           verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    
    output_file = Path('figures/10_proposer_profit_kde.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图10: 矿工利润概率密度函数（展示长尾形态）")
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
    
    print("\n正在计算KDE...")
    success = plot_kde_all_schemes(profit_data)
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] KDE图生成成功！")
        print("="*60)
        print("\n说明:")
        print("- 高峰 + 短尾 = 理想分布（Lagrangian目标）")
        print("- 低峰 + 长尾 = 不公平分布（其他方案）")
        print("- Lagrangian曲线应呈现'胖头短尾'特征")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
