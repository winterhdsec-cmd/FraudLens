@echo off
rem ============================================================
rem   FraudLens 民警单机版 · 停止服务
rem   - 结束 FraudLens 后端进程与内置 Redis（若由本系统拉起）
rem   ============================================================
title FraudLens 停止
echo 正在停止 FraudLens 服务...

rem 关闭后端 uvicorn 进程
taskkill /FI "WINDOWTITLE eq FraudLens-后端服务*" /F /T >nul 2>&1
wmic process where "commandline like '%%uvicorn main:app%%'" call terminate >nul 2>&1

rem 关闭内置 Redis（仅当由 vendor 拉起时）
wmic process where "commandline like '%%backend\\vendor\\redis%%'" call terminate >nul 2>&1

timeout /t 2 /nobreak >nul
echo 服务已停止。如需再次启动，运行 start_police.bat。
pause