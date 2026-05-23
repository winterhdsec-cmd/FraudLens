@echo off
chcp 65001 >nul 2>&1
title FraudLens Docker 部署

echo ============================================
echo   FraudLens Docker 一键部署
echo ============================================
echo.

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Docker，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    docker-compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到 docker-compose
        pause
        exit /b 1
    )
)

if not exist .env (
    echo [1/5] 创建 .env 配置文件...
    copy .env.docker .env
    echo.
    echo [重要] 请编辑 .env 文件，填入你的 DEEPSEEK_API_KEY
    echo.
    notepad .env
    echo 配置文件已保存，继续部署...
) else (
    echo [1/5] .env 配置文件已存在，跳过
)

echo.
echo [2/5] 构建 Docker 镜像（首次可能需要较长时间）...
docker-compose build --no-cache backend
if %errorlevel% neq 0 (
    echo [错误] 镜像构建失败
    pause
    exit /b 1
)

echo.
echo [3/5] 启动所有服务...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [错误] 服务启动失败
    pause
    exit /b 1
)

echo.
echo [4/5] 等待服务就绪...
timeout /t 20 /nobreak >nul

echo.
echo [5/5] 检查 BGE 模型...
if exist "backend\bge-large-zh-v1.5\pytorch_model.bin" (
    echo   检测到本地 BGE 模型，正在复制到容器...
    for /f "tokens=*" %%i in ('docker-compose ps -q backend') do (
        docker cp "backend\bge-large-zh-v1.5\." %%i:/app/bge-large-zh-v1.5/
    )
    echo   BGE 模型复制完成！
    echo   重启后端以加载模型...
    docker-compose restart backend
    timeout /t 10 /nobreak >nul
) else (
    echo   [跳过] 本地未找到 BGE 模型文件
    echo   如需使用聚类分析功能，请手动将模型复制到容器：
    echo   docker cp ./backend/bge-large-zh-v1.5/. ^<容器ID^>:/app/bge-large-zh-v1.5/
)

echo.
echo ============================================
echo   部署完成！
echo ============================================
echo.
echo   访问地址: http://localhost
echo   默认账号: admin / admin123
echo.
echo   MySQL:  localhost:3307 (root / .env中的密码)
echo   Redis:  localhost:6380
echo   后端API: localhost:5003
echo.
echo   常用命令:
echo     查看日志:   docker-compose logs -f
echo     停止服务:   stop.bat 或 docker-compose down
echo     重启服务:   docker-compose restart
echo     注入种子:   docker-compose run --rm seed
echo ============================================
echo.
pause
