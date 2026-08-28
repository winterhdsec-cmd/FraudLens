#!/bin/sh
# G13 从库首次初始化：等待主从两端可达后配置 GTID 自动位点的复制链路
set -e

REPL_USER='repl'
REPL_PASS='repl_pass_2024'
MASTER_HOST='mysql'
MASTER_PORT=3306

echo "[replica-init] waiting for LOCAL mysql..."
for i in $(seq 1 60); do
  if mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "[replica-init] waiting for MASTER mysql (${MASTER_HOST}:${MASTER_PORT})..."
for i in $(seq 1 60); do
  if mysql -h "${MASTER_HOST}" -P "${MASTER_PORT}" -uroot -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then break; fi
  sleep 2
done

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
STOP REPLICA;
RESET REPLICA ALL;
CHANGE MASTER TO
  MASTER_HOST='${MASTER_HOST}',
  MASTER_PORT=${MASTER_PORT},
  MASTER_USER='${REPL_USER}',
  MASTER_PASSWORD='${REPL_PASS}',
  MASTER_AUTO_POSITION=1;
START REPLICA;
SQL

echo "[replica-init] replication configured."
