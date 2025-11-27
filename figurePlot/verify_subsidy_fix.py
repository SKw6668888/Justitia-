import pandas as pd

# 读取两个实验的交易详情数据
print("=" * 60)
print("验证补贴计算修正")
print("=" * 60)

# R=E(f_B)
tx_eb = pd.read_csv(r'c:\Users\admin\Desktop\Justitia 拓展实验\Justitia-\expTest_R_EB\result\supervisor_measureOutput\Tx_Details.csv')
eff_eb = pd.read_csv(r'c:\Users\admin\Desktop\Justitia 拓展实验\Justitia-\expTest_R_EB\result\supervisor_measureOutput\Justitia_Effectiveness.csv')

# R=E(f_A)+E(f_B)
tx_ea_eb = pd.read_csv(r'c:\Users\admin\Desktop\Justitia 拓展实验\Justitia-\expTest_R_EA_EB\result\supervisor_measureOutput\Tx_Details.csv')
eff_ea_eb = pd.read_csv(r'c:\Users\admin\Desktop\Justitia 拓展实验\Justitia-\expTest_R_EA_EB\result\supervisor_measureOutput\Justitia_Effectiveness.csv')

print("\n" + "=" * 60)
print("R=E(f_B) 实验数据分析")
print("=" * 60)

# 分离ITX和CTX
itx_eb = tx_eb[tx_eb['IsCrossShard'] == False]
ctx_eb = tx_eb[tx_eb['IsCrossShard'] == True]

print(f"总交易数: {len(tx_eb)}")
print(f"ITX数量: {len(itx_eb)}")
print(f"CTX数量: {len(ctx_eb)}")

# 计算ITX平均费用
avg_itx_fee_eb = itx_eb['FeeToProposer (wei)'].mean()
print(f"\nITX平均费用 E(f): {avg_itx_fee_eb / 1e18:.6f} ETH ({avg_itx_fee_eb:.0f} Wei)")

# 计算CTX平均费用（对比）
avg_ctx_fee_eb = ctx_eb['FeeToProposer (wei)'].mean()
print(f"CTX平均费用: {avg_ctx_fee_eb / 1e18:.6f} ETH ({avg_ctx_fee_eb:.0f} Wei)")

# 计算总CTX数量
total_ctx_eb = eff_eb['Cross-Shard Tx Count'].sum()
print(f"\n总CTX数(从Effectiveness): {total_ctx_eb}")

# 计算补贴
subsidy_eb = total_ctx_eb * avg_itx_fee_eb / 1e18
print(f"累计补贴 (R=E(f_B)): {subsidy_eb:.2f} ETH")

print("\n" + "=" * 60)
print("R=E(f_A)+E(f_B) 实验数据分析")
print("=" * 60)

# 分离ITX和CTX
itx_ea_eb = tx_ea_eb[tx_ea_eb['IsCrossShard'] == False]
ctx_ea_eb = tx_ea_eb[tx_ea_eb['IsCrossShard'] == True]

print(f"总交易数: {len(tx_ea_eb)}")
print(f"ITX数量: {len(itx_ea_eb)}")
print(f"CTX数量: {len(ctx_ea_eb)}")

# 计算ITX平均费用
avg_itx_fee_ea_eb = itx_ea_eb['FeeToProposer (wei)'].mean()
print(f"\nITX平均费用 E(f): {avg_itx_fee_ea_eb / 1e18:.6f} ETH ({avg_itx_fee_ea_eb:.0f} Wei)")

# 计算CTX平均费用（对比）
avg_ctx_fee_ea_eb = ctx_ea_eb['FeeToProposer (wei)'].mean()
print(f"CTX平均费用: {avg_ctx_fee_ea_eb / 1e18:.6f} ETH ({avg_ctx_fee_ea_eb:.0f} Wei)")

# 计算总CTX数量
total_ctx_ea_eb = eff_ea_eb['Cross-Shard Tx Count'].sum()
print(f"\n总CTX数(从Effectiveness): {total_ctx_ea_eb}")

# 计算补贴 (R = E(f_A) + E(f_B) ≈ 2 * E(f))
subsidy_ea_eb = total_ctx_ea_eb * avg_itx_fee_ea_eb * 2 / 1e18
print(f"累计补贴 (R=E(f_A)+E(f_B)): {subsidy_ea_eb:.2f} ETH")

print("\n" + "=" * 60)
print("对比分析")
print("=" * 60)

print(f"\nITX平均费用比率: {avg_itx_fee_eb / avg_itx_fee_ea_eb:.2f}x")
print(f"CTX数量比率: {total_ctx_eb / total_ctx_ea_eb:.2f}x")
print(f"累计补贴比率: {subsidy_ea_eb / subsidy_eb:.2f}x")

print(f"\n✓ R=E(f_A)+E(f_B) 应该是 R=E(f_B) 的 {subsidy_ea_eb / subsidy_eb:.2f}x")
print(f"  理论上应该接近2x（如果两个实验的ITX费用和CTX数量相似）")

if subsidy_ea_eb > subsidy_eb:
    print(f"\n✓ 正确：R=E(f_A)+E(f_B) ({subsidy_ea_eb:.2f} ETH) > R=E(f_B) ({subsidy_eb:.2f} ETH)")
else:
    print(f"\n✗ 错误：R=E(f_A)+E(f_B) ({subsidy_ea_eb:.2f} ETH) < R=E(f_B) ({subsidy_eb:.2f} ETH)")
    print("  这表明两个实验的条件差异很大")
