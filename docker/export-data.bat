@echo off
title Export MySQL Data

echo ============================================
echo   Export Local MySQL Data to docker/data.sql
echo ============================================
echo.

python -c "import pymysql, sys, os; os.chdir(r'e:\FraudLens'); conn = pymysql.connect(host='localhost', port=3306, user='root', password='20051223', database='fraudlens', charset='utf8mb4'); cursor = conn.cursor(); cursor.execute('SHOW TABLES'); tables = [row[0] for row in cursor.fetchall()]; print(f'Found {len(tables)} tables:'); f = open('docker/data.sql', 'w', encoding='utf-8'); f.write('-- FraudLens data export\n\nSET NAMES utf8mb4;\nSET CHARACTER SET utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n'); [None for t in tables]; [f.write(f'DROP TABLE IF EXISTS `{t}`;\n') or f.write(cursor.execute(f'SHOW CREATE TABLE `{t}`') and cursor.fetchone()[1] + ';\n\n') for t in tables]; f.write('SET FOREIGN_KEY_CHECKS=1;\n'); f.close(); conn.close(); print('Export done!')"

if %errorlevel% neq 0 (
    echo [ERROR] Export failed. Trying alternative method...
    cd /d e:\FraudLens
    python -c "import pymysql,sys,os;os.chdir('e:\\FraudLens');conn=pymysql.connect(host='localhost',port=3306,user='root',password='20051223',database='fraudlens',charset='utf8mb4');cursor=conn.cursor();cursor.execute('SHOW TABLES');tables=[row[0] for row in cursor.fetchall()];print(f'Found {len(tables)} tables');f=open('docker/data.sql','w',encoding='utf-8');f.write('SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n');exec(\"\"\"for t in tables:\n cursor.execute(f'SELECT COUNT(*) FROM `{t}`')\n count=cursor.fetchone()[0]\n print(f'  {t}: {count} rows')\n if count==0: continue\n cursor.execute(f'SHOW CREATE TABLE `{t}`')\n create_sql=cursor.fetchone()[1]\n f.write(f'DROP TABLE IF EXISTS `{t}`;\\n{create_sql};\\n\\n')\n cursor.execute(f'SELECT * FROM `{t}`')\n rows=cursor.fetchall()\n if rows:\n  cols=[d[0] for d in cursor.description]\n  col_list=', '.join(f'`{c}`' for c in cols)\n  for row in rows:\n   vals=[]\n   for v in row:\n    if v is None: vals.append('NULL')\n    elif isinstance(v,bool): vals.append('1' if v else '0')\n    elif isinstance(v,(int,float)): vals.append(str(v))\n    elif isinstance(v,bytes): vals.append(\"X'\"+v.hex()+\"'\")\n    else:\n     s=str(v).replace(chr(92),chr(92)+chr(92)).replace(\"'\",chr(92)+\"'\").replace(chr(10),chr(92)+'n').replace(chr(13),chr(92)+'r')\n     vals.append(f\"'{s}'\")\n   f.write(f'INSERT INTO `{t}` ({col_list}) VALUES ({\", \".join(vals)});\\n')\n  f.write('\\n')\n\"\"\");f.write('SET FOREIGN_KEY_CHECKS=1;\\n');f.close();conn.close();print('Export done!')"
)

echo.
pause
