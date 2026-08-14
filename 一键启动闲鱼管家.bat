@echo off
chcp 65001 >nul
title 闲鱼超级管家一键启动器
echo ========================================================
echo               正在启动 闲鱼超级管家...
echo ========================================================

cd /d "%~dp0"

echo [1/4] 启动 Web API 后台服务 (端口 8089)...
start "1-BackendWeb(8089)" cmd /k "cd /d "%~dp0backend-web" && set PYTHONUTF8=1 && "C:\Program Files\Python311\python.exe" main.py"

timeout /t 2 >nul

echo [2/4] 启动 WebSocket 消息发货服务 (端口 8090)...
start "2-WebSocket(8090)" cmd /k "cd /d "%~dp0websocket" && set PYTHONUTF8=1 && "C:\Program Files\Python311\python.exe" main.py"

timeout /t 2 >nul

echo [3/4] 启动 Scheduler 定时调度服务 (端口 8091)...
start "3-Scheduler(8091)" cmd /k "cd /d "%~dp0scheduler" && set PYTHONUTF8=1 && "C:\Program Files\Python311\python.exe" main.py"

timeout /t 2 >nul

echo [4/4] 启动前端网页界面 (端口 9000)...
start "4-Frontend(9000)" cmd /k "cd /d "%~dp0frontend" && npx vite --host 0.0.0.0 --port 9000"

echo ========================================================
echo 全部 4 个核心服务已在后台启动！
echo 请打开浏览器访问：http://localhost:9000
echo ========================================================
pause
