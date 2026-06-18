@echo off
title FraudLens Docker Deploy

echo ============================================
echo   FraudLens Docker Deploy
echo ============================================
echo.

:: Check Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    echo Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

:: Check Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

:: Check .env file
if not exist .env (
    echo [1/4] Creating .env config file...
    copy .env.docker .env >nul
    echo.
    echo [IMPORTANT] Please edit .env and fill in your DEEPSEEK_API_KEY
    echo.
    notepad .env
    echo Config saved, continuing...
) else (
    echo [1/4] .env already exists, skipping
)

:: Check if services are already running
echo.
echo [2/4] Checking service status...
docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>nul | findstr /i "fraudlens" >nul
if %errorlevel% equ 0 (
    echo   Services are already running!
    echo.
    echo   To restart, run: docker compose restart
    echo   To stop, run: stop.bat
    echo.
    goto :check_health
)

:: Build image only if not exists
echo.
echo [3/4] Building Docker image...
docker compose images fraudlens-backend 2>nul | findstr /i "fraudlens-backend" >nul
if %errorlevel% neq 0 (
    echo   Image not found, building...
    docker compose build backend
    if %errorlevel% neq 0 (
        echo [ERROR] Build failed
        pause
        exit /b 1
    )
) else (
    echo   Image already exists, skipping build
)

:: Start services
echo.
echo [4/4] Starting all services...
docker compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Start failed
    docker compose logs --tail=50
    pause
    exit /b 1
)

:check_health
echo.
echo ============================================
echo   Waiting for services to be ready...
echo ============================================

:: Wait for MySQL
echo   Checking MySQL...
set retry=0
:wait_mysql
if %retry% geq 30 (
    echo   [WARNING] MySQL health check timeout
    goto :wait_backend
)
docker compose exec -T mysql mysqladmin ping -h localhost -uroot -p20051223 >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    set /a retry+=1
    goto :wait_mysql
)
echo   MySQL is ready!

:: Wait for Backend
:wait_backend
echo   Checking Backend...
set retry=0
:wait_backend_loop
if %retry% geq 30 (
    echo   [WARNING] Backend health check timeout
    goto :copy_bge
)
docker compose exec -T backend curl -f http://localhost:5003/health >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    set /a retry+=1
    goto :wait_backend_loop
)
echo   Backend is ready!

:: Copy BGE model
:copy_bge
echo.
echo ============================================
echo   Checking BGE model...
echo ============================================
if exist "backend\bge-large-zh-v1.5\pytorch_model.bin" (
    echo   BGE model found locally
    for /f "tokens=*" %%i in ('docker compose ps -q backend 2^>nul') do set CONTAINER_ID=%%i
    if defined CONTAINER_ID (
        echo   Copying BGE model to container...
        docker cp "backend\bge-large-zh-v1.5\." %CONTAINER_ID%:/app/bge-large-zh-v1.5/ >nul 2>&1
        if %errorlevel% equ 0 (
            echo   BGE model copied successfully!
            echo   Restarting backend to load model...
            docker compose restart backend >nul 2>&1
            timeout /t 5 /nobreak >nul
        ) else (
            echo   [WARNING] Failed to copy BGE model
        )
    )
) else (
    echo   [SKIP] BGE model not found locally
    echo   To enable clustering, download BGE model and place it in:
    echo   backend\bge-large-zh-v1.5\
)

:: Show final status
echo.
echo ============================================
echo   Deploy Complete!
echo ============================================
echo.
echo   Access URL:    http://localhost
echo   Login:         admin / admin123
echo.
echo   Services:
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo.
echo   Quick Commands:
echo     View logs:     docker compose logs -f
echo     Stop:          stop.bat
echo     Restart:       docker compose restart
echo     Rebuild:       docker compose up -d --build
echo ============================================
echo.
pause
