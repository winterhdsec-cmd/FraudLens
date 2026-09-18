@echo off
rem ============================================================
rem   FraudLens 民警电脑·一键单机启动（免 Docker）
rem   - 前端已由后端托管（backend/static，同源 /api 直达，免 nginx）
rem   - 内置便携 Redis 自动拉起（backend/vendor/redis）
rem   - 唯一硬依赖：MySQL（本机/便携皆可，脚本会自动检测引导）
rem   - 全程无外网依赖：BGE/EasyOCR 模型与全部依赖随包内置
rem   ============================================================
setlocal enabledelayedexpansion
title FraudLens 单机版

cd /d "%~dp0"

echo ============================================================
echo   FraudLens 反诈研判系统 · 民警单机版
echo ============================================================
echo.

rem ---- 1. 定位入口目录 ----
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "PY=%BACKEND%\venv-full\Scripts\python.exe"

rem ---- 2. 校验 Python 环境 ----
if not exist "%PY%" (
    echo [错误] 未找到 Python 环境（backend\venv-full）。
    echo        请先在开发机用如下命令生成完整环境：
    echo        "C:\Users\hd\AppData\Local\Programs\Python\Python310\python" -m venv --system-site-packages backend\venv-full
    echo        并将整个 FraudLens 目录拷到民警电脑。
    pause
    exit /b 1
)

rem ---- 3. 校验前端产物已内置 ----
if not exist "%BACKEND%\static\index.html" (
    echo [自动] 检测到前端产物缺失，正在从 frontend\dist 内置...
    if exist "%ROOT%frontend\dist\index.html" (
        mkdir "%BACKEND%\static" 2>nul
        xcopy "%ROOT%frontend\dist\*" "%BACKEND%\static\" /E /I /Y /Q >nul
        echo [完成] 前端已内置到 backend\static。
    ) else (
        echo [错误] 未找到前端构建产物（frontend\dist 或 backend\static）。
        echo        请先在开发机执行 frontend 下 npm run build 后再拷贝。
        pause
        exit /b 1
    )
)

rem ---- 4. 校验 MySQL 是否可达 ----
set "DB_OK="
if exist "%ProgramFiles%\MySQL\MySQL Server 8.0\bin\mysql.exe" set "DB_OK=1"
if exist "%ProgramFiles(x86)%\MySQL\MySQL Server 8.0\bin\mysql.exe" set "DB_OK=1"
if defined DB_OK (
    echo [检测] 已检测到本机 MySQL 8.0。
) else (
    echo [提示] 未检测到本机 MySQL。本系统需要 MySQL 存储案件/账户数据。
    echo        两种选择：
    echo          1) 使用便携版 MySQL（推荐，免安装）：将 MySQL zip 解压到 backend\vendor\mysql
    echo          2) 安装 MySQL Community 8.0 后重试
    echo ------------------------------------------------------------
    echo        尝试连接默认配置 MySQL (localhost:3306, root/20051223)...
    if exist "%BACKEND%\vendor\mysql\bin\mysql.exe" goto :mysql_ok
    echo        未配置便携 MySQL，等待网络 MySQL...
    echo        （若你的 MySQL 已安装在其他端口/密码，请先编辑 backend\key.env）
    echo.
)

:mysql_ok
rem ---- 4.5 确保数据库存在（MySQL 无预建库时自动建库，幂等） ----
echo [检查] 正在确保数据库 fraudlens 存在...
"%PY%" "%BACKEND%\scripts\ensure_db.py" --config "%BACKEND%\key.env"
if errorlevel 1 (
    echo   [警告] 数据库检查未通过，后端可能无法存储数据。请查看上方原因。
    echo          仍将继续尝试启动，如登录/查询报数据库错误请回头处理 MySQL。
)

rem ---- 5. 启动内置 Redis 已由后端自动拉起，此处直接启动后端 ----
echo ============================================================
echo   正在启动后端服务（首次加载 BGE 大模型约需 30-60 秒）...
echo ============================================================
echo.

rem 生产单机默认关闭云端 LLM（数据不出域），如需演示云端智能可改为 0
set "DISABLE_CLOUD_LLM=1"
set "REDIS_AUTOSTART=1"
set "ENV=production"

echo 启动中，日志写入 backend\server.log
echo 访问地址： http://localhost:5003
echo 账号： admin / admin123 （首次请改密）
echo.
echo 启动完成前请勿关闭本窗口。现开始启动服务...
echo.

start "FraudLens-后端服务" /min "%PY%" -m uvicorn main:app --host 0.0.0.0 --port 5003 --app-dir "%BACKEND%"

rem ---- 6. 等待健康检查 ----
echo 等待服务就绪（首次 BGE 加载较慢）...
set "READY="
for /l %%i in (1,1,40) do (
    timeout /t 5 /nobreak >nul
    curl -s -o nul -w "%%{http_code}" http://127.0.0.1:5003/health 2>nul | findstr "200" >nul && (set READY=1 & goto :ready_yes)
)
echo [警告] 服务就绪检测超时，请查看 backend\server.log 确认是否仍在加载。
goto :open
:ready_yes
echo [就绪] FraudLens 已启动成功！

:open
echo.
echo ============================================================
echo   正在打开浏览器...
echo ============================================================
start http://localhost:5003

echo.
echo 提示：关闭服务请关闭"FraudLens-后端服务"窗口；
echo            或在本目录运行 stop_police.bat。
echo.
pause
endlocal