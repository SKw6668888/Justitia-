@echo off
chcp 65001 >nul
echo ========================================
echo   Justitia PID Mode Experiment
echo ========================================
echo.

echo Configuring PID mode...
copy /Y paramsConfig_PID.json paramsConfig.json
echo.

echo Cleaning old data...
if exist expTest_PID (
    rd /s /q expTest_PID
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
echo PID mode experiment started!
echo Results will be saved in: expTest_PID/result/
echo.
