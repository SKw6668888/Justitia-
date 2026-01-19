@echo off
chcp 65001 >nul
echo ========================================
echo   Justitia Hybrid Mode Experiment
echo   (Hierarchical PID + Lagrangian)
echo ========================================
echo.

echo Configuring Hybrid mode (Mode 7)...
copy /Y paramsConfig_Hybrid.json paramsConfig.json
echo.

echo Cleaning old data...
if exist expTest_Hybrid (
    rd /s /q expTest_Hybrid
)
echo.

echo Compiling...
go build
if %errorlevel% neq 0 (
    echo Compilation failed!
    pause
    exit /b %errorlevel%
)
echo.

echo Starting 4 shards with 16 nodes...
timeout /t 2 /nobreak >nul

start cmd /k go run main.go -n 0 -N 4 -s 0 -S 4
start cmd /k go run main.go -n 1 -N 4 -s 0 -S 4
start cmd /k go run main.go -n 2 -N 4 -s 0 -S 4
start cmd /k go run main.go -n 3 -N 4 -s 0 -S 4

start cmd /k go run main.go -n 0 -N 4 -s 1 -S 4
start cmd /k go run main.go -n 1 -N 4 -s 1 -S 4
start cmd /k go run main.go -n 2 -N 4 -s 1 -S 4
start cmd /k go run main.go -n 3 -N 4 -s 1 -S 4

start cmd /k go run main.go -n 0 -N 4 -s 2 -S 4
start cmd /k go run main.go -n 1 -N 4 -s 2 -S 4
start cmd /k go run main.go -n 2 -N 4 -s 2 -S 4
start cmd /k go run main.go -n 3 -N 4 -s 2 -S 4

start cmd /k go run main.go -n 0 -N 4 -s 3 -S 4
start cmd /k go run main.go -n 1 -N 4 -s 3 -S 4
start cmd /k go run main.go -n 2 -N 4 -s 3 -S 4
start cmd /k go run main.go -n 3 -N 4 -s 3 -S 4

start cmd /k go run main.go -c -N 4 -S 4

echo.
echo Hybrid mode experiment started!
echo Results will be saved in: expTest_Hybrid/result/
echo.
echo Control Strategy:
echo   - Lagrangian Layer: Sets optimal target R* every 10 blocks
echo   - PID Layer: Tracks target with fast adjustments
echo.
