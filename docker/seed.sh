#!/bin/bash
set -e

echo "============================================"
echo "  FraudLens Seed Data Injection"
echo "============================================"

echo "Waiting for MySQL..."
while ! python -c "
import pymysql, os
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST', 'mysql'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'fraudlens'),
        connect_timeout=3
    )
    conn.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
    sleep 2
done
echo "MySQL is ready!"

echo "Injecting seed data..."
python seed_demo.py
echo "Seed data injection complete!"
