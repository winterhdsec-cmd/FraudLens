@echo off
title Import Data to Docker MySQL

echo ============================================
echo   Import Data to Docker MySQL
echo ============================================
echo.

if not exist docker\data.sql (
    echo [ERROR] docker\data.sql not found
    echo Please run docker\export-data.bat first
    pause
    exit /b 1
)

echo Checking Docker status...
docker-compose ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not running. Please run start.bat first
    pause
    exit /b 1
)

echo.
echo Importing data...
docker-compose exec -T mysql mysql -uroot -p20051223 fraudlens < docker\data.sql

if %errorlevel% neq 0 (
    echo [ERROR] Import failed
    pause
    exit /b 1
)

echo.
echo Import success! Restarting backend...
docker-compose restart backend
echo.
pause
