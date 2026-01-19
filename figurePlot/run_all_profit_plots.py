#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行所有矿工利润可视化脚本
Run all proposer profit visualization scripts
"""

import subprocess
import sys
from pathlib import Path

def run_script(script_name):
    """运行单个脚本"""
    print(f"\n{'='*60}")
    print(f"运行脚本: {script_name}")
    print('='*60)
    
    result = subprocess.run([sys.executable, script_name], 
                          capture_output=False,
                          text=True)
    
    return result.returncode == 0

def main():
    print("\n" + "="*60)
    print("矿工利润可视化脚本集 - 一键运行")
    print("Proposer Profit Visualization Suite")
    print("="*60)
    
    scripts = [
        ('9_boxplot_profit.py', '图9: 箱线图（展示离群值）'),
        ('10_kde_profit.py', '图10: KDE概率密度图（展示长尾形态）'),
        ('11_tail_latency_bar.py', '图11: P95/P99柱状图（尾部延迟对比）')
    ]
    
    results = {}
    
    for script_file, description in scripts:
        script_path = Path(__file__).parent / script_file
        
        if not script_path.exists():
            print(f"\n[ERROR] 脚本不存在: {script_file}")
            results[script_file] = False
            continue
        
        print(f"\n{description}")
        success = run_script(str(script_path))
        results[script_file] = success
    
    # 总结
    print("\n" + "="*60)
    print("执行总结")
    print("="*60)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for script_file, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {status}: {script_file}")
    
    print(f"\n总计: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("\n[SUCCESS] 所有图表生成成功！")
        print("输出目录: figures/")
        return 0
    else:
        print("\n[WARNING] 部分图表生成失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
