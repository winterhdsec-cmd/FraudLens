"""
ensure_db.py — 单机版启动辅助：确保 MySQL 中目标库存在（否则建库）。
民警电脑的 MySQL 很可能没有预建 fraudlens 库；后端 create_all 只会建表不会建库，
若库不存在会直接连库失败。本脚本在启动后端前调用，幂等安全。

用法: python ensure_db.py [--config path/to/key.env]
"""
import os
import sys
import argparse

def _load_env(path):
    """轻量解析 KEY=VALUE（忽略注释/空行/行内#），写入 os.environ（不覆盖已存在）。"""
    env = {}
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip().strip('"').strip("'")
                v = v.strip().strip('"').strip("'")
                # 去掉行内注释（# 前无引号包裹，简单处理：只取注释前）
                if "#" in v:
                    v = v.split("#")[0].strip()
                if k:
                    env[k] = v
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    # 显式 config 优先，其次环境变量，其次默认
    cfg = _load_env(args.config) if args.config else {}
    db_host = cfg.get("DB_HOST", os.environ.get("DB_HOST", "localhost"))
    db_port = cfg.get("DB_PORT", os.environ.get("DB_PORT", "3306"))
    db_user = cfg.get("DB_USER", os.environ.get("DB_USER", "root"))
    db_pass = cfg.get("DB_PASSWORD", os.environ.get("DB_PASSWORD", ""))
    db_name = cfg.get("DB_NAME", os.environ.get("DB_NAME", "fraudlens"))

    import pymysql

    # 先不带库名连一次（保证库存在是 CREATE DATABASE 的前提）
    try:
        conn = pymysql.connect(
            host=db_host, port=int(db_port),
            user=db_user, password=db_pass, connect_timeout=5,
        )
    except pymysql.err.OperationalError as e:
        print(f"[ensure_db] 无法连接 MySQL ({db_host}:{db_port}): {e}")
        print("[ensure_db] 请确认 MySQL 已启动、key.env 的 DB_* 正确。")
        return 2

    try:
        cur = conn.cursor()
        cur.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s", (db_name,))
        if cur.fetchone():
            print(f"[ensure_db] 数据库 '{db_name}' 已存在，无需建库。")
        else:
            # utf8mb4 与业务默认一致（Docker 初始化也是 utf8mb4 / utf8mb4_unicode_ci）
            cur.execute(
                "CREATE DATABASE `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" % db_name
            )
            conn.commit()
            print(f"[ensure_db] 已创建数据库 '{db_name}' (utf8mb4)。")
        cur.close()
    except Exception as e:
        print(f"[ensure_db] 检查/建库失败: {e}")
        conn.close()
        return 3

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())