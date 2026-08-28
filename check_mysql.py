# -*- coding: utf-8 -*-
"""检查 MySQL 连接状态和慢查询"""
import pymysql

pw = [l.split('=', 1)[1].strip() for l in open('.env', encoding='utf-8') if l.startswith('DB_PASSWORD=')][0]
conn = pymysql.connect(host='localhost', user='root', password=pw, database='fraudlens', connect_timeout=5)
cur = conn.cursor()
cur.execute("SHOW STATUS LIKE 'Threads_connected'")
print('连接数:', cur.fetchone())
cur.execute("SHOW STATUS LIKE 'Max_used_connections'")
print('峰值连接:', cur.fetchone())
cur.execute('SHOW FULL PROCESSLIST')
rows = cur.fetchall()
print('当前进程:')
for r in rows:
    print(' ', r[0], r[4], r[5], (r[7] or '')[:80])
conn.close()
