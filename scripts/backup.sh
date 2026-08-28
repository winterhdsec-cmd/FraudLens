#!/usr/bin/env bash
#
# FraudLens — 备份与恢复演练脚本（G12, docs/13）
#
# 设计：纯脚本，不触碰运行中的服务进程；经 docker exec 直连容器，
# 无需宿主机安装 mysql/redis 客户端。
#
# 用法（在仓库根目录执行）：
#   bash scripts/backup.sh
#
# 产出：
#   backups/mysql/fraudlens_YYYYMMDD_HHMMSS.sql   （mysqldump 全量）
#   backups/redis/dump_YYYYMMDD_HHMMSS.rdb       （SAVE 后拷贝）
#
# RTO / RPO（按试点 SLA 填，下面为占位默认值）：
#   RPO ≈ 最后一份成功备份的时刻（当前为手动/定时触发，未自动）
#   RTO ≈ 恢复演练实测时长（首次演练后回写此处）
#
set -euo pipefail

cd "$(dirname "$0")/.."                       # 切到仓库根
TS="$(date +%Y%m%d_%H%M%S)"
MYSQL_C="fraudlens-mysql-1"
REDIS_C="fraudlens-redis-1"
DB_NAME="${DB_NAME:-fraudlens}"
DB_PASS="${DB_PASSWORD:-20051223}"
REDIS_PASS="${REDIS_PASSWORD:-20051223}"

mkdir -p backups/mysql backups/redis

echo "[backup] 开始 @ $TS"

# ── MySQL 全量 dump（含 --single-transaction 一致性） ──
echo "[backup] mysqldump $DB_NAME ..."
docker exec "$MYSQL_C" \
  mysqldump -uroot -p"$DB_PASS" --single-transaction --routines --events "$DB_NAME" \
  > "backups/mysql/${DB_NAME}_${TS}.sql"
echo "[backup]   -> backups/mysql/${DB_NAME}_${TS}.sql ($(wc -c < "backups/mysql/${DB_NAME}_${TS}.sql") bytes)"

# ── Redis 落盘（SAVE 阻塞式 RDB）+ 拷贝 ──
echo "[backup] redis SAVE ..."
docker exec "$REDIS_C" redis-cli -a "$REDIS_PASS" SAVE >/dev/null 2>&1 || true
docker cp "$REDIS_C":/data/dump.rdb "backups/redis/dump_${TS}.rdb" 2>/dev/null \
  && echo "[backup]   -> backups/redis/dump_${TS}.rdb" \
  || echo "[backup]   (redis 未生成 dump.rdb，跳过)"

# ── 清理：仅保留最近 14 份，避免无限增长 ──
echo "[backup] 清理旧备份（保留最近 14 份）..."
ls -1t backups/mysql/*.sql 2>/dev/null | tail -n +15 | xargs -r rm -f
ls -1t backups/redis/*.rdb 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "[backup] 完成。"
echo "[backup] 恢复演练步骤见 scripts/restore.md（建议每季度至少一次）。"
