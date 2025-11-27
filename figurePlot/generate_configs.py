#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Justitia 实验配置生成器

自动生成5种不同补贴机制的配置文件

使用方法:
    python generate_configs.py

输出: 在当前目录生成5个配置文件
"""

import json
from pathlib import Path

# 读取基础配置模板
BASE_CONFIG_PATH = Path("..") / "paramsConfig.json"

def load_base_config():
    """加载基础配置"""
    if not BASE_CONFIG_PATH.exists():
        print(f"⚠️  警告: 未找到基础配置文件 {BASE_CONFIG_PATH}")
        print("使用默认配置...")
        return {
            "ConsensusMethod": 3,
            "PbftViewChangeTimeOut": 20000,
            "ExpDataRootDir": "expTest",
            "Block_Interval": 5000,
            "BlockSize": 1000,
            "BlocksizeInBytes": 200000,
            "UseBlocksizeInBytes": 0,
            "InjectSpeed": 2000,
            "TotalDataSize": 250000,
            "TxBatchSize": 25000,
            "BrokerNum": 10,
            "RelayWithMerkleProof": 0,
            "DatasetFile": "./23000000to23249999_BlockTransaction.csv",
            "ReconfigTimeGap": 50,
            "Delay": -1,
            "JitterRange": -1,
            "Bandwidth": 10000000,
            "EnableJustitia": 1,
            "JustitiaSubsidyMode": 1,
            "JustitiaWindowBlocks": 16,
            "JustitiaGammaMin": 0,
            "JustitiaGammaMax": 0,
            "JustitiaRewardBase": 1000.0
        }
    
    with open(BASE_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_config(base_config, mechanism_name, enable_justitia, subsidy_mode, reward_base):
    """生成特定机制的配置"""
    config = base_config.copy()
    
    config["EnableJustitia"] = enable_justitia
    config["JustitiaSubsidyMode"] = subsidy_mode
    config["JustitiaRewardBase"] = reward_base
    
    return config

def save_config(config, filename, description):
    """保存配置文件"""
    output_path = Path(filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 已生成: {filename}")
    print(f"  说明: {description}")
    print()

def main():
    print("=" * 60)
    print("Justitia 实验配置生成器")
    print("=" * 60)
    print()
    
    # 加载基础配置
    base_config = load_base_config()
    print(f"✓ 基础配置加载完成")
    print()
    
    # 定义5种机制配置
    mechanisms = [
        {
            'name': 'Monoxide',
            'filename': 'paramsConfig_monoxide.json',
            'description': 'Monoxide基线（无Justitia机制）',
            'enable_justitia': 0,
            'subsidy_mode': 0,
            'reward_base': 0.0
        },
        {
            'name': 'R=0',
            'filename': 'paramsConfig_R0.json',
            'description': 'Justitia启用但无补贴（R=0）',
            'enable_justitia': 1,
            'subsidy_mode': 0,
            'reward_base': 0.0
        },
        {
            'name': 'R=E(f_B)',
            'filename': 'paramsConfig_R_EB.json',
            'description': 'Justitia推荐方案（R=目标分片平均费用）',
            'enable_justitia': 1,
            'subsidy_mode': 1,
            'reward_base': 1000.0
        },
        {
            'name': 'R=E(f_A)+E(f_B)',
            'filename': 'paramsConfig_R_EA_EB.json',
            'description': 'Justitia激进方案（R=两分片平均费用之和）',
            'enable_justitia': 1,
            'subsidy_mode': 2,
            'reward_base': 1000.0
        },
        {
            'name': 'R=1 ETH/CTX',
            'filename': 'paramsConfig_R_1ETH.json',
            'description': 'Justitia固定补贴（R=1 ETH per CTX）',
            'enable_justitia': 1,
            'subsidy_mode': 4,
            'reward_base': 1000000000000000000.0  # 1 ETH = 10^18 Wei
        }
    ]
    
    print("开始生成配置文件...")
    print()
    
    # 生成所有配置
    for mech in mechanisms:
        config = generate_config(
            base_config,
            mech['name'],
            mech['enable_justitia'],
            mech['subsidy_mode'],
            mech['reward_base']
        )
        
        save_config(config, mech['filename'], mech['description'])
    
    print("=" * 60)
    print("✓ 所有配置文件生成完成！")
    print("=" * 60)
    print()
    print("使用说明:")
    print("1. 将配置文件复制到项目根目录，重命名为 paramsConfig.json")
    print("2. 运行实验: ./blockEmulator")
    print("3. 实验完成后，将 expTest/ 文件夹重命名:")
    print()
    for mech in mechanisms:
        folder_name = mech['filename'].replace('paramsConfig_', 'expTest_').replace('.json', '')
        print(f"   - {mech['name']}: 重命名为 {folder_name}/")
    print()
    print("4. 运行5次实验后，执行数据分析:")
    print("   python justitia_data_analyzer.py")
    print("   python justitia_plot_all.py")
    print()
    print("或使用一键脚本:")
    print("   run_analysis.bat (Windows)")
    print("   ./run_analysis.sh (Linux/Mac)")
    print("=" * 60)

if __name__ == "__main__":
    main()
