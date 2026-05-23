@echo off
chcp 65001 >nul 2>&1
title 导入数据到 Docker MySQL

echo ============================================
echo   导入数据到 Docker MySQL
echo ============================================
echo.

if not exist docker\data.sql (
    echo [错误] docker\data.sql 不存在
    echo 请先运行 docker\export-data.bat 导出数据
    pause
    exit /b 1
)

echo 正在检查 Docker 服务状态...
docker-compose ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Docker 服务未启动，请先运行 start.bat
    pause
    exit /b 1
)

echo.
echo 正在导入数据到 Docker MySQL...
docker-compose exec -T mysql mysql -uroot -p20051223 fraudlens < docker\data.sql

if %errorlevel% neq 0 (
    echo [错误] 导入失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   数据导入成功！
echo ============================================
echo.
echo 重启后端以刷新缓存...
docker-compose restart backend
echo.
pause
