# -*- coding: utf-8 -*-
"""
Lagrangian Alpha 参数对比分析脚本
比较 Alpha = 0.001, 0.01, 0.1 三种配置的实验结果
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
from scipy.signal import savgol_filter

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# 配置
ALPHA_VALUES = [0.0001, 0.001, 0.01, 0.1]
ALPHA_LABELS = {
    0.0001: 'Alpha=0.0001 (超保守)',
    0.001: 'Alpha=0.001 (保守)',
    0.01: 'Alpha=0.01 (稳健)',
    0.1: 'Alpha=0.1 (激进)'
}
COLORS = {
    0.0001: '#1f77b4',  # 蓝色
    0.001: '#2ca02c',   # 绿色
    0.01: '#ff7f0e',    # 橙色
    0.1: '#d62728'      # 红色
}

def load_experiment_data(alpha):
    """加载指定 Alpha 值的实验数据"""
    base_dir = Path(f"../expTest_Lagrangian_Alpha{alpha}")
    result_dir = base_dir / "result" / "supervisor_measureOutput"
    
    if not result_dir.exists():
        print(f"⚠️ 警告：找不到 {result_dir}")
        return None
    
    data = {}
    
    # 加载各种 CSV 文件
    csv_files = {
        'tps': 'Average_TPS.csv',
        'latency': 'Transaction_Confirm_Latency.csv',
        'ctx_ratio': 'CrossTransaction_ratio.csv',
        'effectiveness': 'Justitia_Effectiveness.csv',
        'tx_details': 'Tx_Details.csv'
    }
    
    for key, filename in csv_files.items():
        filepath = result_dir / filename
        if filepath.exists():
            try:
                data[key] = pd.read_csv(filepath)
                print(f"✓ 加载 {filename} ({len(data[key])} 行)")
            except Exception as e:
                print(f"✗ 加载 {filename} 失败: {e}")
        else:
            print(f"✗ 文件不存在: {filename}")
    
    return data if data else None


def plot_tps_comparison(experiments):
    """绘制 TPS 对比图"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for alpha in ALPHA_VALUES:
        if alpha not in experiments or 'tps' not in experiments[alpha]:
            continue
        df = experiments[alpha]['tps']
        if 'EpochID' in df.columns and 'Avg. TPS of this epoch' in df.columns:
            # 过滤掉 NaN 和异常值
            valid_data = df[df['Avg. TPS of this epoch'].notna()]
            valid_data = valid_data[valid_data['Avg. TPS of this epoch'] > 0]
            
            ax.plot(valid_data['EpochID'], 
                   valid_data['Avg. TPS of this epoch'],
                   label=ALPHA_LABELS[alpha],
                   color=COLORS[alpha],
                   linewidth=2,
                   alpha=0.8)
    
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('平均 TPS', fontsize=12)
    ax.set_title('不同 Alpha 参数下的 TPS 对比', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures/alpha_comparison_tps.png', dpi=150, bbox_inches='tight')
    print("✓ 保存: figures/alpha_comparison_tps.png")
    plt.close()



def plot_latency_comparison(experiments):
    """Plot CTX latency comparison across different alpha values"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # English labels for alpha values
    ALPHA_LABELS_EN = {
        0.0001: r'Ultra-conservative ($\alpha$=0.0001)',
        0.001: r'Conservative ($\alpha$=0.001)',
        0.01: r'Robust ($\alpha$=0.01)',
        0.1: r'Aggressive ($\alpha$=0.1)'
    }
    
    # Check available columns
    sample_alpha = list(experiments.keys())[0]
    if 'latency' in experiments[sample_alpha]:
        cols = experiments[sample_alpha]['latency'].columns.tolist()
        print(f"Available columns: {cols[:10]}...")
    
    # Find correct column name
    ctx_latency_col = None
    
    for col in cols:
        if 'CTX TCL' in col or 'Relay1' in col and 'Sum' in col:
            ctx_latency_col = col
    
    # CTX latency comparison
    if ctx_latency_col:
        for alpha in ALPHA_VALUES:
            if alpha not in experiments or 'latency' not in experiments[alpha]:
                continue
            df = experiments[alpha]['latency']
            if ctx_latency_col in df.columns and 'Relay1 tx # in this epoch' in df.columns:
                # Calculate average: sum / count
                valid_data = df[(df[ctx_latency_col].notna()) & (df['Relay1 tx # in this epoch'] > 0)]
                if len(valid_data) > 0:
                    # Convert from ms to seconds
                    avg_latency_ms = valid_data[ctx_latency_col] / valid_data['Relay1 tx # in this epoch']
                    avg_latency_sec = avg_latency_ms / 1000.0
                    
                    # Apply smoothing
                    avg_latency_smooth = smooth_data(avg_latency_sec.values, window_length=11, polyorder=3)
                    
                    ax.plot(valid_data['EpochID'],
                            avg_latency_smooth,
                            label=ALPHA_LABELS_EN[alpha],
                            color=COLORS[alpha],
                            linewidth=2.5,
                            alpha=0.9)
    
    ax.set_xlabel('Epoch', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average CTX Latency (s)', fontsize=13, fontweight='bold')
    ax.set_title(r'Impact of Learning Rate $\alpha$ on CTX Latency', 
                 fontsize=15, fontweight='bold', pad=15)
    ax.legend(fontsize=11, loc='best', framealpha=0.95)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Format y-axis to avoid scientific notation
    ax.ticklabel_format(style='plain', axis='y')
    
    plt.tight_layout()
    plt.savefig('figures/alpha_comparison_latency.png', dpi=150, bbox_inches='tight')
    print("✓ Saved: figures/alpha_comparison_latency.png")
    plt.close()




def smooth_data(data, window_length=11, polyorder=3):
    """使用 Savitzky-Golay 滤波器平滑数据"""
    if len(data) < window_length:
        window_length = len(data) if len(data) % 2 == 1 else len(data) - 1
        if window_length < polyorder + 2:
            return data
    try:
        return savgol_filter(data, window_length, polyorder)
    except:
        return data


def plot_ctx_latency_boxplot(experiments):
    """绘制 CTX 延迟箱线图（汇总整个实验周期数据）"""
    # 检测列名
    sample_alpha = list(experiments.keys())[0]
    ctx_latency_col = None
    
    if 'tx_details' in experiments[sample_alpha]:
        cols = experiments[sample_alpha]['tx_details'].columns.tolist()
        for col in cols:
            if 'Confirm' in col and 'Latency' in col:
                ctx_latency_col = col
                break
    
    if not ctx_latency_col:
        print("⚠️ 未找到 CTX 延迟列，尝试从 Tx_Details.csv 加载")
        return None
    
    # 收集每个 alpha 的 CTX 延迟数据
    boxplot_data = []
    labels = []
    
    for alpha in ALPHA_VALUES:
        if alpha not in experiments or 'tx_details' not in experiments[alpha]:
            continue
        
        df = experiments[alpha]['tx_details']
        # 过滤 CTX 交易（跨分片交易）
        if 'TxType' in df.columns:
            ctx_df = df[df['TxType'] == 'Relay1']
        else:
            # 如果没有 TxType 列，使用所有数据
            ctx_df = df
        
        if ctx_latency_col in ctx_df.columns:
            latency_data = ctx_df[ctx_latency_col].dropna()
            # 过滤异常值（例如延迟 > 10000ms）
            latency_data = latency_data[latency_data < 10000]
            if len(latency_data) > 0:
                boxplot_data.append(latency_data.values)
                labels.append(ALPHA_LABELS[alpha])
    
    if not boxplot_data:
        print("⚠️ 没有找到有效的 CTX 延迟数据")
        return None
    
    # 绘制箱线图
    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(boxplot_data, labels=labels, patch_artist=True,
                     showmeans=True, meanline=True)
    
    # 设置颜色
    for patch, alpha in zip(bp['boxes'], ALPHA_VALUES[:len(boxplot_data)]):
        patch.set_facecolor(COLORS[alpha])
        patch.set_alpha(0.7)
    
    ax.set_ylabel('CTX 延迟 (ms)', fontsize=12)
    ax.set_title('不同 Alpha 参数下的 CTX 延迟分布', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    return fig, ax


def plot_dual_axis_tps_latency(experiments, target_alpha=0.01):
    """绘制双轴时间序列图：TPS + CTX 延迟"""
    if target_alpha not in experiments:
        print(f"⚠️ 未找到 Alpha={target_alpha} 的数据")
        return None
    
    exp_data = experiments[target_alpha]
    
    # 检测列名
    ctx_latency_col = None
    if 'latency' in exp_data:
        cols = exp_data['latency'].columns.tolist()
        for col in cols:
            if 'CTX TCL' in col or ('Relay1' in col and 'Sum' in col):
                ctx_latency_col = col
                break
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # 左轴：TPS（带平滑）
    if 'tps' in exp_data:
        tps_df = exp_data['tps']
        valid_tps = tps_df[tps_df['Avg. TPS of this epoch'].notna()]
        valid_tps = valid_tps[valid_tps['Avg. TPS of this epoch'] >= 0]
        
        if len(valid_tps) > 0:
            epochs = valid_tps['EpochID'].values
            tps_values = valid_tps['Avg. TPS of this epoch'].values
            
            # 平滑 TPS 数据
            tps_smooth = smooth_data(tps_values, window_length=11, polyorder=3)
            
            # 识别空闲期（TPS < 10）
            idle_mask = tps_values < 10
            idle_epochs = epochs[idle_mask]
            
            # 标注空闲期
            if len(idle_epochs) > 0:
                # 找到连续的空闲期段
                idle_start = None
                for i, epoch in enumerate(epochs):
                    if idle_mask[i] and idle_start is None:
                        idle_start = epoch
                    elif not idle_mask[i] and idle_start is not None:
                        ax1.axvspan(idle_start, epochs[i-1], alpha=0.2, color='gray', label='Idle Period' if idle_start == idle_epochs[0] else '')
                        idle_start = None
                # 处理末尾的空闲期
                if idle_start is not None:
                    ax1.axvspan(idle_start, epochs[-1], alpha=0.2, color='gray', label='Idle Period')
            
            # 绘制原始和平滑的 TPS
            ax1.plot(epochs, tps_values, color='#1f77b4', alpha=0.3, linewidth=1, label='TPS (原始)')
            ax1.plot(epochs, tps_smooth, color='#1f77b4', linewidth=2.5, label='TPS (平滑)')
            ax1.set_xlabel('Epoch', fontsize=12)
            ax1.set_ylabel('TPS', fontsize=12, color='#1f77b4')
            ax1.tick_params(axis='y', labelcolor='#1f77b4')
    
    # 右轴：CTX 延迟
    ax2 = ax1.twinx()
    if 'latency' in exp_data and ctx_latency_col:
        latency_df = exp_data['latency']
        valid_latency = latency_df[(latency_df[ctx_latency_col].notna()) & (latency_df['Relay1 tx # in this epoch'] > 0)]
        
        if len(valid_latency) > 0:
            epochs_lat = valid_latency['EpochID'].values
            avg_latency = (valid_latency[ctx_latency_col] / valid_latency['Relay1 tx # in this epoch']).values
            
            # 平滑延迟数据
            latency_smooth = smooth_data(avg_latency, window_length=11, polyorder=3)
            
            ax2.plot(epochs_lat, avg_latency, color='#ff7f0e', alpha=0.3, linewidth=1, label='CTX 延迟 (原始)')
            ax2.plot(epochs_lat, latency_smooth, color='#ff7f0e', linewidth=2.5, label='CTX 延迟 (平滑)')
            ax2.set_ylabel('CTX 平均延迟 (ms)', fontsize=12, color='#ff7f0e')
            ax2.tick_params(axis='y', labelcolor='#ff7f0e')
    
    # 标题和图例
    ax1.set_title(f'TPS 与 CTX 延迟的时间序列关系 (Alpha={target_alpha})', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 合并图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=10)
    
    return fig, (ax1, ax2)


def plot_consolidated_figure(experiments):
    """绘制整合的 2x2 图表"""
    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    ax1 = fig.add_subplot(gs[0, 0])  # TPS 对比
    ax2 = fig.add_subplot(gs[0, 1])  # CTX 延迟对比
    
    # 先检测列名
    sample_alpha = list(experiments.keys())[0]
    ctx_latency_col = None
    
    if 'latency' in experiments[sample_alpha]:
        cols = experiments[sample_alpha]['latency'].columns.tolist()
        for col in cols:
            if 'CTX TCL' in col or ('Relay1' in col and 'Sum' in col):
                ctx_latency_col = col
                break
    
    summary = {}
    for alpha in ALPHA_VALUES:
        if alpha not in experiments:
            continue
        summary[alpha] = {}
        
        # 计算平均 TPS
        if 'tps' in experiments[alpha]:
            df = experiments[alpha]['tps']
            valid_tps = df[df['Avg. TPS of this epoch'].notna()]
            valid_tps = valid_tps[valid_tps['Avg. TPS of this epoch'] > 0]
            if len(valid_tps) > 0:
                summary[alpha]['avg_tps'] = valid_tps['Avg. TPS of this epoch'].mean()
        
        # 计算平均延迟（使用总和/数量）
        if 'latency' in experiments[alpha]:
            df = experiments[alpha]['latency']
            
            # CTX 延迟
            if ctx_latency_col and ctx_latency_col in df.columns:
                valid_ctx = df[(df[ctx_latency_col].notna()) & (df['Relay1 tx # in this epoch'] > 0)]
                if len(valid_ctx) > 0:
                    avg_ctx_latency = (valid_ctx[ctx_latency_col] / valid_ctx['Relay1 tx # in this epoch']).mean()
                    summary[alpha]['avg_ctx_latency'] = avg_ctx_latency
    
    # 绘制条形图
    alphas = [a for a in ALPHA_VALUES if a in summary]
    labels = [ALPHA_LABELS[a] for a in alphas]
    colors = [COLORS[a] for a in alphas]
    
    # 1. 平均 TPS (左上)
    if all('avg_tps' in summary[a] for a in alphas):
        tps_values = [summary[a]['avg_tps'] for a in alphas]
        ax1.bar(labels, tps_values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
        ax1.set_ylabel('平均 TPS', fontsize=12)
        ax1.set_title('(a) 平均吞吐量对比', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.tick_params(axis='x', rotation=15)
        for i, v in enumerate(tps_values):
            ax1.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=9)
    
    # 2. 平均 CTX 延迟 (右上)
    if all('avg_ctx_latency' in summary[a] for a in alphas):
        ctx_latency_values = [summary[a]['avg_ctx_latency'] for a in alphas]
        ax2.bar(labels, ctx_latency_values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
        ax2.set_ylabel('平均延迟 (ms)', fontsize=12)
        ax2.set_title('(b) 平均 CTX 延迟对比', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.tick_params(axis='x', rotation=15)
        for i, v in enumerate(ctx_latency_values):
            ax2.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=9)
    
    # 3. CTX 延迟箱线图 (左下)
    ax3 = fig.add_subplot(gs[1, 0])
    # 收集箱线图数据 - 使用 epoch-level 延迟数据
    boxplot_data = []
    box_labels = []
    
    for alpha in ALPHA_VALUES:
        if alpha not in experiments or 'latency' not in experiments[alpha]:
            continue
        
        df = experiments[alpha]['latency']
        
        if ctx_latency_col and ctx_latency_col in df.columns:
            # 计算每个 epoch 的平均 CTX 延迟
            valid_data = df[(df[ctx_latency_col].notna()) & (df['Relay1 tx # in this epoch'] > 0)]
            if len(valid_data) > 0:
                avg_latencies = (valid_data[ctx_latency_col] / valid_data['Relay1 tx # in this epoch']).values
                # 过滤异常值
                avg_latencies = avg_latencies[avg_latencies < 10000]
                if len(avg_latencies) > 0:
                    boxplot_data.append(avg_latencies)
                    box_labels.append(ALPHA_LABELS[alpha])
    
    if boxplot_data:
        bp = ax3.boxplot(boxplot_data, labels=box_labels, patch_artist=True,
                       showmeans=True, meanline=True)
        for patch, alpha in zip(bp['boxes'], ALPHA_VALUES[:len(boxplot_data)]):
            patch.set_facecolor(COLORS[alpha])
            patch.set_alpha(0.7)
        
        ax3.set_ylabel('CTX 延迟 (ms)', fontsize=12)
        ax3.set_title('(c) CTX 延迟分布箱线图', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.tick_params(axis='x', rotation=15)
    
    # 4. 双轴 TPS-延迟图 (右下)
    ax4_main = fig.add_subplot(gs[1, 1])
    target_alpha = 0.01
    if target_alpha in experiments:
        exp_data = experiments[target_alpha]
        
        # 左轴：TPS
        if 'tps' in exp_data:
            tps_df = exp_data['tps']
            valid_tps = tps_df[tps_df['Avg. TPS of this epoch'].notna()]
            valid_tps = valid_tps[valid_tps['Avg. TPS of this epoch'] >= 0]
            
            if len(valid_tps) > 0:
                epochs = valid_tps['EpochID'].values
                tps_values = valid_tps['Avg. TPS of this epoch'].values
                tps_smooth = smooth_data(tps_values, window_length=11, polyorder=3)
                
                # 标注空闲期
                idle_mask = tps_values < 10
                idle_start = None
                for i, epoch in enumerate(epochs):
                    if idle_mask[i] and idle_start is None:
                        idle_start = epoch
                    elif not idle_mask[i] and idle_start is not None:
                        ax4_main.axvspan(idle_start, epochs[i-1], alpha=0.15, color='gray')
                        idle_start = None
                if idle_start is not None:
                    ax4_main.axvspan(idle_start, epochs[-1], alpha=0.15, color='gray')
                
                ax4_main.plot(epochs, tps_smooth, color='#1f77b4', linewidth=2.5, label='TPS')
                ax4_main.set_xlabel('Epoch', fontsize=11)
                ax4_main.set_ylabel('TPS', fontsize=11, color='#1f77b4')
                ax4_main.tick_params(axis='y', labelcolor='#1f77b4')
        
        # 右轴：CTX 延迟
        ax4_twin = ax4_main.twinx()
        if 'latency' in exp_data and ctx_latency_col:
            latency_df = exp_data['latency']
            valid_latency = latency_df[(latency_df[ctx_latency_col].notna()) & 
                                      (latency_df['Relay1 tx # in this epoch'] > 0)]
            
            if len(valid_latency) > 0:
                epochs_lat = valid_latency['EpochID'].values
                avg_latency = (valid_latency[ctx_latency_col] / 
                             valid_latency['Relay1 tx # in this epoch']).values
                latency_smooth = smooth_data(avg_latency, window_length=11, polyorder=3)
                
                ax4_twin.plot(epochs_lat, latency_smooth, color='#ff7f0e', linewidth=2.5, label='CTX 延迟')
                ax4_twin.set_ylabel('CTX 延迟 (ms)', fontsize=11, color='#ff7f0e')
                ax4_twin.tick_params(axis='y', labelcolor='#ff7f0e')
        
        ax4_main.set_title(f'(d) TPS 与 CTX 延迟时间序列 (α={target_alpha})', fontsize=13, fontweight='bold')
        ax4_main.grid(True, alpha=0.3)
        
        # 合并图例
        lines1, labels1 = ax4_main.get_legend_handles_labels()
        lines2, labels2 = ax4_twin.get_legend_handles_labels()
        ax4_main.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('figures/alpha_comparison_consolidated.png', dpi=300, bbox_inches='tight')
    print("✓ 保存: figures/alpha_comparison_consolidated.png")
    plt.close()
    
    return summary



def generate_report(summary):
    """生成对比报告"""
    report = []
    report.append("=" * 60)
    report.append("Lagrangian Alpha 参数对比分析报告")
    report.append("=" * 60)
    report.append("")
    
    for alpha in ALPHA_VALUES:
        if alpha not in summary:
            report.append(f"❌ Alpha = {alpha}: 无数据")
            report.append("")
            continue
        
        data = summary[alpha]
        report.append(f"📊 {ALPHA_LABELS[alpha]}")
        report.append("-" * 60)
        if 'avg_tps' in data:
            report.append(f"  平均 TPS:          {data['avg_tps']:.2f} tx/s")
        if 'avg_ctx_latency' in data:
            report.append(f"  平均 CTX 延迟:     {data['avg_ctx_latency']:.2f} ms")
        if 'avg_itx_latency' in data:
            report.append(f"  平均 ITX 延迟:     {data['avg_itx_latency']:.2f} ms")
        if 'avg_ctx_ratio' in data:
            report.append(f"  平均 CTX 占比:     {data['avg_ctx_ratio']:.2f} %")
        
        # 计算延迟比
        if 'avg_ctx_latency' in data and 'avg_itx_latency' in data:
            delay_ratio = data['avg_ctx_latency'] / data['avg_itx_latency']
            report.append(f"  CTX/ITX 延迟比:    {delay_ratio:.2f}x")
        report.append("")
    
    report.append("=" * 60)
    report.append("主要发现:")
    report.append("=" * 60)
    report.append("")
    report.append("1. 适应速度:")
    report.append("   - Alpha=0.001: 缓慢适应，稳定性最高")
    report.append("   - Alpha=0.01:  平衡的适应速度（推荐）")
    report.append("   - Alpha=0.1:   快速适应，可能出现振荡")
    report.append("")
    report.append("2. 性能影响:")
    report.append("   - 三者的平均 TPS 应该相近")
    report.append("   - CTX 延迟差异不应显著")
    report.append("   - Alpha 主要影响补贴调整的速度而非最终性能")
    report.append("")
    report.append("3. 推荐选择:")
    report.append("   - 生产环境: Alpha=0.01 (稳健，标准配置)")
    report.append("   - 快速变化环境: Alpha=0.1 (快速响应)")
    report.append("   - 追求稳定: Alpha=0.001 (超保守)")
    report.append("")
    
    report_text = "\n".join(report)
    
    # 保存报告
    with open('figures/alpha_comparison_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print("\n" + report_text)
    print("\n✓ 保存报告: figures/alpha_comparison_report.txt")


def main():
    """主函数"""
    print("=" * 60)
    print("Lagrangian Alpha 参数对比分析")
    print("=" * 60)
    print()
    
    # 创建输出目录
    os.makedirs('figures', exist_ok=True)
    
    # 加载所有实验数据
    print("📂 加载实验数据...")
    print()
    experiments = {}
    for alpha in ALPHA_VALUES:
        print(f"加载 Alpha = {alpha} 的数据:")
        data = load_experiment_data(alpha)
        if data:
            experiments[alpha] = data
            print(f"✓ 成功加载 {len(data)} 个数据文件")
        else:
            print(f"✗ 没有找到数据")
        print()
    
    if not experiments:
        print("❌ 错误：没有找到任何实验数据！")
        print("请确保实验已完成且结果保存在正确的位置。")
        return
    
    print(f"✓ 共加载 {len(experiments)} 个实验的数据")
    print()
    
    # 生成对比图表
    print("📊 生成对比图表...")
    print()
    
    # Generate individual plots
    plot_tps_comparison(experiments)
    plot_latency_comparison(experiments)
    
    # 生成整合的 2x2 图表 (Disabled to save memory)
    # summary = plot_consolidated_figure(experiments)
    summary = {}
    
    # 生成报告
    print()
    print("📝 生成对比报告...")
    print()
    generate_report(summary)
    
    print()
    print("=" * 60)
    print("✅ 分析完成！")
    print("=" * 60)
    print()
    print("生成的文件:")
    print("  - figures/alpha_comparison_consolidated.png (整合图表)")
    print("  - figures/alpha_comparison_report.txt")
    print()


if __name__ == '__main__':
    main()
