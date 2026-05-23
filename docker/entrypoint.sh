#!/bin/bash
set -e

echo "============================================"
echo "  FraudLens Backend Entrypoint"
echo "============================================"

echo "[1/4] Waiting for MySQL..."
for i in $(seq 1 60); do
    if python -c "
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
" 2>/dev/null; then
        echo "  MySQL is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "  [ERROR] MySQL timeout after 120s"
        exit 1
    fi
    sleep 2
done

echo "[2/4] Waiting for Redis..."
for i in $(seq 1 30); do
    if python -c "
import redis as r, os
try:
    client = r.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD', '') or None,
        socket_connect_timeout=3
    )
    client.ping()
    client.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
        echo "  Redis is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  [WARN] Redis timeout, continuing without Redis..."
        break
    fi
    sleep 2
done

echo "[3/4] Checking BGE model..."
if [ -f "/app/bge-large-zh-v1.5/config.json" ] && [ -f "/app/bge-large-zh-v1.5/pytorch_model.bin" ]; then
    echo "  BGE model found!"
else
    echo "  [WARN] BGE model not found in volume."
    echo "  To load the model, run:"
    echo "    docker-compose exec backend python -c \""
    echo "import shutil, os"
    echo "src = '/app/bge-large-zh-v1.5-local'"
    echo "dst = '/app/bge-large-zh-v1.5'"
    echo "if os.path.exists(src):"
    echo "    for f in os.listdir(src):"
    echo "        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))"
    echo "    print('Model copied!')"
    echo "else:"
    echo "    print('Local model not found, downloading...')"
    echo "\""
    echo ""
    echo "  Or copy from host:"
    echo "    docker cp ./backend/bge-large-zh-v1.5/. <backend_container>:/app/bge-large-zh-v1.5/"
    echo ""
fi

echo "[4/4] Starting FraudLens backend..."
exec python main.py
