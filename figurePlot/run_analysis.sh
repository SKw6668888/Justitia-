#!/bin/bash
# Justitia 数据分析与绘图一键运行脚本 (Linux/Mac)
# 
# 使用方法:
#   chmod +x run_analysis.sh
#   ./run_analysis.sh

echo "============================================================"
echo "Justitia 数据分析与绘图工具"
echo "============================================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

echo "[1/3] 检查依赖包..."
if ! python3 -c "import numpy" 2>/dev/null; then
    echo "正在安装依赖包..."
    pip3 install numpy pandas matplotlib seaborn scipy
fi

echo ""
echo "[2/3] 运行数据分析器..."
python3 justitia_data_analyzer.py
if [ $? -ne 0 ]; then
    echo "[错误] 数据分析失败"
    exit 1
fi

echo ""
echo "[3/3] 生成图表..."
python3 justitia_plot_all.py
if [ $? -ne 0 ]; then
    echo "[错误] 绘图失败"
    exit 1
fi

echo ""
echo "============================================================"
echo "[完成] 所有图表已生成！"
echo "数据文件: data/"
echo "图表文件: figures/"
echo "============================================================"
echo ""

# 在Mac上打开图表文件夹
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [ -d "figures" ]; then
        open figures
    fi
fi

# 在Linux上尝试打开图表文件夹
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -d "figures" ]; then
        xdg-open figures 2>/dev/null || echo "请手动查看 figures/ 目录"
    fi
fi
