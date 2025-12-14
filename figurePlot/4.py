#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图4: 矿工利润CDF - R_EB方案下的公平性验证
Proposer's profit CDF with R_AB = E(f_B), ensuring proposer fairness
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

# 实验数据路径 - 只分析R_EB方案
EXPERIMENT_PATH = '../expTest_R_EB/result/supervisor_measureOutput'

def load_proposer_profit():
    """加载矿工利润数据（R_EB方案）"""
    data_path = Path(EXPERIMENT_PATH)
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING]  警告: 文件不存在 {tx_details_file}")
        return None
    
    try:
        # 读取交易详情
        df = pd.read_csv(tx_details_file)
        
        # 只统计已确认的交易
        confirmed_col = 'Tx finally commit timestamp'
        confirmed_df = df[df[confirmed_col].notna()].copy()
        
        if len(confirmed_df) == 0:
            print(f"[WARNING]  警告: 没有已确认的交易")
            return None
        
        # 计算矿工利润
        # 对于ITX: Profit = FeeToProposer
        # 对于CTX: Profit = FeeToProposer + SubsidyR (通过Shapley分配后的部分)
        
        # 确保字段存在
        fee_col = 'FeeToProposer (wei)'
        subsidy_col = 'SubsidyR (wei)'
        
        if fee_col not in confirmed_df.columns:
            print(f"[WARNING]  警告: 缺少{fee_col}字段")
            print(f"  可用列: {list(confirmed_df.columns)}")
            return None
        
        confirmed_df[fee_col] = confirmed_df[fee_col].fillna(0)
        
        # 对于CTX，添加补贴
        if subsidy_col in confirmed_df.columns:
            confirmed_df[subsidy_col] = confirmed_df[subsidy_col].fillna(0)
        else:
            confirmed_df[subsidy_col] = 0
        
        # 计算总利润（单位：wei）
        confirmed_df['TotalProfit'] = confirmed_df[fee_col].copy()
        
        # 对于CTX，利润 = Fee + Subsidy
        ctx_mask = confirmed_df['IsCrossShard'] == True
        confirmed_df.loc[ctx_mask, 'TotalProfit'] = (
            confirmed_df.loc[ctx_mask, fee_col] + 
            confirmed_df.loc[ctx_mask, subsidy_col]
        )
        
        # 转换为ETH
        confirmed_df['ProfitETH'] = confirmed_df['TotalProfit'] / 1e18
        
        # 分离CTX和ITX
        ctx_profit = confirmed_df[confirmed_df['IsCrossShard'] == True]['ProfitETH'].values
        itx_profit = confirmed_df[confirmed_df['IsCrossShard'] == False]['ProfitETH'].values
        
        # 过滤掉0值和异常值
        ctx_profit = ctx_profit[ctx_profit > 0]
        itx_profit = itx_profit[itx_profit > 0]
        
        print(f"[OK] R_EB方案数据加载成功:")
        print(f"  - CTX数量: {len(ctx_profit):,}")
        print(f"  - ITX数量: {len(itx_profit):,}")
        print(f"  - CTX平均利润: {np.mean(ctx_profit):.9f} ETH")
        print(f"  - ITX平均利润: {np.mean(itx_profit):.9f} ETH")
        print(f"  - CTX中位数利润: {np.median(ctx_profit):.9f} ETH")
        print(f"  - ITX中位数利润: {np.median(itx_profit):.9f} ETH")
        
        return {
            'ctx_profit': ctx_profit,
            'itx_profit': itx_profit
        }
        
    except Exception as e:
        print(f"[ERROR] 错误: 加载数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def plot_profit_cdf(profit_data):
    """绘制矿工利润CDF图（对数坐标）"""
    
    if profit_data is None:
        return False
    
    ctx_profit = profit_data['ctx_profit']
    itx_profit = profit_data['itx_profit']
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 绘制ITX利润CDF
    sorted_itx = np.sort(itx_profit)
    cdf_itx = np.arange(1, len(sorted_itx) + 1) / len(sorted_itx)
    ax.plot(sorted_itx, cdf_itx,
            label='ITX (Intra-shard)',
            color='#2ECC71',
            linewidth=3.0,
            alpha=0.9,
            linestyle='-')
    
    # 绘制CTX利润CDF
    sorted_ctx = np.sort(ctx_profit)
    cdf_ctx = np.arange(1, len(sorted_ctx) + 1) / len(sorted_ctx)
    ax.plot(sorted_ctx, cdf_ctx,
            label='CTX (Cross-shard) with R = E(f_B)',
            color='#E74C3C',
            linewidth=3.0,
            alpha=0.9,
            linestyle='--')
    
    # 设置对数坐标
    ax.set_xscale('log')
    
    # 设置坐标轴
    ax.set_xlabel('Proposer Profit per Transaction (ETH, log scale)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Distribution Function (CDF)', fontsize=14, fontweight='bold')
    ax.set_title('Proposer Fairness: CTX vs ITX Profit Distribution\nWith Subsidy R = E(f_B)', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置Y轴范围
    ax.set_ylim([0, 1.05])
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--', which='both')
    
    # 添加图例
    ax.legend(loc='lower right', framealpha=0.95, fontsize=12)
    
    # 添加文本说明
    textstr = f'CTX Mean: {np.mean(ctx_profit):.6e} ETH\n'
    textstr += f'ITX Mean: {np.mean(itx_profit):.6e} ETH\n'
    textstr += f'Ratio: {np.mean(ctx_profit)/np.mean(itx_profit):.3f}'
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/4_proposer_profit_fairness.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图4: 矿工利润公平性分析 (R_EB方案)")
    print("="*60)
    
    # 加载R_EB方案的利润数据
    print(f"\n正在加载 R_EB 方案数据...")
    profit_data = load_proposer_profit()
    
    if profit_data is None:
        print("\n[ERROR] 错误: 数据加载失败")
        return 1
    
    # 绘制利润CDF图
    success = plot_profit_cdf(profit_data)
    
    if success:
        print("\n" + "="*60)
        print("[OK] 矿工利润公平性图生成成功！")
        print("="*60)
        print("\n说明:")
        print("- 该图展示了在R=E(f_B)补贴方案下，CTX和ITX的矿工利润分布")
        print("- 如果两条曲线接近，说明补贴机制实现了矿工公平性")
        print("- CTX利润 = FeeToProposer + SubsidyR")
        print("- ITX利润 = FeeToProposer")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
