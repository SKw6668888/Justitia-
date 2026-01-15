@echo off
chcp 65001 >nul
echo ============================================
echo   预算硬约束测试对比图表生成
echo   Budget Constraint Test Comparison
echo ============================================
echo.

cd /d "%~dp0"

echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python not found!
    pause
    exit /b 1
)
echo ✓ Python installed
echo.

echo ============================================
echo   Generating Budget Constraint Charts
echo ============================================
echo.

python compare_budget_constraint.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   ✅ Charts Generated Successfully!
    echo ============================================
    echo.
    echo Opening figures folder...
    start figures
) else (
    echo.
    echo ❌ Error during chart generation
    echo.
    pause
)
