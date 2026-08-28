#!/usr/bin/env bash
# G1 全链路 TLS：生成自签证书并写入 nginx/tls.inc（443 ssl server）
# 用法：bash scripts/gen_tls.sh
# 前置：openssl 已安装；项目根下存在 nginx/ 与 docker-compose.yml。
set -euo pipefail
cd "$(dirname "$0")/.."   # 切到项目根

mkdir -p nginx/certs

CERT=nginx/certs/fraudlens.crt
KEY=nginx/certs/fraudlens.key

if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
  echo "[gen_tls] 生成自签证书 (有效期 825 天) ..."
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY" -out "$CERT" -days 825 \
    -subj "/CN=fraudlens.local" 2>/dev/null
else
  echo "[gen_tls] 证书已存在，跳过生成"
fi

echo "[gen_tls] 写入 nginx/tls.inc (443 ssl server) ..."
cat > nginx/tls.inc <<'INC'
# ── G1 全链路 TLS（由 scripts/gen_tls.sh 生成；清空本文件并 reload 可回退 80 明文） ──
server {
    listen 443 ssl;
    http2 on;
    server_name _;

    ssl_certificate     /etc/nginx/certs/fraudlens.crt;
    ssl_certificate_key /etc/nginx/certs/fraudlens.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;

    client_max_body_size 50m;

    location /api/ {
        proxy_pass http://backend:5003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
    }

    location /agent-analyze {
        proxy_pass http://backend:5003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 50m;
    }

    location /ws {
        proxy_pass http://backend:5003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
INC

# 可选：强制 80→443 重定向（严格模式）。
# 默认主 server 仍明文服务；如需强制 HTTPS，取消下一行注释后运行：
#   sed -i 's/^\(\s*\)listen 80;/\1listen 80;\n\1return 301 https:\/\/$host$request_uri;/' nginx.conf
#   docker compose exec nginx nginx -s reload

echo "[gen_tls] 完成。使配置生效："
echo "    docker compose up -d nginx      # 或 docker compose exec nginx nginx -s reload"
echo "    部署环境设置 TLS_ENABLED=1（启用 HSTS 响应头，见 backend/main.py）。"
