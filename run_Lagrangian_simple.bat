@echo off
chcp 65001 >nul
echo ========================================
echo   Justitia Lagrangian Mode Experiment
echo ========================================
echo.

echo Configuring Lagrangian mode...
copy /Y paramsConfig_Lagrangian.json paramsConfig.json
echo.

echo Cleaning old data...
if exist expTest_Lagrangian (
    rd /s /q expTest_Lagrangian
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
echo Lagrangian mode experiment started!
echo Results will be saved in: expTest_Lagrangian/result/
echo.
