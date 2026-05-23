@echo off
chcp 65001 >nul 2>&1
title 导出本地 MySQL 数据到 Docker

echo ============================================
echo   导出本地 MySQL 数据 → docker/data.sql
echo ============================================
echo.

where mysqldump >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 mysqldump 命令
    echo 请确保 MySQL 已安装并添加到系统 PATH
    echo.
    echo 尝试常见路径...
    set "MYSQL_PATH="
    for %%p in (
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
        "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe"
        "C:\xampp\mysql\bin\mysqldump.exe"
        "C:\phpstudy_pro\Extensions\MySQL8.0.12\bin\mysqldump.exe"
    ) do (
        if exist %%p (
            echo 找到: %%p
            set "MYSQL_PATH=%%p"
        )
    )
    if not defined MYSQL_PATH (
        echo 未找到 mysqldump，请手动指定路径
        pause
        exit /b 1
    )
)

echo 正在导出 fraudlens 数据库...
echo.

set MYSQL_PWD=20051223

if defined MYSQL_PATH (
    "%MYSQL_PATH%" --host=localhost --port=3306 --user=root --routines --triggers --add-drop-table --complete-insert --skip-extended-insert fraudlens > docker\data.sql 2>nul
) else (
    mysqldump --host=localhost --port=3306 --user=root --routines --triggers --add-drop-table --complete-insert --skip-extended-insert fraudlens > docker\data.sql 2>nul
)

if %errorlevel% neq 0 (
    echo.
    echo [错误] 导出失败，尝试使用 Python 方式导出...
    echo.
    python -c "
import pymysql, sys, os
try:
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='20051223', database='fraudlens', charset='utf8mb4')
    cursor = conn.cursor()
    cursor.execute('SHOW TABLES')
    tables = [row[0] for row in cursor.fetchall()]
    with open('docker/data.sql', 'w', encoding='utf-8') as f:
        f.write('-- FraudLens 数据导出\n')
        f.write('SET NAMES utf8mb4;\n')
        f.write('SET CHARACTER SET utf8mb4;\n')
        f.write('SET FOREIGN_KEY_CHECKS=0;\n\n')
        for table in tables:
            cursor.execute(f'SHOW CREATE TABLE `{table}`')
            create_sql = cursor.fetchone()[1]
            f.write(f'DROP TABLE IF EXISTS `{table}`;\n')
            f.write(f'{create_sql};\n\n')
            cursor.execute(f'SELECT * FROM `{table}`')
            rows = cursor.fetchall()
            if rows:
                cols = [desc[0] for desc in cursor.description]
                col_list = ', '.join(f'`{c}`' for c in cols)
                for row in rows:
                    vals = []
                    for v in row:
                        if v is None:
                            vals.append('NULL')
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bytes):
                            vals.append(\"0x\" + v.hex())
                        else:
                            escaped = str(v).replace('\\\\', '\\\\\\\\').replace(\"'\", \"\\\\'\").replace('\\n', '\\\\n').replace('\\r', '\\\\r')
                            vals.append(f\"'{escaped}'\")
                    f.write(f'INSERT INTO `{table}` ({col_list}) VALUES ({', '.join(vals)});\n')
                f.write('\n')
        f.write('SET FOREIGN_KEY_CHECKS=1;\n')
    conn.close()
    print(f'导出完成: {len(tables)} 张表')
except Exception as e:
    print(f'导出失败: {e}')
    sys.exit(1)
"
    if %errorlevel% neq 0 (
        echo [错误] Python 导出也失败了
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo   导出成功！文件: docker\data.sql
echo ============================================
echo.
echo 下次 docker-compose up 时会自动导入此数据
echo.
pause
