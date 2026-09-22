@echo off
chcp 65001 >nul
rem ============================================================
rem   FraudLens 演示一键启动
rem
rem   特点：
rem   - 用 start 开**独立窗口**，进程不隶属于任何调用方，
rem     关掉本窗口也不影响服务
rem   - 启动前检查端口，已占用则跳过（避免重复启动报错）
rem   - 自动打开浏览器并显示登录信息
rem   - 结束演示：直接关掉弹出的两个黑色窗口即可
rem ============================================================
setlocal
set "ROOT=%~dp0"
title FraudLens 演示启动

echo ============================================================
echo   FraudLens 反诈研判系统 · 演示启动
echo ============================================================
echo.

rem ---------- 后端 ----------
netstat -ano | findstr ":5003 " | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
    echo [跳过] 后端已在运行（5003 已监听）
) else (
    echo [1/3] 启动后端  http://127.0.0.1:5003
    start "FraudLens-Backend" cmd /k "cd /d %ROOT%backend && venv-full\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 5003"
)

rem ---------- 前端 ----------
netstat -ano | findstr ":5173 " | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
    echo [跳过] 前端已在运行（5173 已监听）
) else (
    echo [2/3] 启动前端  http://127.0.0.1:5173
    start "FraudLens-Frontend" cmd /k "cd /d %ROOT%frontend && npx vite --port 5173 --host 127.0.0.1"
)

echo [3/3] 等待服务就绪（首次启动后端约需 10-20 秒）...
timeout /t 14 /nobreak >nul

echo.
echo ============================================================
echo   登录地址 : http://127.0.0.1:5173
echo   账号密码 : admin / admin123
echo.
echo   演示期间请不要关闭那两个黑色窗口（标题分别为
echo   FraudLens-Backend / FraudLens-Frontend）。
echo   结束演示后直接关掉它们即可。
echo ============================================================
echo.
start "" http://127.0.0.1:5173
echo 浏览器已打开。按任意键关闭本窗口（不影响服务运行）。
pause >nul
