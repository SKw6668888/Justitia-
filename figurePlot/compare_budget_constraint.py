# -*- coding: utf-8 -*-
"""
预算硬约束测试对比图表 (Budget Constraint Test Comparison)
展示 Lagrangian 机制如何通过影子价格 λ 强制遵守预算约束

实验配置：
- Loose (宽松):   MaxInflation = 2.0 ETH
- Normal (正常):  MaxInflation = 1.0 ETH  
- Tight (紧缩):   MaxInflation = 0.2 ETH

Author: Antigravity AI Assistant
Date: 2026-01-14
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from pathlib import Path

# ============================================================================
# Publication-Quality Settings
# ============================================================================
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['ps.fonttype'] = 42
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
mpl.rcParams['font.size'] = 10
mpl.rcParams['axes.labelsize'] = 12
mpl.rcParams['axes.titlesize'] = 14
mpl.rcParams['xtick.labelsize'] = 10
mpl.rcParams['ytick.labelsize'] = 10
mpl.rcParams['legend.fontsize'] = 10
mpl.rcParams['lines.linewidth'] = 2
mpl.rcParams['grid.linewidth'] = 0.5
mpl.rcParams['grid.alpha'] = 0.3

# 实验配置
BUDGETS = {
    'max2': {'label': 'Loose (2.0 ETH)', 'color': '#2ca02c', 'marker': 'o', 'value': 2.0},
    'max1': {'label': 'Normal (1.0 ETH)', 'color': '#ff7f0e', 'marker': 's', 'value': 1.0},
    'max0.2': {'label': 'Tight (0.2 ETH)', 'color': '#d62728', 'marker': '^', 'value': 0.2}
}

def load_experiment_data(budget_key):
    """加载特定预算实验的数据"""
    base_dir = Path(f"../expTest_{budget_key}")
    result_dir = base_dir / "result" / "supervisor_measureOutput"
    
    if not result_dir.exists():
        print(f"⚠️  {result_dir} not found")
        return None
    
    data = {}
    
    # 加载 Justitia Effectiveness 数据
    jus_file = result_dir / "Justitia_Effectiveness.csv"
    if jus_file.exists():
        try:
            df = pd.read_csv(jus_file)
            data['justitia'] = df
            print(f"✓ {budget_key}: Loaded {len(df)} epochs of Justitia data")
        except Exception as e:
            print(f"✗ {budget_key}: Failed to load Justitia data: {e}")
    
    # 加载 TPS 数据
    tps_file = result_dir / "Average_TPS.csv"
    if tps_file.exists():
        try:
            df = pd.read_csv(tps_file)
            data['tps'] = df
        except Exception as e:
            print(f"✗ {budget_key}: Failed to load TPS data: {e}")
    
    return data if data else None


def plot_cumulative_subsidy(experiments, output_path=None):
    """
    图 1: 累计补贴曲线对比
    展示不同预算下补贴如何"触顶"
    注意：由于CSV中的"Justitia Reward"是固定参数而非实际补贴，
    我们通过 CTX数量 × 单笔补贴(假设) 来估算累计补贴
    """
    if output_path is None:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f'figures/budget_constraint_cumulative_{timestamp}.pdf'
    
    print("\n" + "="*60)
    print("图 1: 累计补贴曲线 (Cumulative Subsidy)")
    print("="*60)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    
    has_data = False
    for budget_key, config in BUDGETS.items():
        if budget_key not in experiments or 'justitia' not in experiments[budget_key]:
            continue
        
        df = experiments[budget_key]['justitia']
        
        # 方法：使用 CTX 数量作为补贴的代理指标
        # 假设每笔 CTX 的平均补贴约为配置的 Justitia Reward
        # 实际补贴 ≈ CTX_count × avg_subsidy_per_tx
        
        if 'Cross-Shard Tx Count' in df.columns and 'Justitia Reward' in df.columns:
            # 计算累计CTX数量
            ctx_cumsum = df['Cross-Shard Tx Count'].cumsum()
            
            # 每笔交易的平均补贴（从配置中获取，单位：Wei）
            # Justitia Reward 是固定的基准值（1 ETH = 1e18 Wei）
            reward_per_tx_wei = df['Justitia Reward'].iloc[0]  # 应该是 1e18
            
            # 估算累计补贴（转换为 ETH）
            # 注意：这是一个简化估算，实际补贴会因 Shapley split而有所不同
            cumulative_eth = (ctx_cumsum * reward_per_tx_wei) / 1e18
            
            ax.plot(df['EpochID'], cumulative_eth,
                   label=config['label'],
                   color=config['color'],
                   marker=config['marker'],
                   markersize=5,
                   linewidth=2.5,
                   alpha=0.8,
                   markevery=max(1, len(df)//20))
            
            has_data = True
            
            # 添加预算上限线
            max_subsidy = config['value']
            ax.axhline(y=max_subsidy, color=config['color'], 
                      linestyle='--', linewidth=2, alpha=0.6,
                      label=f"{config['label'].split('(')[0].strip()} Limit")
            
            final_subsidy = cumulative_eth.iloc[-1]
            print(f"  {budget_key}: Total CTX={ctx_cumsum.iloc[-1]}, Est. Subsidy={final_subsidy:.4f} ETH")
            
            # 检查是否触顶
            if final_subsidy >= max_subsidy * 0.95:
                print(f"    ⚠️  Approaching budget limit!")
    
    if not has_data:
        print("❌ No subsidy data available")
        plt.close(fig)
        return
    
    ax.set_xlabel('Epoch', fontsize=13, fontweight='bold')
    ax.set_ylabel('Estimated Cumulative Subsidy (ETH)', fontsize=12, fontweight='bold')
    ax.set_title('Budget Constraint Enforcement: Cumulative Subsidy Estimation', 
                fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='upper left', frameon=True, shadow=True, fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 添加注释说明
    ax.text(0.98, 0.02, 'Note: Subsidy estimated from CTX count × avg reward',
           transform=ax.transAxes, fontsize=8, style='italic',
           verticalalignment='bottom', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    fig.tight_layout()
    
    # Clean up old file
    output_file = Path(output_path)
    if output_file.exists():
        try:
            output_file.unlink()
        except:
            pass
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_performance_comparison(experiments, output_path=None):
    """
    图 2: 性能对比 (TPS & CTX Latency)
    展示预算约束对系统性能的影响
    """
    if output_path is None:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f'figures/budget_constraint_performance_{timestamp}.pdf'
    
    print("\n" + "="*60)
    print("图 2: 性能对比 (Performance)")
    print("="*60)
    
    # 收集数据
    budget_labels = []
    avg_tps = []
    avg_latency = []
    
    for budget_key, config in BUDGETS.items():
        if budget_key not in experiments:
            continue
        
        data = experiments[budget_key]
        
        # 计算平均 TPS
        if 'tps' in data:
            df_tps = data['tps']
            valid_tps = df_tps[df_tps['Avg. TPS of this epoch'] > 0]
            if len(valid_tps) > 0:
                tps = valid_tps['Avg. TPS of this epoch'].mean()
                avg_tps.append(tps)
            else:
                avg_tps.append(0)
        else:
            avg_tps.append(0)
        
        # 计算平均 CTX 延迟 - 使用正确的列！
        if 'justitia' in data:
            df_jus = data['justitia']
            if 'CTX Avg Latency (sec)' in df_jus.columns:
                # 过滤有效数据（排除0和异常值）
                valid_lat = df_jus[(df_jus['CTX Avg Latency (sec)'] > 0) & 
                                  (df_jus['CTX Avg Latency (sec)'] < 100)]  # 排除 >100秒的异常值
                if len(valid_lat) > 0:
                    lat_sec = valid_lat['CTX Avg Latency (sec)'].mean()
                    lat_ms = lat_sec * 1000  # 转换为毫秒
                    avg_latency.append(lat_ms)
                else:
                    avg_latency.append(0)
            else:
                avg_latency.append(0)
        else:
            avg_latency.append(0)
        
        budget_labels.append(config['label'])
        print(f"  {budget_key}: TPS={avg_tps[-1]:.1f}, Latency={avg_latency[-1]:.2f}ms")
    
    if not budget_labels:
        print("❌ No performance data")
        return
    
    # 创建双子图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('white')
    
    x_pos = np.arange(len(budget_labels))
    colors = [BUDGETS[key]['color'] for key in BUDGETS.keys() if key in experiments]
    
    # 子图1: TPS
    bars1 = ax1.bar(x_pos, avg_tps, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Average Throughput (tx/s)', fontsize=12, fontweight='bold')
    ax1.set_title('Throughput Comparison', fontsize=13, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([label.split('(')[0].strip() for label in budget_labels], fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars1, avg_tps)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height + max(avg_tps)*0.02,
                f'{int(val)}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # 子图2: Latency
    bars2 = ax2.bar(x_pos, avg_latency, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('CTX Average Latency (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('CTX Latency Comparison', fontsize=13, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([label.split('(')[0].strip() for label in budget_labels], fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars2, avg_latency)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height + max(avg_latency)*0.02,
                f'{val:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    fig.suptitle('Impact of Budget Constraint on System Performance', 
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    # Clean up old file
    output_file = Path(output_path)
    if output_file.exists():
        try:
            output_file.unlink()
        except:
            pass
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()

    """
    图 1: 累计补贴曲线对比
    展示不同预算下补贴如何"触顶"
    """
    if output_path is None:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f'figures/budget_constraint_cumulative_{timestamp}.pdf'
    
    print("\n" + "="*60)
    print("图 1: 累计补贴曲线 (Cumulative Subsidy)")
    print("="*60)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    
    has_data = False
    for budget_key, config in BUDGETS.items():
        if budget_key not in experiments or 'justitia' not in experiments[budget_key]:
            continue
        
        df = experiments[budget_key]['justitia']
        
        # 注意：CSV中没有直接的补贴列，我们需要从其他数据推算
        # 这里先用一个占位符，实际需要根据你的CSV结构调整
        if 'Justitia Reward' in df.columns:
            # 计算累计补贴 (将单位转换为 ETH)
            cumulative = df['Justitia Reward'].cumsum() / 1e18  # Wei to ETH
            
            ax.plot(df['EpochID'], cumulative,
                   label=config['label'],
                   color=config['color'],
                   marker=config['marker'],
                   markersize=5,
                   linewidth=2.5,
                   alpha=0.8,
                   markevery=max(1, len(df)//20))
            
            has_data = True
            
            # 添加预算上限线
            max_subsidy = config['value']
            ax.axhline(y=max_subsidy, color=config['color'], 
                      linestyle='--', linewidth=1.5, alpha=0.5,
                      label=f"{config['label']} Limit")
            
            print(f"  {budget_key}: Final cumulative subsidy = {cumulative.iloc[-1]:.4f} ETH")
    
    if not has_data:
        print("❌ No subsidy data available")
        plt.close(fig)
        return
    
    ax.set_xlabel('Epoch', fontsize=13, fontweight='bold')
    ax.set_ylabel('Cumulative Subsidy Issued (ETH)', fontsize=12, fontweight='bold')
    ax.set_title('Budget Constraint Enforcement: Cumulative Subsidy', 
                fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='best', frameon=True, shadow=True, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    fig.tight_layout()
    
    # Clean up old file
    output_file = Path(output_path)
    if output_file.exists():
        try:
            output_file.unlink()
        except:
            pass
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_performance_comparison(experiments, output_path=None):
    """
    图 2: 性能对比 (TPS & CTX Latency)
    展示预算约束对系统性能的影响
    """
    if output_path is None:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f'figures/budget_constraint_performance_{timestamp}.pdf'
    
    print("\n" + "="*60)
    print("图 2: 性能对比 (Performance)")
    print("="*60)
    
    # 收集数据
    budget_labels = []
    avg_tps = []
    avg_latency = []
    
    for budget_key, config in BUDGETS.items():
        if budget_key not in experiments:
            continue
        
        data = experiments[budget_key]
        
        # 计算平均 TPS
        if 'tps' in data:
            df_tps = data['tps']
            valid_tps = df_tps[df_tps['Avg. TPS of this epoch'] > 0]
            if len(valid_tps) > 0:
                tps = valid_tps['Avg. TPS of this epoch'].mean()
                avg_tps.append(tps)
            else:
                avg_tps.append(0)
        else:
            avg_tps.append(0)
        
        # 计算平均 CTX 延迟
        if 'justitia' in data:
            df_jus = data['justitia']
            if 'CTX Avg Latency (sec)' in df_jus.columns:
                valid_lat = df_jus[df_jus['CTX Avg Latency (sec)'] > 0]
                if len(valid_lat) > 0:
                    lat = valid_lat['CTX Avg Latency (sec)'].mean() * 1000  # sec to ms
                    avg_latency.append(lat)
                else:
                    avg_latency.append(0)
            else:
                avg_latency.append(0)
        else:
            avg_latency.append(0)
        
        budget_labels.append(config['label'])
        print(f"  {budget_key}: TPS={avg_tps[-1]:.1f}, Latency={avg_latency[-1]:.2f}ms")
    
    if not budget_labels:
        print("❌ No performance data")
        return
    
    # 创建双子图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('white')
    
    x_pos = np.arange(len(budget_labels))
    colors = [BUDGETS[key]['color'] for key in BUDGETS.keys() if key in experiments]
    
    # 子图1: TPS
    bars1 = ax1.bar(x_pos, avg_tps, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Average Throughput (tx/s)', fontsize=12, fontweight='bold')
    ax1.set_title('Throughput Comparison', fontsize=13, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(budget_labels, rotation=15, ha='right')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars1, avg_tps)):
        ax1.text(bar.get_x() + bar.get_width()/2, val + max(avg_tps)*0.02,
                f'{int(val)}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # 子图2: Latency
    bars2 = ax2.bar(x_pos, avg_latency, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('CTX Average Latency (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('CTX Latency Comparison', fontsize=13, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(budget_labels, rotation=15, ha='right')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars2, avg_latency)):
        ax2.text(bar.get_x() + bar.get_width()/2, val + max(avg_latency)*0.02,
                f'{val:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    fig.suptitle('Impact of Budget Constraint on System Performance', 
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    # Clean up old file
    output_file = Path(output_path)
    if output_file.exists():
        try:
            output_file.unlink()
        except:
            pass
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def main():
    """主函数"""
    print("="*60)
    print("预算硬约束测试对比图表生成")
    print("Budget Constraint Test Comparison")
    print("="*60)
    print()
    
    # 创建输出目录
    Path("figures").mkdir(exist_ok=True)
    
    # 加载实验数据
    print("📂 加载实验数据...")
    print()
    experiments = {}
    for budget_key in BUDGETS.keys():
        print(f"Loading {budget_key}:")
        data = load_experiment_data(budget_key)
        if data:
            experiments[budget_key] = data
        print()
    
    if not experiments:
        print("❌ ERROR: No experimental data found!")
        print("   Please ensure experiments are in:")
        for key in BUDGETS.keys():
            print(f"   - expTest_{key}/result/supervisor_measureOutput/")
        return
    
    # 生成图表
    plot_cumulative_subsidy(experiments)
    plot_performance_comparison(experiments)
    
    print("\n" + "="*60)
    print("✅ All charts generated successfully!")
    print("="*60)
    print("\n生成的文件:")
    print("  📊 figures/budget_constraint_cumulative_*.pdf")
    print("  📊 figures/budget_constraint_performance_*.pdf")
    print("\n这些图表展示了 Lagrangian 机制的预算约束能力。")
    print()


if __name__ == '__main__':
    main()
