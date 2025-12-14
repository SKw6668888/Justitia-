#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图3: 累计补贴代币发行量
The cumulative tokens issued (subsidy)
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
    'Monoxide': '#27AE60',      # 绿色 (基准)
    'R_EB': '#9B59B6',          # 紫色 (R=E(f_B))
    'PID': '#3498DB',           # 蓝色
    'Lagrangian': '#E74C3C',    # 红色
    'R_EA_EB': '#F39C12'        # 橙色 (R=E(f_A)+E(f_B))
}

# 实验数据路径配置（5个方案）
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian/result/supervisor_measureOutput',
    'R_EA_EB': '../expTest_R_EA_EB/result/supervisor_measureOutput'
}

def load_cumulative_subsidy(method_name):
    """加载累计补贴数据"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING]  警告: 文件不存在 {tx_details_file}")
        return None
    
    try:
        # 读取交易详情
        df = pd.read_csv(tx_details_file)
        
        # 只统计已确认的CTX（有补贴）
        confirmed_col = 'Tx finally commit timestamp'
        confirmed_ctx = df[(df[confirmed_col].notna()) & (df['IsCrossShard'] == True)].copy()
        
        if len(confirmed_ctx) == 0:
            print(f"[WARNING]  警告: {method_name} 没有已确认的CTX")
            return None
        
        # 按确认时间排序
        confirmed_ctx = confirmed_ctx.sort_values(confirmed_col)
        
        # 获取补贴数据（SubsidyR (wei)字段）
        subsidy_col = 'SubsidyR (wei)'
        if subsidy_col not in confirmed_ctx.columns:
            print(f"[WARNING]  警告: {method_name} 缺少{subsidy_col}字段")
            print(f"  可用列: {list(confirmed_ctx.columns)}")
            return None
        
        # 填充缺失值为0
        confirmed_ctx[subsidy_col] = confirmed_ctx[subsidy_col].fillna(0)
        
        # 转换为ETH（1 ETH = 10^18 wei）
        confirmed_ctx['SubsidyETH'] = confirmed_ctx[subsidy_col] / 1e18
        
        # 计算累计补贴
        confirmed_ctx['CumulativeSubsidy'] = confirmed_ctx['SubsidyETH'].cumsum()
        
        # 获取区块高度（如果有的话）
        if 'BlockNumber' in confirmed_ctx.columns:
            block_numbers = confirmed_ctx['BlockNumber'].values
        else:
            # 如果没有区块高度，使用交易索引作为替代
            block_numbers = np.arange(len(confirmed_ctx))
        
        cumulative_subsidy = confirmed_ctx['CumulativeSubsidy'].values
        
        total_subsidy = cumulative_subsidy[-1] if len(cumulative_subsidy) > 0 else 0
        
        print(f"[OK] {method_name}:")
        print(f"  - CTX数量: {len(confirmed_ctx):,}")
        print(f"  - 总补贴: {total_subsidy:.6f} ETH")
        print(f"  - 平均补贴/CTX: {total_subsidy/len(confirmed_ctx):.9f} ETH")
        
        return {
            'block_numbers': block_numbers,
            'cumulative_subsidy': cumulative_subsidy,
            'total_subsidy': total_subsidy
        }
        
    except Exception as e:
        print(f"[ERROR] 错误: 加载 {method_name} 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def plot_cumulative_subsidy(subsidy_data):
    """绘制累计补贴发行量图（对数坐标）"""
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 为每个方案绘制累计补贴曲线
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        if method not in subsidy_data or subsidy_data[method] is None:
            continue
        
        data = subsidy_data[method]
        block_numbers = data['block_numbers']
        cumulative = data['cumulative_subsidy']
        
        # Monoxide没有补贴，跳过
        if method == 'Monoxide' or data['total_subsidy'] < 1e-10:
            print(f"  跳过 {method} (无补贴)")
            continue
        
        # 为了对数坐标，将0值替换为一个很小的数
        cumulative_log = np.where(cumulative > 0, cumulative, 1e-10)
        
        # 绘制曲线
        ax.plot(block_numbers, cumulative_log,
                label=method,
                color=COLORS[method],
                linewidth=2.5,
                alpha=0.85)
    
    # 设置对数坐标
    ax.set_yscale('log')
    
    # 设置坐标轴
    ax.set_xlabel('Block Height', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Subsidy Issued (ETH, log scale)', fontsize=14, fontweight='bold')
    ax.set_title('Cumulative Tokens Issued Over Time\nAcross Different Subsidy Schemes', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置Y轴范围（10^-6 到 10^4）
    ax.set_ylim([1e-6, 1e4])
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--', which='both')
    
    # 添加图例
    ax.legend(loc='lower right', framealpha=0.95, fontsize=11)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/3_cumulative_subsidy.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图3: 累计补贴发行量生成器")
    print("="*60)
    
    # 加载所有方案的补贴数据
    subsidy_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在加载 {method} 数据...")
        data = load_cumulative_subsidy(method)
        if data is not None:
            subsidy_data[method] = data
    
    # 检查是否有足够的数据
    if len(subsidy_data) == 0:
        print("\n[ERROR] 错误: 没有可用的数据")
        return 1
    
    # 绘制累计补贴图
    success = plot_cumulative_subsidy(subsidy_data)
    
    if success:
        print("\n" + "="*60)
        print("[OK] 累计补贴图生成成功！")
        print("="*60)
        return 0
    else:
        print("\n[ERROR] 累计补贴图生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
