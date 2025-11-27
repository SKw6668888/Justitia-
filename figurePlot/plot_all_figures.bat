@echo off
chcp 65001 >nul
echo ============================================================
echo Justitia 图表生成器 - 生成所有7张图表
echo ============================================================
echo.

echo 第1步: 运行数据分析器
echo ------------------------------------------------------------
python justitia_data_analyzer.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ 数据分析失败，请检查实验数据是否存在
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 第2步: 生成7张图表
echo ============================================================
echo.

echo [1/7] 生成图1: CTX排队延迟箱线图...
python plot_fig1_boxplot.py
if %errorlevel% neq 0 (
    echo ⚠️ 图1生成失败
)
echo.

echo [2/7] 生成图2: CTX/ITX延迟比值柱状图...
python plot_fig2_ratio.py
if %errorlevel% neq 0 (
    echo ⚠️ 图2生成失败
)
echo.

echo [3/7] 生成图3: CTX延迟KDE分布...
python plot_fig3_kde.py
if %errorlevel% neq 0 (
    echo ⚠️ 图3生成失败
)
echo.

echo [4/7] 生成图4: CTX延迟CDF...
python plot_fig4_cdf.py
if %errorlevel% neq 0 (
    echo ⚠️ 图4生成失败
)
echo.

echo [5/7] 生成图5: 区块中CTX占比...
python plot_fig5_ctx_ratio.py
if %errorlevel% neq 0 (
    echo ⚠️ 图5生成失败
)
echo.

echo [6/7] 生成图6: 累计补贴发行量...
python plot_fig6_subsidy.py
if %errorlevel% neq 0 (
    echo ⚠️ 图6生成失败
)
echo.

echo [7/7] 生成图7: 提议者利润分布...
python plot_fig7_profit.py
if %errorlevel% neq 0 (
    echo ⚠️ 图7生成失败
)
echo.

echo ============================================================
echo ✓ 所有图表生成完成！
echo ============================================================
echo.
echo 请查看 figures\ 目录获取生成的图表
echo.

pause
