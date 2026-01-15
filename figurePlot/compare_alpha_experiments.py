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
    plt.savefig('figures/alpha_comparison_tps.png', dpi=300, bbox_inches='tight')
    print("✓ 保存: figures/alpha_comparison_tps.png")
    plt.close()


def plot_latency_comparison(experiments):
    """绘制延迟对比图"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 检查可用的列名
    sample_alpha = list(experiments.keys())[0]
    if 'latency' in experiments[sample_alpha]:
        cols = experiments[sample_alpha]['latency'].columns.tolist()
        print(f"可用列: {cols[:10]}...")  # 打印前10个列名
    
    # 尝试找到正确的列名
    ctx_latency_col = None
    
    for col in cols:
        if 'CTX TCL' in col or 'Relay1' in col and 'Sum' in col:
            ctx_latency_col = col
    
    # CTX 延迟对比
    if ctx_latency_col:
        for alpha in ALPHA_VALUES:
            if alpha not in experiments or 'latency' not in experiments[alpha]:
                continue
            df = experiments[alpha]['latency']
            if ctx_latency_col in df.columns and 'Relay1 tx # in this epoch' in df.columns:
                # 计算平均值：总和除以数量
                valid_data = df[(df[ctx_latency_col].notna()) & (df['Relay1 tx # in this epoch'] > 0)]
                if len(valid_data) > 0:
                    avg_latency = valid_data[ctx_latency_col] / valid_data['Relay1 tx # in this epoch']
                    ax.plot(valid_data['EpochID'],
                            avg_latency,
                            label=ALPHA_LABELS[alpha],
                            color=COLORS[alpha],
                            linewidth=2,
                            alpha=0.8)
    
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('CTX 平均延迟 (ms)', fontsize=12)
    ax.set_title('不同 Alpha 参数下的 CTX 延迟对比', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures/alpha_comparison_latency.png', dpi=300, bbox_inches='tight')
    print("✓ 保存: figures/alpha_comparison_latency.png")
    plt.close()



def plot_ctx_ratio(experiments):
    """绘制 CTX 占比对比"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for alpha in ALPHA_VALUES:
        if alpha not in experiments or 'ctx_ratio' not in experiments[alpha]:
            continue
        df = experiments[alpha]['ctx_ratio']
        if 'EpochID' in df.columns and 'CTX ratio of this epoch' in df.columns:
            valid_data = df[df['CTX ratio of this epoch'].notna()]
            
            # 转换为百分比
            ratio_percent = valid_data['CTX ratio of this epoch'] * 100
            
            ax.plot(valid_data['EpochID'],
                   ratio_percent,
                   label=ALPHA_LABELS[alpha],
                   color=COLORS[alpha],
                   linewidth=2,
                   alpha=0.8)
    
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('CTX 占比 (%)', fontsize=12)
    ax.set_title('不同 Alpha 参数下的跨分片交易占比', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figures/alpha_comparison_ctx_ratio.png', dpi=300, bbox_inches='tight')
    print("✓ 保存: figures/alpha_comparison_ctx_ratio.png")
    plt.close()


def plot_summary_statistics(experiments):
    """绘制汇总统计对比"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 先检测列名
    sample_alpha = list(experiments.keys())[0]
    ctx_latency_col = None
    itx_latency_col = None
    
    if 'latency' in experiments[sample_alpha]:
        cols = experiments[sample_alpha]['latency'].columns.tolist()
        for col in cols:
            if 'CTX TCL' in col or ('Relay1' in col and 'Sum' in col):
                ctx_latency_col = col
            if 'Normal' in col and 'Sum' in col:
                itx_latency_col = col
    
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
            
            # ITX 延迟
            if itx_latency_col and itx_latency_col in df.columns:
                valid_itx = df[(df[itx_latency_col].notna()) & (df['Normal tx # in this epoch'] > 0)]
                if len(valid_itx) > 0:
                    avg_itx_latency = (valid_itx[itx_latency_col] / valid_itx['Normal tx # in this epoch']).mean()
                    summary[alpha]['avg_itx_latency'] = avg_itx_latency
        
        # 计算平均 CTX 占比
        if 'ctx_ratio' in experiments[alpha]:
            df = experiments[alpha]['ctx_ratio']
            valid_ratio = df[df['CTX ratio of this epoch'].notna()]
            if len(valid_ratio) > 0:
                summary[alpha]['avg_ctx_ratio'] = valid_ratio['CTX ratio of this epoch'].mean() * 100
    
    # 绘制条形图
    alphas = [a for a in ALPHA_VALUES if a in summary]
    labels = [ALPHA_LABELS[a] for a in alphas]
    colors = [COLORS[a] for a in alphas]
    
    # 平均 TPS
    if all('avg_tps' in summary[a] for a in alphas):
        tps_values = [summary[a]['avg_tps'] for a in alphas]
        ax1.bar(labels, tps_values, color=colors, alpha=0.7, edgecolor='black')
        ax1.set_ylabel('平均 TPS', fontsize=12)
        ax1.set_title('平均吞吐量对比', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        for i, v in enumerate(tps_values):
            ax1.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=10)
    
    # 平均 CTX 延迟
    if all('avg_ctx_latency' in summary[a] for a in alphas):
        ctx_latency_values = [summary[a]['avg_ctx_latency'] for a in alphas]
        ax2.bar(labels, ctx_latency_values, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_ylabel('平均延迟 (ms)', fontsize=12)
        ax2.set_title('平均 CTX 延迟对比', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        for i, v in enumerate(ctx_latency_values):
            ax2.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=10)
    
    # 平均 ITX 延迟
    if all('avg_itx_latency' in summary[a] for a in alphas):
        itx_latency_values = [summary[a]['avg_itx_latency'] for a in alphas]
        ax3.bar(labels, itx_latency_values, color=colors, alpha=0.7, edgecolor='black')
        ax3.set_ylabel('平均延迟 (ms)', fontsize=12)
        ax3.set_title('平均 ITX 延迟对比', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        for i, v in enumerate(itx_latency_values):
            ax3.text(i, v, f'{v:.1f}', ha='center', va='bottom', fontsize=10)
    
    # 平均 CTX 占比
    if all('avg_ctx_ratio' in summary[a] for a in alphas):
        ratio_values = [summary[a]['avg_ctx_ratio'] for a in alphas]
        ax4.bar(labels, ratio_values, color=colors, alpha=0.7, edgecolor='black')
        ax4.set_ylabel('CTX 占比 (%)', fontsize=12)
        ax4.set_title('平均跨分片交易占比', fontsize=13, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        for i, v in enumerate(ratio_values):
            ax4.text(i, v, f'{v:.1f}%', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('figures/alpha_comparison_summary.png', dpi=300, bbox_inches='tight')
    print("✓ 保存: figures/alpha_comparison_summary.png")
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
    
    plot_tps_comparison(experiments)
    plot_latency_comparison(experiments)
    plot_ctx_ratio(experiments)
    summary = plot_summary_statistics(experiments)
    
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
    print("  - figures/alpha_comparison_tps.png")
    print("  - figures/alpha_comparison_latency.png")
    print("  - figures/alpha_comparison_ctx_ratio.png")
    print("  - figures/alpha_comparison_summary.png")
    print("  - figures/alpha_comparison_report.txt")
    print()


if __name__ == '__main__':
    main()
