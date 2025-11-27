#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证补贴数据是否正确记录
检查CSV文件中是否包含SubsidyR列，以及补贴值是否合理
"""

import pandas as pd
import numpy as np
from pathlib import Path

def verify_subsidy_data(csv_path):
    """验证补贴数据"""
    print("=" * 80)
    print(f"验证文件: {csv_path}")
    print("=" * 80)
    
    if not Path(csv_path).exists():
        print(f"❌ 文件不存在: {csv_path}")
        return False
    
    # 读取数据
    df = pd.read_csv(csv_path)
    print(f"\n✓ 成功读取 {len(df)} 条记录")
    print(f"\n可用列: {df.columns.tolist()}")
    
    # 检查是否有补贴列
    subsidy_cols = [col for col in df.columns if 'subsidy' in col.lower() or 'reward' in col.lower()]
    fee_cols = [col for col in df.columns if 'fee' in col.lower() or 'proposer' in col.lower()]
    
    print(f"\n费用相关列: {fee_cols}")
    print(f"补贴相关列: {subsidy_cols}")
    
    if not subsidy_cols:
        print("\n⚠️  警告: 未找到补贴相关列!")
        print("这可能意味着:")
        print("1. 补贴数据未被记录到CSV")
        print("2. 列名不包含'subsidy'或'reward'")
        print("3. Justitia机制未正确启用")
        return False
    
    # 分析补贴数据
    subsidy_col = subsidy_cols[0]
    df[subsidy_col] = pd.to_numeric(df[subsidy_col], errors='coerce')
    
    print(f"\n补贴数据统计 ({subsidy_col}):")
    print(f"  总记录数: {len(df)}")
    print(f"  非零补贴: {(df[subsidy_col] > 0).sum()}")
    print(f"  零补贴: {(df[subsidy_col] == 0).sum()}")
    print(f"  空值: {df[subsidy_col].isna().sum()}")
    
    non_zero_subsidy = df[df[subsidy_col] > 0][subsidy_col]
    if len(non_zero_subsidy) > 0:
        print(f"\n非零补贴统计:")
        print(f"  平均值: {non_zero_subsidy.mean():.2e} wei")
        print(f"  中位数: {non_zero_subsidy.median():.2e} wei")
        print(f"  最小值: {non_zero_subsidy.min():.2e} wei")
        print(f"  最大值: {non_zero_subsidy.max():.2e} wei")
        
        # 检查是否有异常高的补贴（可能是Mode 4的1 ETH）
        one_eth = 1e18
        high_subsidy = non_zero_subsidy[non_zero_subsidy > one_eth * 0.9]
        if len(high_subsidy) > 0:
            print(f"\n  ⚠️  发现 {len(high_subsidy)} 笔高额补贴 (>0.9 ETH)")
            print(f"     可能是Mode 4 (ExtremeFixed)的固定补贴")
    else:
        print("\n❌ 所有补贴都为零!")
        print("   这表明补贴机制可能未生效")
    
    # 检查CTX分类
    relay_cols = [col for col in df.columns if 'relay' in col.lower()]
    if relay_cols:
        is_ctx = (df[relay_cols[0]].notna()) | (df[relay_cols[1]].notna() if len(relay_cols) > 1 else False)
        ctx_count = is_ctx.sum()
        itx_count = (~is_ctx).sum()
        
        print(f"\n交易类型分布:")
        print(f"  CTX (跨片): {ctx_count} ({ctx_count/len(df)*100:.1f}%)")
        print(f"  ITX (片内): {itx_count} ({itx_count/len(df)*100:.1f}%)")
        
        # 检查CTX是否有补贴
        ctx_with_subsidy = (is_ctx & (df[subsidy_col] > 0)).sum()
        print(f"\n  有补贴的CTX: {ctx_with_subsidy} / {ctx_count} ({ctx_with_subsidy/ctx_count*100:.1f}%)")
        
        if ctx_with_subsidy == 0 and ctx_count > 0:
            print("  ❌ 没有CTX获得补贴!")
        elif ctx_with_subsidy < ctx_count * 0.5:
            print("  ⚠️  只有部分CTX获得补贴")
        else:
            print("  ✓ 大部分CTX都获得了补贴")
    
    return True

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Justitia补贴数据验证工具")
    print("=" * 80 + "\n")
    
    # 检查各个实验的数据
    experiments = [
        ("无Justitia", "../expTest/result/supervisor_measureOutput/Tx_Details.csv"),
        ("R=0", "../expTest_R0/result/supervisor_measureOutput/Tx_Details.csv"),
        ("R=1", "../expTest_R_EB/result/supervisor_measureOutput/Tx_Details.csv"),
        ("R=2", "../expTest_R_EA_EB/result/supervisor_measureOutput/Tx_Details.csv"),
        ("R=4", "../expTest_R_1ETH/result/supervisor_measureOutput/Tx_Details.csv"),
    ]
    
    for name, path in experiments:
        print(f"\n{'='*80}")
        print(f"检查实验: {name}")
        print(f"{'='*80}")
        verify_subsidy_data(path)
        print("\n")

if __name__ == "__main__":
    main()
