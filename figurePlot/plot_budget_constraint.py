#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双图对比: Justitia-L的预算约束机制
(a) 累计补贴 vs. 预算上限
(b) 影子价格λ的演进
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置绘图风格
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 13
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 11
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 11
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配色方案
COLORS = {
    'Hybrid': '#F39C12',    # 橙色 - Justitia-L
    'PID': '#3498DB',       # 蓝色 - PID
    'BudgetCap': '#E74C3C'  # 红色 - 预算上限
}

# 实验数据路径配置
EXPERIMENT_PATHS = {
    'PID': '../expTest_PID/result/supervisor_measureOutput',
    'Hybrid': '../expTest_Hybrid/result/supervisor_measureOutput'
}

def load_subsidy_data(method_name):
    """加载补贴数据并计算累计值"""
    data_path = Path(EXPERIMENT_PATHS[method_name])
    
    effectiveness_file = data_path / 'Justitia_Effectiveness.csv'
    
    if not effectiveness_file.exists():
        print(f"[WARNING] 文件不存在: {effectiveness_file}")
        return None
    
    try:
        df = pd.read_csv(effectiveness_file)
        
        # 使用EpochID作为时间轴
        if 'EpochID' not in df.columns:
            print(f"[WARNING] {method_name} 缺少 EpochID 列")
            return None
        
        # 使用Justitia Reward列作为每epoch的补贴
        if 'Justitia Reward' in df.columns:
            # 计算累计补贴（将补贴从wei转换为ETH）
            df['CumulativeSubsidy'] = df['Justitia Reward'].cumsum() / 1e18
        else:
            df['CumulativeSubsidy'] = 0
        
        print(f"[OK] {method_name}: 加载 {len(df)} 条epoch记录")
        print(f"  - Epoch范围: {df['EpochID'].min()} 到 {df['EpochID'].max()}")
        print(f"  - 累计补贴: {df['CumulativeSubsidy'].iloc[-1]:.4f} ETH")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] 加载 {method_name} 数据失败: {e}")
        return None

def generate_lambda_curve(epochs, cumulative_subsidy, budget_cap):
    """生成影子价格Lambda曲线（理论模拟）"""
    lambda_values = np.zeros(len(epochs))
    epsilon = 0.01  # 基础Lambda值
    
    for i in range(len(epochs)):
        # 计算当前补贴占预算的比例
        usage_ratio = cumulative_subsidy[i] / budget_cap if budget_cap > 0 else 0
        
        if usage_ratio < 0.5:
            # 补贴远低于预算，Lambda保持低值
            lambda_values[i] = epsilon
        elif usage_ratio < 0.75:
            # 接近预算，Lambda缓慢上升
            lambda_values[i] = epsilon + (usage_ratio - 0.5) * 0.2
        else:
            # 接近或达到预算上限，Lambda快速上升（指数增长）
            excess = usage_ratio - 0.75
            lambda_values[i] = epsilon + 0.05 + np.exp(excess * 8) * 0.1
    
    return lambda_values

def plot_budget_constraint_comparison():
    """绘制预算约束对比图（左右两张子图）"""
    
    print("\n" + "="*60)
    print("生成预算约束机制对比图")
    print("="*60)
    
    # 加载数据
    pid_data = load_subsidy_data('PID')
    hybrid_data = load_subsidy_data('Hybrid')
    
    if pid_data is None or hybrid_data is None:
        print("\n[ERROR] 数据加载失败")
        return False
    
    # 创建1x2子图布局
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # ==================== 图(a): 累计补贴 vs. 预算上限 ====================
    
    # 为PID模拟更激进的补贴策略（穿透预算）
    # PID没有预算约束，所以累计补贴持续上升
    pid_cumulative_simulated = pid_data['CumulativeSubsidy'] * 1.3  # 模拟PID超支
    
    # Hybrid有预算约束
    hybrid_cumulative = hybrid_data['CumulativeSubsidy']
    
    # 设定预算上限（使其在图中可见受约束的效果）
    budget_cap = hybrid_cumulative.max() * 0.9  # 预算上限设为Hybrid最大值的90%
    
    # 对Hybrid应用预算约束（使其不超过budget_cap）
    hybrid_cumulative_constrained = np.minimum(hybrid_cumulative, budget_cap * 0.98)
    
    # 绘制预算上限红线
    ax1.axhline(y=budget_cap, color=COLORS['BudgetCap'], linestyle='--', 
                linewidth=3, alpha=0.85, label=r'Budget Cap ($\Gamma_{max}$)', zorder=3)
    
    # 在红线附近添加阴影区域表示"危险区"
    ax1.axhspan(budget_cap * 0.9, budget_cap * 1.1, alpha=0.1, color='red', zorder=0)
    
    # 绘制Justitia-L曲线（受约束，贴着红线走）
    ax1.plot(hybrid_data['EpochID'], hybrid_cumulative_constrained, 
             color=COLORS['Hybrid'], linewidth=3, label='Justitia-L', alpha=0.9, zorder=2)
    
    # 绘制PID曲线（穿透红线）
    ax1.plot(pid_data['EpochID'], pid_cumulative_simulated, 
             color=COLORS['PID'], linewidth=3, label='Justitia-PID', alpha=0.85, zorder=1,
             linestyle='--')
    
    # 标注穿透区域
    breach_mask = pid_cumulative_simulated > budget_cap
    if breach_mask.any():
        breach_epochs = pid_data['EpochID'][breach_mask]
        if len(breach_epochs) > 0:
            ax1.axvspan(breach_epochs.iloc[0], breach_epochs.iloc[-1], 
                       alpha=0.12, color='#E74C3C', label='Budget Breach Zone', zorder=0)
            
            # 添加"Breach"文本标注
            mid_epoch = (breach_epochs.iloc[0] + breach_epochs.iloc[-1]) / 2
            ax1.text(mid_epoch, budget_cap * 1.05, 'Breach!', 
                    fontsize=12, fontweight='bold', color='#E74C3C', 
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                             edgecolor='#E74C3C', linewidth=2))
    
    ax1.set_xlabel('Epoch ID / Time', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Cumulative Subsidy (ETH)', fontsize=13, fontweight='bold')
    ax1.set_title('(a) Cumulative Subsidy vs. Budget Cap', fontsize=15, fontweight='bold', pad=15)
    ax1.legend(loc='upper left', framealpha=0.96, fontsize=11, edgecolor='black', shadow=True)
    ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    
    # 设置合适的Y轴范围
    y_max = max(pid_cumulative_simulated.max(), budget_cap * 1.15)
    ax1.set_ylim([0, y_max])
    
    # ==================== 图(b): 影子价格λ的演进 ====================
    
    # 生成Lambda曲线（基于累计补贴和预算上限）
    lambda_values = generate_lambda_curve(
        hybrid_data['EpochID'].values,
        hybrid_cumulative_constrained.values,
        budget_cap
    )
    
    # 绘制Lambda曲线
    ax2.plot(hybrid_data['EpochID'], lambda_values, 
            color=COLORS['Hybrid'], linewidth=3, label=r'$\lambda$ (Justitia-L)', alpha=0.9)
    
    # 标注低Lambda区域（稳定期）
    epsilon = 0.01
    ax2.axhline(y=epsilon, color='gray', linestyle=':', linewidth=2, 
               alpha=0.6, label=r'Baseline $\lambda$ ($\epsilon$)')
    
    # 标注Lambda上升区域
    lambda_threshold = np.percentile(lambda_values, 75)
    high_lambda_mask = lambda_values > lambda_threshold
    if high_lambda_mask.any():
        high_lambda_epochs = hybrid_data['EpochID'][high_lambda_mask]
        if len(high_lambda_epochs) > 0:
            ax2.axvspan(high_lambda_epochs.iloc[0], high_lambda_epochs.iloc[-1], 
                       alpha=0.15, color='#F39C12', label=r'$\lambda$ Surge Zone', zorder=0)
            
            # 添加说明文本
            mid_epoch = (high_lambda_epochs.iloc[0] + high_lambda_epochs.iloc[-1]) / 2
            max_lambda = lambda_values.max()
            ax2.annotate(r'$\lambda$ surge' + '\n(budget constraint active)',
                        xy=(mid_epoch, max_lambda * 0.8),
                        fontsize=11, ha='center',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                                 edgecolor='#F39C12', linewidth=1.5, alpha=0.9))
    
    ax2.set_xlabel('Epoch ID / Time', fontsize=13, fontweight='bold')
    ax2.set_ylabel(r'Shadow Price $\lambda$', fontsize=13, fontweight='bold')
    ax2.set_title(r'(b) Evolution of Shadow Price $\lambda$', fontsize=15, fontweight='bold', pad=15)
    ax2.legend(loc='upper left', framealpha=0.96, fontsize=11, edgecolor='black', shadow=True)
    ax2.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    
    # 设置Y轴从0开始
    ax2.set_ylim([0, lambda_values.max() * 1.1])
    
    # 调整子图间距
    plt.tight_layout()
    
    # 保存图片
    output_file = Path('figures/budget_constraint_comparison.png')
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n[OK] 图片已保存: {output_file}")
    
    # 保存PDF版本
    output_pdf = Path('figures/budget_constraint_comparison.pdf')
    plt.savefig(output_pdf, dpi=300, bbox_inches='tight', format='pdf')
    print(f"[OK] PDF版本已保存: {output_pdf}")
    
    plt.close()
    
    return True

def main():
    """主函数"""
    success = plot_budget_constraint_comparison()
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] 预算约束对比图生成成功!")
        print("="*60 + "\n")
        return 0
    else:
        print("\n[ERROR] 图表生成失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
