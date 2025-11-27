#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Justitia 绘图程序 - 生成所有7张图表

使用方法:
1. 先运行数据分析器: python justitia_data_analyzer.py
2. 运行此脚本: python justitia_plot_all.py

输出: 在 figurePlot/figures/ 目录下生成所有图表
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from scipy.interpolate import make_interp_spline
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

# 设置seaborn样式
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.3)

# 颜色方案
COLORS = {
    'Monoxide': '#E74C3C',      # 红色
    'R=0': '#F39C12',           # 橙色
    'R=E(f_B)': '#27AE60',      # 绿色
    'R=E(f_A)+E(f_B)': '#3498DB',  # 蓝色
    'R=1 ETH/CTX': '#9B59B6'    # 紫色
}

class JustitiaPlotter:
    def __init__(self):
        self.data_dir = Path("data")
        self.output_dir = Path("figures")
        self.output_dir.mkdir(exist_ok=True)
        
    def load_json(self, filename):
        """加载JSON数据文件"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            print(f"⚠️  警告: 文件不存在 {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def plot_fig1_boxplot(self):
        """
        图1: CTX排队延迟箱线图
        """
        print("\n生成图1: CTX排队延迟箱线图...")
        
        data = self.load_json("fig1_queueing_latency_boxplot.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 准备数据
        mechanisms = list(data.keys())
        latencies = [data[m] for m in mechanisms]
        
        # 创建箱线图
        bp = ax.boxplot(latencies, 
                        labels=mechanisms,
                        patch_artist=True,
                        showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='red', markersize=6))
        
        # 设置颜色
        for patch, mechanism in zip(bp['boxes'], mechanisms):
            patch.set_facecolor(COLORS.get(mechanism, '#95A5A6'))
            patch.set_alpha(0.7)
        
        ax.set_xlabel('Subsidy Mechanism', fontsize=14, fontweight='bold')
        ax.set_ylabel('Queueing Latency (seconds)', fontsize=14, fontweight='bold')
        ax.set_title('Queueing Latency of CTXs under Various Subsidy Solutions', 
                     fontsize=16, fontweight='bold', pad=20)
        
        # 旋转x轴标签
        plt.xticks(rotation=15, ha='right')
        
        # 添加网格
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_file = self.output_dir / "fig1_ctx_latency_boxplot.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图1已保存: {output_file}")
    
    def plot_fig2_ratio_bar(self):
        """
        图2: CTX/ITX延迟比值柱状图
        """
        print("\n生成图2: CTX/ITX延迟比值柱状图...")
        
        data = self.load_json("fig2_latency_ratio_bar.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 准备数据 - 支持两种格式
        mechanisms = list(data.keys())
        if isinstance(data[mechanisms[0]], dict):
            ratios = [data[m]['ratio'] for m in mechanisms]
        else:
            ratios = [data[m] for m in mechanisms]
        
        # 创建柱状图
        bars = ax.bar(range(len(mechanisms)), ratios, 
                      color=[COLORS.get(m, '#95A5A6') for m in mechanisms],
                      alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # 添加数值标签
        for i, (bar, ratio) in enumerate(zip(bars, ratios)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{ratio:.2f}x',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # 添加参考线 (y=1.0 表示公平)
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2, 
                   label='Fair (CTX = ITX)', alpha=0.7)
        
        ax.set_xlabel('Subsidy Mechanism', fontsize=14, fontweight='bold')
        ax.set_ylabel('CTX / ITX Latency Ratio', fontsize=14, fontweight='bold')
        ax.set_title('Queueing Latency Declines as Subsidy R_AB Increases', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(range(len(mechanisms)))
        ax.set_xticklabels(mechanisms, rotation=15, ha='right')
        
        ax.legend(fontsize=11)
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_file = self.output_dir / "fig2_latency_ratio_bar.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图2已保存: {output_file}")
    
    def plot_fig3_kde(self):
        """
        图3: CTX排队延迟KDE分布
        """
        print("\n生成图3: CTX排队延迟KDE分布...")
        
        data = self.load_json("fig3_kde_distribution.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 为每种机制绘制KDE曲线
        for mechanism, latencies in data.items():
            if len(latencies) < 2:
                continue
            
            latencies = np.array(latencies)
            
            # 使用scipy的gaussian_kde
            try:
                kde = stats.gaussian_kde(latencies)
                x_range = np.linspace(0, 50, 500)
                density = kde(x_range)
                
                ax.plot(x_range, density, 
                       label=mechanism, 
                       color=COLORS.get(mechanism, '#95A5A6'),
                       linewidth=2.5, alpha=0.8)
            except:
                print(f"  ⚠️  无法为 {mechanism} 生成KDE")
        
        ax.set_xlabel('Queueing Latency (seconds)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Probability Density', fontsize=14, fontweight='bold')
        ax.set_title('The Queueing Latency Distribution of Confirmed CTXs\n(Kernel Density Estimation)', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlim(0, 50)
        ax.legend(fontsize=10, loc='upper right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_file = self.output_dir / "fig3_latency_kde.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图3已保存: {output_file}")
    
    def plot_fig4_cdf(self):
        """
        图4: CTX排队延迟CDF
        """
        print("\n生成图4: CTX排队延迟CDF...")
        
        data = self.load_json("fig4_cdf.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 为每种机制绘制CDF曲线
        for mechanism, latencies in data.items():
            if len(latencies) < 2:
                continue
            
            latencies = np.array(latencies)
            n = len(latencies)
            
            # 计算CDF
            cdf = np.arange(1, n + 1) / n
            
            ax.plot(latencies, cdf, 
                   label=mechanism, 
                   color=COLORS.get(mechanism, '#95A5A6'),
                   linewidth=2.5, alpha=0.8)
        
        ax.set_xlabel('Queueing Latency (seconds)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Cumulative Probability', fontsize=14, fontweight='bold')
        ax.set_title('CDF of the Queueing Latency of Confirmed CTXs', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlim(0, None)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=10, loc='lower right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_file = self.output_dir / "fig4_latency_cdf.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图4已保存: {output_file}")
    
    def plot_fig5_ctx_ratio(self):
        """
        图5: 区块中CTX占比
        """
        print("\n生成图5: 区块中CTX占比...")
        
        data = self.load_json("fig5_ctx_ratio.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 准备数据 - 支持两种格式，并转换为百分比
        mechanisms = list(data.keys())
        if isinstance(data[mechanisms[0]], dict):
            ratios = [data[m]['ratio'] for m in mechanisms]
        else:
            ratios = [data[m] * 100 for m in mechanisms]  # 转换为百分比
        
        # 创建柱状图
        bars = ax.bar(range(len(mechanisms)), ratios, 
                      color=[COLORS.get(m, '#95A5A6') for m in mechanisms],
                      alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # 添加数值标签
        for bar, ratio in zip(bars, ratios):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{ratio:.1f}%',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_xlabel('Subsidy Mechanism', fontsize=14, fontweight='bold')
        ax.set_ylabel('CTX Ratio in Packaged Blocks (%)', fontsize=14, fontweight='bold')
        ax.set_title('The Ratio of CTXs out of All TXs in Packaged Blocks', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(range(len(mechanisms)))
        ax.set_xticklabels(mechanisms, rotation=15, ha='right')
        ax.set_ylim(0, 100)
        
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        output_file = self.output_dir / "fig5_ctx_ratio.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图5已保存: {output_file}")
    
    def plot_fig6_cumulative_subsidy(self):
        """
        图6: 累计补贴发行量（对数坐标）
        """
        print("\n生成图6: 累计补贴发行量...")
        
        data = self.load_json("fig6_cumulative_subsidy.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 为每种机制绘制累计曲线
        for mechanism, values in data.items():
            if not values or 'epochs' not in values:
                continue
            
            epochs = values['epochs']
            cumulative = values['cumulative_subsidy_eth']
            
            # 过滤掉0值（对数坐标无法显示）
            non_zero_mask = np.array(cumulative) > 0
            if not any(non_zero_mask):
                continue
            
            epochs_nz = np.array(epochs)[non_zero_mask]
            cumulative_nz = np.array(cumulative)[non_zero_mask]
            
            ax.plot(epochs_nz, cumulative_nz, 
                   label=mechanism, 
                   color=COLORS.get(mechanism, '#95A5A6'),
                   linewidth=2.5, alpha=0.8, marker='o', markersize=3)
        
        ax.set_xlabel('Block Height (Epoch)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Cumulative Tokens Issued (ETH)', fontsize=14, fontweight='bold')
        ax.set_title('The Cumulative Tokens Issued', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_yscale('log')
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3, which='both')
        
        plt.tight_layout()
        output_file = self.output_dir / "fig6_cumulative_subsidy.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图6已保存: {output_file}")
    
    def plot_fig7_proposer_profit(self):
        """
        图7: 提议者利润分布CDF（对数坐标）- 所有机制
        """
        print("\n生成图7: 提议者利润分布CDF（所有机制）...")
        
        data = self.load_json("fig7_proposer_profit_cdf.json")
        if not data:
            return
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # 定义线型样式
        linestyles = {
            'Monoxide': '-',
            'R=0': '--',
            'R=E(f_B)': '-.',
            'R=E(f_A)+E(f_B)': ':',
            'R=1 ETH/CTX': '-'
        }
        
        # 为每种机制绘制利润CDF
        for mechanism, profits in data.items():
            if len(profits) < 2:
                continue
            
            profits = np.array(profits)
            profits = profits[profits > 0]  # 过滤0值
            n = len(profits)
            cdf = np.arange(1, n + 1) / n
            
            ax.plot(profits, cdf, 
                   label=mechanism, 
                   color=COLORS.get(mechanism, '#95A5A6'),
                   linewidth=2.5, 
                   alpha=0.85,
                   linestyle=linestyles.get(mechanism, '-'))
        
        ax.set_xlabel('Proposer Profit per CTX (ETH)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Cumulative Distribution Function', fontsize=14, fontweight='bold')
        ax.set_title('Proposer Profit Distribution under Various Subsidy Mechanisms', 
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xscale('log')
        ax.set_ylim(0, 1)
        ax.legend(fontsize=11, loc='lower right', framealpha=0.9)
        ax.grid(True, alpha=0.3, which='both')
        
        plt.tight_layout()
        output_file = self.output_dir / "fig7_proposer_profit_cdf.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 图7已保存: {output_file}")
    
    def plot_all(self):
        """生成所有图表"""
        print("\n" + "=" * 60)
        print("Justitia 绘图程序")
        print("=" * 60)
        
        self.plot_fig1_boxplot()
        self.plot_fig2_ratio_bar()
        self.plot_fig3_kde()
        self.plot_fig4_cdf()
        self.plot_fig5_ctx_ratio()
        self.plot_fig6_cumulative_subsidy()
        self.plot_fig7_proposer_profit()
        
        print("\n" + "=" * 60)
        print("✓ 所有图表生成完成！")
        print(f"✓ 图表保存在: {self.output_dir.absolute()}")
        print("=" * 60)


def main():
    plotter = JustitiaPlotter()
    plotter.plot_all()


if __name__ == "__main__":
    main()
