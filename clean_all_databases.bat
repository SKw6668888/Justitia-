@echo off
chcp 65001 >nul
echo ========================================
echo   清理所有实验数据的工具脚本
echo ========================================
echo.
echo 警告：此脚本将删除以下目录中的 database 文件夹：
echo   - expTest_Lagrangian_Alpha0.001/database
echo   - expTest_Lagrangian_Alpha0.01/database
echo   - expTest_Lagrangian_Alpha0.1/database
echo   - expTest_PID/database
echo   - expTest_R0/database
echo   - expTest_R_1ETH/database
echo   - expTest_R_EA_EB/database
echo   - expTest_R_EB/database
echo   - expTest_monoxide/database
echo.
echo 这将确保下次实验从 Epoch 0 开始
echo.
pause

REM 删除所有实验文件夹中的 database
if exist "expTest_Lagrangian_Alpha0.001\database" (
    echo 删除 expTest_Lagrangian_Alpha0.001\database...
    rd /s /q "expTest_Lagrangian_Alpha0.001\database"
)

if exist "expTest_Lagrangian_Alpha0.01\database" (
    echo 删除 expTest_Lagrangian_Alpha0.01\database...
    rd /s /q "expTest_Lagrangian_Alpha0.01\database"
)

if exist "expTest_Lagrangian_Alpha0.1\database" (
    echo 删除 expTest_Lagrangian_Alpha0.1\database...
    rd /s /q "expTest_Lagrangian_Alpha0.1\database"
)

if exist "expTest_PID\database" (
    echo 删除 expTest_PID\database...
    rd /s /q "expTest_PID\database"
)

if exist "expTest_R0\database" (
    echo 删除 expTest_R0\database...
    rd /s /q "expTest_R0\database"
)

if exist "expTest_R_1ETH\database" (
    echo 删除 expTest_R_1ETH\database...
    rd /s /q "expTest_R_1ETH\database"
)

if exist "expTest_R_EA_EB\database" (
    echo 删除 expTest_R_EA_EB\database...
    rd /s /q "expTest_R_EA_EB\database"
)

if exist "expTest_R_EB\database" (
    echo 删除 expTest_R_EB\database...
    rd /s /q "expTest_R_EB\database"
)

if exist "expTest_monoxide\database" (
    echo 删除 expTest_monoxide\database...
    rd /s /q "expTest_monoxide\database"
)

if exist "expTest\database" (
    echo 删除 expTest\database...
    rd /s /q "expTest\database"
)

echo.
echo ========================================
echo   数据库清理完成！
echo ========================================
echo.
echo 下次运行实验将从 Epoch 0 开始
echo.
pause
