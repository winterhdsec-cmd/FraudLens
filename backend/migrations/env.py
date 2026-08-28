"""Alembic 环境（可选迁移能力，对应 docs/09 #C18 T5）。

- 仅在执行 `alembic` CLI 时运行，不影响 FastAPI/Celery 启动。
- target_metadata 取自 database 门面的 Base.metadata（与 models/p1_models 共享）。
- 用法（需 DATABASE_URI 指向目标库）：
    cd backend
    alembic revision --autogenerate -m "init"
    alembic upgrade head
"""
from logging.config import fileConfig

from alembic import context

from database import db

target_metadata = db.Model.metadata


def run_migrations_offline():
    url = db.engine.url.render_as_string(hide_password=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with db.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
