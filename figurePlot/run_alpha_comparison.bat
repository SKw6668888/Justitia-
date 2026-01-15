@echo off
chcp 65001 >nul
echo ============================================
echo   Lagrangian Alpha 参数对比分析
echo ============================================
echo.

cd /d "%~dp0"

echo 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未找到 Python！
    echo 请安装 Python 3.7+ 并添加到 PATH
    pause
    exit /b 1
)
echo ✓ Python 已安装
echo.

echo 检查依赖库...
pip show pandas >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装 pandas...
    pip install pandas
)

pip show matplotlib >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装 matplotlib...
    pip install matplotlib
)

pip show numpy >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装 numpy...
    pip install numpy
)
echo ✓ 依赖库检查完成
echo.

echo ============================================
echo   运行对比分析脚本
echo ============================================
echo.

python compare_alpha_experiments.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   ✅ 分析完成！
    echo ============================================
    echo.
    echo 生成的图表保存在 figures\ 文件夹中：
    echo   - alpha_comparison_tps.png
    echo   - alpha_comparison_latency.png
    echo   - alpha_comparison_ctx_ratio.png
    echo   - alpha_comparison_summary.png
    echo   - alpha_comparison_report.txt
    echo.
    echo 按任意键打开 figures 文件夹...
    pause >nul
    explorer figures
) else (
    echo.
    echo ❌ 分析过程中出现错误
    echo.
    pause
)
