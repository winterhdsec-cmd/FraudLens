@echo off
rem ============================================
rem   FraudLens 本地零依赖启动（Windows）
rem   - 内置 Redis：REDIS_AUTOSTART=1 时自动拉起 vendor/redis
rem   - 完整环境：使用 venv-full（系统 Python 3.10 + 全量深度学习依赖）
rem   需要 Docker 的生产部署请用 start.bat
rem ============================================
title FraudLens Local Dev

cd /d "%~dp0"

if not exist backend\venv-full\Scripts\python.exe (
    echo [ERROR] venv-full not found.
    echo   Run: "C:\Users\hd\AppData\Local\Programs\Python\Python310\python" -m venv --system-site-packages backend\venv-full
    pause
    exit /b 1
)

echo [1/2] Starting backend with full environment (BGE/HDBSCAN/OCR enabled)...
start "FraudLens-Backend" cmd /k "cd /d %~dp0backend && venv-full\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 5003"

echo [2/2] Starting frontend dev server...
start "FraudLens-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo   Backend:  http://localhost:5003/docs
echo   Frontend: http://localhost:5173
echo   Login:    admin / admin123
echo.
pause
