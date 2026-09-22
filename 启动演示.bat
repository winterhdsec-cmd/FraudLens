@echo off
chcp 65001 >nul
rem ============================================================
rem   FraudLens 演示一键启动
rem
rem   特点：
rem   - 用 start 开**独立窗口**，进程不隶属于任何调用方，
rem     关掉本窗口也不影响服务
rem   - 启动前**强制释放 5003 / 5173**（清掉任何旧实例），
rem     保证演示用的永远是本次启动的进程 ——
rem     避免复用"别的进程"（如 AI 会话里起的、会被回收的那种）
rem   - 等服务真正就绪后才打开浏览器（最多等 90 秒）
rem   - 结束演示：关掉弹出的两个黑色窗口即可
rem ============================================================
setlocal
set "ROOT=%~dp0"
title FraudLens 演示启动

echo ============================================================
echo   FraudLens 反诈研判系统 · 演示启动
echo ============================================================
echo.

rem ---------- 前置检查 ----------
if not exist "%ROOT%backend\venv-full\Scripts\python.exe" (
    echo [错误] 找不到后端 Python 环境：
    echo        %ROOT%backend\venv-full\Scripts\python.exe
    echo.
    pause
    exit /b 1
)
if not exist "%ROOT%frontend\node_modules" (
    echo [错误] 找不到前端依赖目录：
    echo        %ROOT%frontend\node_modules
    echo        请先在 frontend 目录执行 npm install
    echo.
    pause
    exit /b 1
)

rem ---------- 释放端口（清掉旧实例）----------
echo [1/4] 清理旧实例（释放 5003 / 5173）...
call :killport 5003
call :killport 5173
timeout /t 2 /nobreak >nul

rem ---------- 后端 ----------
echo [2/4] 启动后端  http://127.0.0.1:5003
start "FraudLens-Backend" cmd /k "cd /d %ROOT%backend && venv-full\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 5003"

echo [3/4] 启动前端  http://127.0.0.1:5173
start "FraudLens-Frontend" cmd /k "cd /d %ROOT%frontend && npx vite --port 5173 --host 127.0.0.1"

rem ---------- 等待就绪 ----------
echo [4/4] 等待服务就绪（首次启动后端约 10-25 秒，最多等 90 秒）...
set /a _n=0
:waitloop
timeout /t 3 /nobreak >nul
set /a _n+=3
set "_be="
set "_fe="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5003 " ^| findstr LISTENING') do set "_be=1"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr LISTENING') do set "_fe=1"
if not defined _be if not defined _fe if %_n% lss 90 goto waitloop
if not defined _be if %_n% lss 90 goto waitloop
if not defined _fe if %_n% lss 90 goto waitloop

echo.
echo ============================================================
if defined _be (echo   后端 : 已就绪 ^(5003^)) else (echo   后端 : 未就绪 —— 请看 "FraudLens-Backend" 窗口的报错)
if defined _fe (echo   前端 : 已就绪 ^(5173^)) else (echo   前端 : 未就绪 —— 请看 "FraudLens-Frontend" 窗口的报错)
echo.
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

goto :eof

rem ---------- 子过程：按端口杀进程 ----------
:killport
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%~1 " ^| findstr LISTENING') do (
    echo        释放端口 %~1 ^(PID %%p^)
    taskkill /F /PID %%p >nul 2>&1
)
exit /b 0
