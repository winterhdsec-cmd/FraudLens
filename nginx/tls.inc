# G1 全链路 TLS 占位文件（默认空 = 仅 HTTP 明文）。
# 运行 `bash scripts/gen_tls.sh` 生成自签证书并写入 443 ssl server 块。
# 删除本文件内容并 `docker compose exec nginx nginx -s reload` 可回退到纯 HTTP。
