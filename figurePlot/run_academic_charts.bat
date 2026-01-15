@echo off
chcp 65001 >nul
echo ============================================
echo   Academic PDF Chart Generation
echo ============================================
echo.

cd /d "%~dp0"

echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python not found!
    echo Please install Python 3.7+ and add to PATH
    pause
    exit /b 1
)
echo ✓ Python installed
echo.

echo Checking dependencies...
pip show pandas >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pandas...
    pip install pandas
)

pip show matplotlib >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing matplotlib...
    pip install matplotlib
)

pip show numpy >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing numpy...
    pip install numpy
)
echo ✓ Dependencies installed
echo.

echo ============================================
echo   Generating Academic Charts
echo ============================================
echo.

python plot_academic_charts.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   ✅ Charts Generated Successfully!
    echo ============================================
    echo.
    echo Generated PDF files:
    echo   📊 figures/chart_a_macro_tradeoff.pdf
    echo   📊 figures/chart_b_lambda_convergence.pdf
    echo.
    echo Opening figures folder...
    start figures
) else (
    echo.
    echo ❌ Error during chart generation
    echo.
    pause
)
