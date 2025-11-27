#!/usr/bin/env python3
"""
诊断时延比例问题的脚本
分析Justitia机制下CTX和ITX的时延差异原因
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_data():
    """加载实验数据"""
    base_path = Path('../expTest/result/supervisor_measureOutput')
    
    # 加载交易详情
    tx_details_path = base_path / 'Tx_Details.csv'
    if not tx_details_path.exists():
        print(f"❌ 错误: 找不到文件 {tx_details_path}")
        return None, None
    
    df = pd.read_csv(tx_details_path)
    
    # 加载费用数据（如果存在）
    ctx_fee_path = base_path / 'CTX_Fee_Latency.csv'
    fee_df = None
    if ctx_fee_path.exists():
        fee_df = pd.read_csv(ctx_fee_path)
    
    return df, fee_df

def classify_transactions(df):
    """分类交易类型"""
    # 跨片交易 (Cross-Shard Transactions)
    cross_shard_mask = (df['Relay1 Tx commit timestamp (not a relay tx -> nil)'].notna()) | \
                      (df['Relay2 Tx commit timestamp (not a relay tx -> nil)'].notna())
    
    # 片内交易 (Inner-Shard Transactions)
    inner_shard_mask = ~cross_shard_mask
    
    return cross_shard_mask, inner_shard_mask

def analyze_delay_ratio(df, cross_shard_mask, inner_shard_mask):
    """分析时延比例"""
    print("\n" + "=" * 80)
    print("时延比例诊断分析")
    print("=" * 80)
    
    latency_column = 'Confirmed latency of this tx (ms)'
    
    # 基本统计
    ctx_latency = df[cross_shard_mask][latency_column]
    itx_latency = df[inner_shard_mask][latency_column]
    
    ctx_mean = ctx_latency.mean()
    itx_mean = itx_latency.mean()
    ratio = ctx_mean / itx_mean if itx_mean > 0 else float('inf')
    
    print(f"\n📊 基本时延统计:")
    print(f"  ITX平均时延: {itx_mean:.2f} ms")
    print(f"  CTX平均时延: {ctx_mean:.2f} ms")
    print(f"  时延比例: {ratio:.2f}x")
    
    if ratio > 2.0:
        print(f"\n⚠️  警告: 时延比例过高 ({ratio:.2f}x > 2.0)")
    elif ratio < 1.5:
        print(f"\n✅ 时延比例良好 ({ratio:.2f}x < 1.5)")
    else:
        print(f"\n🟡 时延比例一般 (1.5 <= {ratio:.2f}x <= 2.0)")
    
    return ratio, ctx_mean, itx_mean

def analyze_transaction_counts(df, cross_shard_mask, inner_shard_mask):
    """分析交易数量分布"""
    print("\n" + "=" * 80)
    print("交易数量分析")
    print("=" * 80)
    
    total = len(df)
    ctx_count = cross_shard_mask.sum()
    itx_count = inner_shard_mask.sum()
    
    ctx_pct = (ctx_count / total * 100) if total > 0 else 0
    itx_pct = (itx_count / total * 100) if total > 0 else 0
    
    print(f"\n📈 交易分布:")
    print(f"  总交易数: {total:,}")
    print(f"  CTX数量: {ctx_count:,} ({ctx_pct:.1f}%)")
    print(f"  ITX数量: {itx_count:,} ({itx_pct:.1f}%)")
    
    # 检查CTX占比是否过低
    if ctx_pct < 10:
        print(f"\n⚠️  警告: CTX占比过低 ({ctx_pct:.1f}% < 10%)")
        print("  可能原因:")
        print("  1. CTX交易被Justitia调度器分类为Case2并丢弃")
        print("  2. CTX交易在交易池中优先级过低")
        print("  3. 补贴R计算不正确，导致uA过低")
    
    return ctx_count, itx_count, total

def analyze_fee_data(fee_df):
    """分析费用数据（如果可用）"""
    if fee_df is None:
        print("\n⚠️  费用数据不可用，跳过费用分析")
        return
    
    print("\n" + "=" * 80)
    print("费用数据分析")
    print("=" * 80)
    
    # 检查是否有补贴相关列
    subsidy_cols = [col for col in fee_df.columns if 'subsidy' in col.lower() or 'reward' in col.lower()]
    utility_cols = [col for col in fee_df.columns if 'utility' in col.lower() or 'ua' in col.lower() or 'ub' in col.lower()]
    
    print(f"\n📋 可用列:")
    print(f"  补贴相关列: {subsidy_cols if subsidy_cols else '无'}")
    print(f"  效用相关列: {utility_cols if utility_cols else '无'}")
    
    if not subsidy_cols and not utility_cols:
        print("\n⚠️  警告: 未找到补贴或效用相关数据")
        print("  这可能意味着:")
        print("  1. Justitia机制未正确启用")
        print("  2. 费用跟踪器未正确初始化")
        print("  3. 数据记录功能未启用")

def check_config():
    """检查配置文件"""
    print("\n" + "=" * 80)
    print("配置检查")
    print("=" * 80)
    
    config_path = Path('../paramsConfig.json')
    if not config_path.exists():
        print("❌ 错误: 找不到配置文件 paramsConfig.json")
        return
    
    import json
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 关键参数
    enable_justitia = config.get('EnableJustitia', 0)
    subsidy_mode = config.get('JustitiaSubsidyMode', 0)
    window_blocks = config.get('JustitiaWindowBlocks', 16)
    gamma_min = config.get('JustitiaGammaMin', 0)
    gamma_max = config.get('JustitiaGammaMax', 0)
    
    print(f"\n⚙️  Justitia配置:")
    print(f"  EnableJustitia: {enable_justitia} {'✅' if enable_justitia == 1 else '❌'}")
    print(f"  SubsidyMode: {subsidy_mode} ({get_subsidy_mode_name(subsidy_mode)})")
    print(f"  WindowBlocks: {window_blocks}")
    print(f"  GammaMin: {gamma_min}")
    print(f"  GammaMax: {gamma_max}")
    
    # 诊断问题
    issues = []
    
    if enable_justitia != 1:
        issues.append("❌ EnableJustitia未启用 (应设置为1)")
    
    if gamma_min == 0 and gamma_max == 0:
        issues.append("⚠️  GammaMin和GammaMax都为0，没有补贴预算限制")
        issues.append("   这可能导致补贴R计算不受约束")
    
    if window_blocks < 4:
        issues.append(f"⚠️  WindowBlocks过小 ({window_blocks} < 4)")
        issues.append("   费用平均值可能不稳定")
    
    if subsidy_mode == 0:
        issues.append("❌ SubsidyMode为0 (无补贴模式)")
        issues.append("   Justitia机制将不会提供补贴")
    
    if issues:
        print(f"\n🔍 发现的问题:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ 配置看起来正常")
    
    return config

def get_subsidy_mode_name(mode):
    """获取补贴模式名称"""
    modes = {
        0: "None (无补贴)",
        1: "DestAvg (R=E(f_B))",
        2: "SumAvg (R=E(f_A)+E(f_B))",
        3: "Custom (自定义)",
        4: "ExtremeFixed (固定1 ETH)"
    }
    return modes.get(mode, "Unknown")

def generate_diagnostic_report(ratio, ctx_mean, itx_mean, ctx_count, itx_count, total, config):
    """生成诊断报告"""
    print("\n" + "=" * 80)
    print("🔍 诊断报告")
    print("=" * 80)
    
    print(f"\n📊 实验结果摘要:")
    print(f"  - 时延比例: {ratio:.2f}x")
    print(f"  - CTX平均时延: {ctx_mean:.2f} ms")
    print(f"  - ITX平均时延: {itx_mean:.2f} ms")
    print(f"  - CTX占比: {ctx_count/total*100:.1f}% ({ctx_count:,}/{total:,})")
    
    print(f"\n🔍 可能的原因分析:")
    
    # 原因1: 费用跟踪器初始化问题
    print(f"\n1️⃣  费用跟踪器初始化问题")
    print(f"  问题: 在实验初期，费用跟踪器可能还没有收集到足够的ITX费用数据")
    print(f"  影响: EA和EB可能为0或很小，导致:")
    print(f"    - 补贴R计算不准确")
    print(f"    - Shapley值uA和uB分配不合理")
    print(f"    - CTX被错误分类为Case2或Case3")
    print(f"  解决方案:")
    print(f"    - 增加预热期，让系统先处理一些ITX交易")
    print(f"    - 设置合理的初始费用值")
    print(f"    - 检查费用跟踪器的更新逻辑")
    
    # 原因2: Justitia调度器逻辑
    print(f"\n2️⃣  Justitia调度器分类逻辑")
    print(f"  问题: 新引入的调度器会根据uA对CTX进行分类:")
    print(f"    - Case1 (uA >= EA): 高优先级，总是打包")
    print(f"    - Case2 (uA <= EA-EB): 低优先级，丢弃")
    print(f"    - Case3 (EA-EB < uA < EA): 中等优先级，有空间才打包")
    print(f"  影响: 如果uA计算不正确，CTX可能被错误分类")
    print(f"  解决方案:")
    print(f"    - 检查uA的计算逻辑")
    print(f"    - 验证补贴R是否正确计算")
    print(f"    - 添加日志输出uA、EA、EB的值")
    
    # 原因3: 补贴模式配置
    subsidy_mode = config.get('JustitiaSubsidyMode', 0)
    print(f"\n3️⃣  补贴模式配置")
    print(f"  当前模式: {subsidy_mode} ({get_subsidy_mode_name(subsidy_mode)})")
    if subsidy_mode == 1:
        print(f"  说明: R = E(f_B) (目标分片的平均ITX费用)")
        print(f"  注意: 如果E(f_B)很小或为0，补贴R也会很小")
    elif subsidy_mode == 0:
        print(f"  ⚠️  警告: 当前为无补贴模式，Justitia机制不会生效")
    print(f"  解决方案:")
    print(f"    - 考虑使用SubsidyMode=2 (SumAvg)提供更多补贴")
    print(f"    - 或使用SubsidyMode=4 (ExtremeFixed)提供固定补贴")
    
    # 原因4: 与之前模拟的差异
    print(f"\n4️⃣  代码修改导致的差异")
    print(f"  问题: 最近的代码修改引入了新的Justitia调度器")
    print(f"  之前: 使用简单的优先级队列 (packTxsSimple)")
    print(f"    - 只基于FeeToProposer排序")
    print(f"    - 不涉及Shapley值计算")
    print(f"  现在: 使用Justitia调度器 (packTxsWithScheduler)")
    print(f"    - 基于uA/uB进行智能选择")
    print(f"    - 涉及Case1/Case2/Case3分类")
    print(f"  解决方案:")
    print(f"    - 临时禁用调度器，使用简单模式验证")
    print(f"    - 或调试调度器逻辑，确保正确实现")
    
    print(f"\n💡 建议的调试步骤:")
    print(f"  1. 添加详细日志，输出每个CTX的:")
    print(f"     - FeeToProposer (用户支付的费用)")
    print(f"     - EA, EB (源和目标分片的平均ITX费用)")
    print(f"     - R (补贴)")
    print(f"     - uA, uB (Shapley值分配)")
    print(f"     - Case (分类结果)")
    print(f"  2. 检查费用跟踪器的更新频率")
    print(f"  3. 验证ITX交易是否被正确识别和统计")
    print(f"  4. 对比使用简单模式和调度器模式的结果")

def create_diagnostic_plots(df, cross_shard_mask, inner_shard_mask):
    """创建诊断图表"""
    latency_column = 'Confirmed latency of this tx (ms)'
    ctx_latency = df[cross_shard_mask][latency_column]
    itx_latency = df[inner_shard_mask][latency_column]
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('时延比例诊断图表', fontsize=16, fontweight='bold')
    
    # 1. 时延分布对比
    ax1 = axes[0, 0]
    ax1.hist(itx_latency, bins=50, alpha=0.6, label=f'ITX (n={len(itx_latency)})', color='blue')
    ax1.hist(ctx_latency, bins=50, alpha=0.6, label=f'CTX (n={len(ctx_latency)})', color='red')
    ax1.set_title('时延分布直方图')
    ax1.set_xlabel('确认时延 (ms)')
    ax1.set_ylabel('频数')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 箱线图对比
    ax2 = axes[0, 1]
    data_for_box = [itx_latency, ctx_latency]
    labels = ['ITX', 'CTX']
    box_plot = ax2.boxplot(data_for_box, labels=labels, patch_artist=True)
    colors = ['lightblue', 'lightcoral']
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
    ax2.set_title('时延分布箱线图')
    ax2.set_ylabel('确认时延 (ms)')
    ax2.grid(True, alpha=0.3)
    
    # 3. CDF对比
    ax3 = axes[1, 0]
    
    def plot_cdf(data, label, color):
        sorted_data = np.sort(data)
        y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        ax3.plot(sorted_data, y, label=label, color=color, linewidth=2)
    
    plot_cdf(itx_latency, 'ITX', 'blue')
    plot_cdf(ctx_latency, 'CTX', 'red')
    ax3.set_title('累积分布函数 (CDF)')
    ax3.set_xlabel('确认时延 (ms)')
    ax3.set_ylabel('累积概率')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 时延比率分析
    ax4 = axes[1, 1]
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    ratios = []
    
    for p in percentiles:
        itx_val = itx_latency.quantile(p/100)
        ctx_val = ctx_latency.quantile(p/100)
        if itx_val > 0:
            ratio = ctx_val / itx_val
            ratios.append(ratio)
        else:
            ratios.append(0)
    
    bars = ax4.bar(range(len(percentiles)), ratios, 
                   color=['lightblue' if r < 2 else 'lightcoral' for r in ratios])
    ax4.set_title('不同分位数时延比率')
    ax4.set_xlabel('分位数 (%)')
    ax4.set_ylabel('CTX/ITX时延比率')
    ax4.set_xticks(range(len(percentiles)))
    ax4.set_xticklabels([f'{p}%' for p in percentiles])
    ax4.axhline(y=1, color='black', linestyle='--', alpha=0.5, label='理想比率')
    ax4.axhline(y=2, color='red', linestyle='--', alpha=0.5, label='可接受上限')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 添加数值标签
    for i, (bar, ratio) in enumerate(zip(bars, ratios)):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, 
                f'{ratio:.2f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    return fig

def main():
    """主函数"""
    print("=" * 80)
    print("Justitia时延比例诊断工具")
    print("=" * 80)
    
    # 1. 检查配置
    config = check_config()
    
    # 2. 加载数据
    print("\n正在加载数据...")
    df, fee_df = load_data()
    
    if df is None:
        print("❌ 无法加载数据，退出")
        return
    
    # 3. 分类交易
    cross_shard_mask, inner_shard_mask = classify_transactions(df)
    
    # 4. 分析时延比例
    ratio, ctx_mean, itx_mean = analyze_delay_ratio(df, cross_shard_mask, inner_shard_mask)
    
    # 5. 分析交易数量
    ctx_count, itx_count, total = analyze_transaction_counts(df, cross_shard_mask, inner_shard_mask)
    
    # 6. 分析费用数据
    analyze_fee_data(fee_df)
    
    # 7. 生成诊断报告
    generate_diagnostic_report(ratio, ctx_mean, itx_mean, ctx_count, itx_count, total, config)
    
    # 8. 创建诊断图表
    print("\n正在生成诊断图表...")
    fig = create_diagnostic_plots(df, cross_shard_mask, inner_shard_mask)
    
    # 保存图表
    output_path = Path('../expTest/result/diagnostic_delay_ratio.png')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 诊断图表已保存到: {output_path}")
    
    plt.show()
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)
    
    input("\n按Enter键关闭...")

if __name__ == "__main__":
    main()
