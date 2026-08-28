#!/bin/sh
# G14 Redis Sentinel 入口：按环境变量生成配置后启动 sentinel
# 监控名为 mymaster 的主节点（compose 中 redis 服务），quorum=2（3 哨兵）
set -e

PASS="${REDIS_PASSWORD:-20051223}"

cat > /data/sentinel.conf <<EOF
port 26379
dir /data
# 允许哨兵按主机名解析主节点（Docker 网络 DNS），解析不到时重试而非直接 FATAL
sentinel resolve-hostnames yes
# 哨兵之间以 IP 互相宣告（稳定，避免按主机名反复重解析导致事件风暴触发 TILT）
sentinel announce-hostnames no
sentinel monitor mymaster redis 6379 2
sentinel auth-pass mymaster ${PASS}
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
EOF

exec redis-server /data/sentinel.conf --sentinel
