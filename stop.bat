@echo off
chcp 65001 >nul 2>&1
title FraudLens Docker 停止

echo 正在停止 FraudLens 所有服务...
docker-compose down
echo.
echo 所有服务已停止
pause
