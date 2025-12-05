@echo off
echo ========================================
echo   Justitia 批量实验脚本
echo   依次运行 PID、拉格朗日、RL 三种模式
echo ========================================
echo.

REM 编译项目
echo ======================================
echo   编译项目...
echo ======================================
go build
if %errorlevel% neq 0 (
    echo 编译失败！请检查错误。
    pause
    exit /b %errorlevel%
)
echo 编译成功！
echo.

REM ========================================
REM 实验 1: PID 控制器模式
REM ========================================
echo.
echo ========================================
echo   实验 1/3: PID 控制器模式
echo ========================================
echo 正在配置 PID 模式...
copy /Y paramsConfig_PID.json paramsConfig.json
echo.

echo 清理旧数据...
if exist expTest_PID (
    rd /s /q expTest_PID
)
echo.

echo 启动 PID 模式实验...
echo 这将启动 4 个分片，共 16 个节点 + 1 个协调器
timeout /t 2 /nobreak >nul

start /min cmd /k go run main.go -n 0 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 0 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 1 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 2 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 3 -S 4

start /min cmd /k go run main.go -c -N 4 -S 4

echo PID 模式实验已启动！
echo 请等待实验完成（所有窗口自动关闭），然后按任意键继续...
pause
echo.

REM ========================================
REM 实验 2: 拉格朗日优化模式
REM ========================================
echo.
echo ========================================
echo   实验 2/3: 拉格朗日优化模式
echo ========================================
echo 正在配置拉格朗日模式...
copy /Y paramsConfig_Lagrangian.json paramsConfig.json
echo.

echo 清理旧数据...
if exist expTest_Lagrangian (
    rd /s /q expTest_Lagrangian
)
echo.

echo 启动拉格朗日模式实验...
timeout /t 2 /nobreak >nul

start /min cmd /k go run main.go -n 0 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 0 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 1 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 2 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 3 -S 4

start /min cmd /k go run main.go -c -N 4 -S 4

echo 拉格朗日模式实验已启动！
echo 请等待实验完成（所有窗口自动关闭），然后按任意键继续...
pause
echo.

REM ========================================
REM 实验 3: 强化学习模式
REM ========================================
echo.
echo ========================================
echo   实验 3/3: 强化学习模式
echo ========================================
echo 正在配置 RL 模式...
copy /Y paramsConfig_RL.json paramsConfig.json
echo.

echo 清理旧数据...
if exist expTest_RL (
    rd /s /q expTest_RL
)
echo.

echo 启动 RL 模式实验...
timeout /t 2 /nobreak >nul

start /min cmd /k go run main.go -n 0 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 0 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 0 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 1 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 1 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 2 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 2 -S 4

start /min cmd /k go run main.go -n 0 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 1 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 2 -N 4 -s 3 -S 4
start /min cmd /k go run main.go -n 3 -N 4 -s 3 -S 4

start /min cmd /k go run main.go -c -N 4 -S 4

echo RL 模式实验已启动！
echo 请等待实验完成（所有窗口自动关闭）...
pause
echo.

REM ========================================
REM 完成
REM ========================================
echo.
echo ========================================
echo   所有实验完成！
echo ========================================
echo.
echo 实验结果保存在以下目录：
echo   1. PID 模式:        expTest_PID/result/
echo   2. 拉格朗日模式:    expTest_Lagrangian/result/
echo   3. RL 模式:         expTest_RL/result/
echo.
echo 你可以对比这三个目录中的结果文件来分析不同模式的性能。
echo.
pause
