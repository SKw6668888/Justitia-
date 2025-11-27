@echo off
echo ========================================
echo 重新分析实验数据（修复版）
echo ========================================
echo.

cd figurePlot

echo [1/5] 分析无Justitia机制...
python justitia_effectiveness_analysis.py
echo.

echo 完成！请查看输出结果
pause
