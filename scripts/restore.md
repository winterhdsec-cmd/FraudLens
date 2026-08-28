# FraudLens 备份与恢复演练（G12, docs/13）

> 脚本：`scripts/backup.sh`（经 `docker exec` 直连容器，宿主机无需安装 mysql/redis 客户端）。
> 备份产出：`backups/mysql/fraudlens_*.sql` + `backups/redis/dump_*.rdb`。

## 1. 备份（建议每日定时 / 每次重大操作前）

```bash
bash scripts/backup.sh
```

- MySQL：全量 `mysqldump --single-transaction`（一致性快照，不锁表）。
- Redis：`SAVE` 阻塞式落盘后拷贝 `dump.rdb`。
- 自动保留最近 14 份，超出清理。

## 2. 恢复演练（建议每季度至少一次，回填下方 RTO/RPO）

### 2.1 MySQL 恢复

```bash
# 1) 停止写入（或进维护模式）
# 2) 恢复指定全量备份
docker exec -i fraudlens-mysql-1 mysql -uroot -p"$DB_PASSWORD" fraudlens \
  < backups/mysql/fraudlens_YYYYMMDD_HHMMSS.sql
# 3) 校验
docker exec fraudlens-mysql-1 mysql -uroot -p"$DB_PASSWORD" -e "SELECT COUNT(*) FROM cases;" fraudlens
```

### 2.2 Redis 恢复

```bash
# 1) 停止 redis 容器
docker stop fraudlens-redis-1
# 2) 用备份覆盖数据卷
docker cp backups/redis/dump_YYYYMMDD_HHMMSS.rdb fraudlens-redis-1:/data/dump.rdb
# 3) 重启（加载 dump.rdb）
docker start fraudlens-redis-1
```

## 3. RTO / RPO（按试点 SLA 回填）

| 指标 | 定义 | 当前值（首次演练后回填） |
|---|---|---|
| **RPO** | 最多丢失的数据时长 | 上次成功备份时刻至今（手动/定时触发） |
| **RTO** | 从故障到恢复可用 | 待演练实测（目标 < 30 min） |

> 注：当前为单副本 + 手动备份，未启用 MySQL binlog 增量 + Redis AOF 持久化增强。
> 启用 binlog：`mysql` 服务加 `--log-bin`；Redis 改 `appendonly yes`。详见 Wave 3（G12 强化）。
