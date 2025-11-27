@echo off
REM Justitia 数据分析与绘图一键运行脚本 (Windows)
REM 
REM 使用方法:
REM   1. 确保已运行5次实验并正确命名文件夹
REM   2. 双击运行此脚本

echo ============================================================
echo Justitia 数据分析与绘图工具
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [1/3] 检查依赖包...
pip show numpy >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install numpy pandas matplotlib seaborn scipy
)

echo.
echo [2/3] 运行数据分析器...
python justitia_data_analyzer.py
if errorlevel 1 (
    echo [错误] 数据分析失败
    pause
    exit /b 1
)

echo.
echo [3/3] 生成图表...
python justitia_plot_all.py
if errorlevel 1 (
    echo [错误] 绘图失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [完成] 所有图表已生成！
echo 数据文件: data\
echo 图表文件: figures\
echo ============================================================
echo.

REM 打开图表文件夹
if exist figures\ (
    explorer figures
)

pause
