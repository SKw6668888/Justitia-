#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图1: CTX排队延迟的累积分布函数 (CDF)
Cumulative Distribution Function (CDF) of the queueing latency of confirmed CTXs
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
# 注意：这些路径是相对于figurePlot目录的
EXPERIMENT_PATHS = {
    'Monoxide': '../expTest_monoxide/result/supervisor_measureOutput',
    'R_EB': '../expTest_R_EB/result/supervisor_measureOutput',
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Lagrangian': '../expTest_Lagrangian/result/supervisor_measureOutput',
    'R_EA_EB': '../expTest_R_EA_EB/result/supervisor_measureOutput'
}

def load_ctx_latency(method_name):
    """加载CTX的排队延迟数据"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    tx_details_file = data_path / 'Tx_Details.csv'
    
    if not tx_details_file.exists():
        print(f"[WARNING] 文件不存在: {tx_details_file}")
        return None
    
    try:
        # 读取交易详情
        df = pd.read_csv(tx_details_file)
        
        # 筛选CTX (IsCrossShard == True)
        ctx_df = df[df['IsCrossShard'] == True].copy()
        
        if len(ctx_df) == 0:
            print(f"[WARNING] {method_name} 没有CTX数据")
            return None
        
        # 计算排队延迟（秒）
        # QueueingLatency = 确认时间 - 提交时间
        time_col = 'Tx propose timestamp'
        confirmed_col = 'Tx finally commit timestamp'
        
        if time_col in ctx_df.columns and confirmed_col in ctx_df.columns:
            ctx_df['QueueingLatency'] = (ctx_df[confirmed_col] - ctx_df[time_col]) / 1000.0  # 转换为秒
        else:
            print(f"[WARNING] {method_name} 缺少时间字段")
            print(f"  可用列: {list(ctx_df.columns)}")
            return None
        
        # 过滤异常值（负延迟或过大延迟）
        ctx_df = ctx_df[(ctx_df['QueueingLatency'] >= 0) & (ctx_df['QueueingLatency'] < 1000)]
        
        latency = ctx_df['QueueingLatency'].values
        
        print(f"[OK] {method_name}: 加载 {len(latency)} 条CTX延迟数据")
        print(f"  - 平均延迟: {np.mean(latency):.2f}s")
        print(f"  - 中位数延迟: {np.median(latency):.2f}s")
        print(f"  - 最大延迟: {np.max(latency):.2f}s")
        
        return latency
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def plot_ctx_latency_cdf(latency_data):
    """绘制CTX排队延迟的CDF图"""
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 为每个方案绘制CDF
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        if method not in latency_data or latency_data[method] is None:
            continue
        
        latency = latency_data[method]
        
        # 排序数据
        sorted_latency = np.sort(latency)
        
        # 计算CDF
        cdf = np.arange(1, len(sorted_latency) + 1) / len(sorted_latency)
        
        # 绘制CDF曲线
        ax.plot(sorted_latency, cdf, 
                label=method, 
                color=COLORS[method],
                linewidth=2.5,
                alpha=0.85)
    
    # 设置坐标轴
    ax.set_xlabel('CTX Queueing Latency (seconds)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Cumulative Probability (CDF)', fontsize=14, fontweight='bold')
    ax.set_title('CDF of CTX Queueing Latency\nAcross Different Subsidy Schemes', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # 设置网格
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 设置Y轴范围
    ax.set_ylim([0, 1.05])
    
    # 添加图例
    ax.legend(loc='lower right', framealpha=0.95, fontsize=11)
    
    # 紧凑布局
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/1_ctx_latency_cdf.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("图1: CTX排队延迟CDF生成器")
    print("="*60)
    
    # 加载所有方案的延迟数据
    latency_data = {}
    
    for method in ['Monoxide', 'R_EB', 'PID', 'Lagrangian', 'R_EA_EB']:
        print(f"\n正在加载 {method} 数据...")
        latency = load_ctx_latency(method)
        if latency is not None:
            latency_data[method] = latency
    
    # 检查是否有足够的数据
    if len(latency_data) == 0:
        print("\n[ERROR] 没有可用的数据")
        return 1
    
    # 绘制CDF图
    success = plot_ctx_latency_cdf(latency_data)
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] CTX延迟CDF图生成成功!")
        print("="*60)
        return 0
    else:
        print("\n[ERROR] CDF图生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
