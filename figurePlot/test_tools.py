#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Justitia 工具测试脚本

用于验证数据分析和绘图工具是否正常工作

使用方法:
    python test_tools.py
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

def test_dependencies():
    """测试依赖包是否安装"""
    print("\n" + "=" * 60)
    print("测试1: 检查依赖包")
    print("=" * 60)
    
    required_packages = {
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'matplotlib': 'Matplotlib',
        'seaborn': 'Seaborn',
        'scipy': 'SciPy'
    }
    
    all_installed = True
    
    for package, name in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {name} 已安装")
        except ImportError:
            print(f"✗ {name} 未安装")
            all_installed = False
    
    if all_installed:
        print("\n✓ 所有依赖包已安装")
        return True
    else:
        print("\n✗ 部分依赖包缺失，请运行: pip install -r requirements.txt")
        return False

def test_data_structure():
    """测试数据目录结构"""
    print("\n" + "=" * 60)
    print("测试2: 检查实验数据目录")
    print("=" * 60)
    
    base_dir = Path("..")
    expected_folders = [
        'expTest_monoxide',
        'expTest_R0',
        'expTest_R_EB',
        'expTest_R_EA_EB',
        'expTest_R_1ETH'
    ]
    
    found_count = 0
    
    for folder in expected_folders:
        folder_path = base_dir / folder / "result"
        if folder_path.exists():
            csv_file = folder_path / "Justitia_Effectiveness.csv"
            if csv_file.exists():
                print(f"✓ {folder}: 数据完整")
                found_count += 1
            else:
                print(f"⚠ {folder}: 缺少 Justitia_Effectiveness.csv")
        else:
            print(f"✗ {folder}: 文件夹不存在")
    
    if found_count == 0:
        print("\n⚠ 警告: 未找到任何实验数据")
        print("请先运行实验并正确命名文件夹")
        return False
    elif found_count < 5:
        print(f"\n⚠ 警告: 仅找到 {found_count}/5 个实验数据")
        print("建议完成所有5个实验以获得完整对比")
        return True
    else:
        print(f"\n✓ 找到所有 {found_count}/5 个实验数据")
        return True

def generate_sample_data():
    """生成示例数据用于测试"""
    print("\n" + "=" * 60)
    print("测试3: 生成示例数据")
    print("=" * 60)
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 生成示例数据
    sample_data = {
        'Monoxide': list(np.random.lognormal(1.5, 0.5, 100)),
        'R=0': list(np.random.lognormal(1.3, 0.5, 100)),
        'R=E(f_B)': list(np.random.lognormal(0.8, 0.4, 100)),
        'R=E(f_A)+E(f_B)': list(np.random.lognormal(0.6, 0.4, 100)),
        'R=1 ETH/CTX': list(np.random.lognormal(0.5, 0.3, 100))
    }
    
    # 保存示例数据
    test_file = data_dir / "test_sample.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"✓ 示例数据已生成: {test_file}")
    
    # 验证可以读取
    with open(test_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    
    print(f"✓ 数据读取验证成功")
    print(f"  包含 {len(loaded_data)} 种机制")
    print(f"  每种机制有 {len(loaded_data['Monoxide'])} 个数据点")
    
    return True

def test_plotting():
    """测试绘图功能"""
    print("\n" + "=" * 60)
    print("测试4: 测试绘图功能")
    print("=" * 60)
    
    try:
        import matplotlib.pyplot as plt
        
        # 创建简单测试图
        fig, ax = plt.subplots(figsize=(8, 6))
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        ax.plot(x, y)
        ax.set_xlabel('X axis')
        ax.set_ylabel('Y axis')
        ax.set_title('Test Plot')
        
        # 保存测试图
        figures_dir = Path("figures")
        figures_dir.mkdir(exist_ok=True)
        test_file = figures_dir / "test_plot.png"
        plt.savefig(test_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ 测试图表已生成: {test_file}")
        
        # 验证文件存在
        if test_file.exists():
            file_size = test_file.stat().st_size
            print(f"✓ 文件大小: {file_size} 字节")
            return True
        else:
            print("✗ 文件保存失败")
            return False
            
    except Exception as e:
        print(f"✗ 绘图测试失败: {e}")
        return False

def test_data_analysis():
    """测试数据分析功能"""
    print("\n" + "=" * 60)
    print("测试5: 测试数据分析功能")
    print("=" * 60)
    
    try:
        # 创建示例DataFrame
        data = {
            'EpochID': range(10),
            'Inner-Shard Tx Count': np.random.randint(100, 200, 10),
            'Cross-Shard Tx Count': np.random.randint(50, 100, 10),
            'Inner-Shard Avg Latency (sec)': np.random.uniform(2, 4, 10),
            'CTX Avg Latency (sec)': np.random.uniform(1, 3, 10),
            'Latency Reduction (%)': np.random.uniform(-50, 20, 10),
            'CTX Priority Rate (%)': np.random.uniform(20, 40, 10)
        }
        
        df = pd.DataFrame(data)
        
        # 计算统计信息
        ctx_avg = df['CTX Avg Latency (sec)'].mean()
        itx_avg = df['Inner-Shard Avg Latency (sec)'].mean()
        ratio = ctx_avg / itx_avg
        
        print(f"✓ DataFrame创建成功: {len(df)} 行")
        print(f"✓ CTX平均延迟: {ctx_avg:.4f} 秒")
        print(f"✓ ITX平均延迟: {itx_avg:.4f} 秒")
        print(f"✓ 延迟比值: {ratio:.4f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 数据分析测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Justitia 工具测试套件")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("依赖包检查", test_dependencies()))
    results.append(("数据目录检查", test_data_structure()))
    results.append(("示例数据生成", generate_sample_data()))
    results.append(("绘图功能", test_plotting()))
    results.append(("数据分析", test_data_analysis()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ 所有测试通过！工具可以正常使用。")
        print("\n下一步:")
        print("1. 运行实验收集数据")
        print("2. 运行 python justitia_data_analyzer.py")
        print("3. 运行 python justitia_plot_all.py")
        return True
    else:
        print(f"\n⚠ {failed} 个测试失败，请检查并修复问题。")
        return False

def main():
    success = run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
