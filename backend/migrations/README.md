# Alembic 迁移（可选增强，对应 T5 / #C18）

本目录提供基于 Alembic 的数据库迁移能力，作为「去除 Flask-SQLAlchemy 依赖」
后的可选增强。**不运行也不影响应用启动**，仅在执行 `alembic` CLI 时使用。

## 前提
- 已安装 `alembic`（`pip install alembic`）
- 环境变量 `DATABASE_URI`（由 `core/config.py` 读取）指向目标 MySQL

## 用法
```bash
cd backend
# 生成迁移脚本（依据 models/p1_models 与库现状自动 diff）
alembic revision --autogenerate -m "init schema"
# 应用迁移
alembic upgrade head
# 回滚一步
alembic downgrade -1
```

## 说明
- `target_metadata` 取自 `database` 门面的 `Base.metadata`，与 `db.Model` 共享，
  无需重复维护元数据。
- 当前 `init_db()` 仍使用 `Base.metadata.create_all()` 建表（开发/演示便利）；
  生产环境建议改为由 Alembic 迁移管理，关闭 `create_all` 以纳入版本控制。
