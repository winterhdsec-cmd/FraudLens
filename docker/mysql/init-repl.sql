-- G13 主库初始化：创建专用于复制的账号（仅主库挂载本文件）
-- 使用 mysql_native_password，避免 MySQL 8.0 默认的 caching_sha2_password 在无 SSL 复制时要求安全连接而失败
CREATE USER IF NOT EXISTS 'repl'@'%' IDENTIFIED WITH mysql_native_password BY 'repl_pass_2024';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
