@echo off
echo ======================================
echo   Cleaning old experimental data...
echo ======================================

REM Delete expTest folder if exists
if exist expTest (
    echo Deleting expTest folder...
    rd /s /q expTest
    echo expTest folder deleted.
) else (
    echo expTest folder does not exist, skipping deletion.
)

echo.
echo ======================================
echo   Compiling the project...
echo ======================================
go build
if %errorlevel% neq 0 (
    echo Compilation failed! Please check errors.
    pause
    exit /b %errorlevel%
)
echo Compilation successful!

echo.
echo ======================================
echo   Starting 4 shards with 16 nodes...
echo ======================================
timeout /t 2 /nobreak >nul

start cmd /k go run main.go -n 0 -N 4 -s 0 -S 4 & 

start cmd /k go run main.go -n 1 -N 4 -s 0 -S 4 & 

start cmd /k go run main.go -n 2 -N 4 -s 0 -S 4 & 

start cmd /k go run main.go -n 3 -N 4 -s 0 -S 4 & 

start cmd /k go run main.go -n 0 -N 4 -s 1 -S 4 & 

start cmd /k go run main.go -n 1 -N 4 -s 1 -S 4 & 

start cmd /k go run main.go -n 2 -N 4 -s 1 -S 4 & 

start cmd /k go run main.go -n 3 -N 4 -s 1 -S 4 & 

start cmd /k go run main.go -n 0 -N 4 -s 2 -S 4 & 

start cmd /k go run main.go -n 1 -N 4 -s 2 -S 4 & 

start cmd /k go run main.go -n 2 -N 4 -s 2 -S 4 & 

start cmd /k go run main.go -n 3 -N 4 -s 2 -S 4 & 

start cmd /k go run main.go -n 0 -N 4 -s 3 -S 4 & 

start cmd /k go run main.go -n 1 -N 4 -s 3 -S 4 & 

start cmd /k go run main.go -n 2 -N 4 -s 3 -S 4 & 

start cmd /k go run main.go -n 3 -N 4 -s 3 -S 4 & 

start cmd /k go run main.go -c -N 4 -S 4 & 

