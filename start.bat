@echo off
title FraudLens Docker Deploy

echo ============================================
echo   FraudLens Docker Deploy
echo ============================================
echo.

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    echo Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    docker-compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] docker-compose not found.
        pause
        exit /b 1
    )
)

if not exist .env (
    echo [1/6] Creating .env config file...
    copy .env.docker .env
    echo.
    echo [IMPORTANT] Please edit .env and fill in your DEEPSEEK_API_KEY
    echo.
    notepad .env
    echo Config saved, continuing...
) else (
    echo [1/6] .env already exists, skipping
)

echo.
echo [2/6] Building frontend...
cd /d "%~dp0frontend"
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Please install Node.js 18+
    echo Download: https://nodejs.org/
    pause
    exit /b 1
)
if not exist node_modules (
    echo Installing npm dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
)
echo Running npm run build...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)
cd /d "%~dp0"

echo.
echo [3/6] Copying frontend dist to static...
if exist "static" rmdir /s /q "static"
xcopy /e /i /q "frontend\dist" "static" >nul

echo.
echo [4/6] Building Docker image...
docker-compose build --no-cache backend
if %errorlevel% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo [5/6] Starting all services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Start failed
    pause
    exit /b 1
)

echo.
echo Waiting for services...
timeout /t 20 /nobreak >nul

echo.
echo [6/6] Checking BGE model...
if exist "backend\bge-large-zh-v1.5\pytorch_model.bin" (
    echo   BGE model found locally, copying to container...
    for /f "tokens=*" %%i in ('docker-compose ps -q backend 2^>nul') do (
        docker cp "backend\bge-large-zh-v1.5\." %%i:/app/bge-large-zh-v1.5/
    )
    echo   BGE model copied!
    echo   Restarting backend to load model...
    docker-compose restart backend
    timeout /t 10 /nobreak >nul
) else (
    echo   [SKIP] BGE model not found locally
    echo   To use clustering, copy model to container:
    echo   docker cp ./backend/bge-large-zh-v1.5/. CONTAINER_ID:/app/bge-large-zh-v1.5/
)

echo.
echo ============================================
echo   Deploy Complete!
echo ============================================
echo.
echo   URL:       http://localhost
echo   Account:   admin / admin123
echo.
echo   MySQL:     localhost:3307
echo   Redis:     localhost:6380
echo   Backend:   localhost:5003
echo.
echo   Commands:
echo     Logs:      docker-compose logs -f
echo     Stop:      stop.bat
echo     Restart:   docker-compose restart
echo     Seed data: docker-compose run --rm seed
echo ============================================
echo.
pause
