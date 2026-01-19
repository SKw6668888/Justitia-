import pandas as pd

# 读取Hybrid数据
df = pd.read_csv(r'../expTest_Hybrid/result/supervisor_measureOutput/Justitia_Effectiveness.csv')
print("Hybrid - Justitia_Effectiveness.csv列名:")
for i, col in enumerate(df.columns):
    print(f"  {i}: {col}")

print(f"\n前3行数据:")
print(df.head(3))
