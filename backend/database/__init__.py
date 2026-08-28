"""
数据库层：基于 SQLAlchemy 2.0 的轻量门面（去除 Flask 依赖，消除 docs/06 标注的 P0 架构异味）。

对外保留与 flask_sqlalchemy 兼容的常用 API：
    db.Model / db.Column / db.Integer / db.String / db.Text / db.Boolean /
    db.DateTime / db.Float / db.ForeignKey / db.JSON / db.LargeBinary /
    db.UniqueConstraint / db.PrimaryKeyConstraint / db.Index / db.relationship /
    db.text / db.session / db.engine / db.create_all() / db.drop_all() / db.remove()

内部使用 DeclarativeBase + scoped_session + sessionmaker，与 FastAPI 无状态/多副本部署兼容。
模型文件（db.Model / db.Column 经典写法）无需改动即可工作。
"""
from sqlalchemy import (
    create_engine, text, Column, Integer, String, Text, Boolean, DateTime,
    Float, ForeignKey, JSON, LargeBinary, UniqueConstraint, PrimaryKeyConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, scoped_session, relationship
from sqlalchemy.pool import QueuePool

from core.config import settings
from tools.response import logger
from .failover import FailoverEngine


class _QueryProperty:
    """类级 .query 描述符，复刻 flask_sqlalchemy 的 Model.query 行为。

    Case.query.filter_by(...) 在类上访问时返回 db.session.query(Case)，
    使现有使用 Model.query 的 crud/routes/测试无需修改即可工作。
    """

    def __get__(self, instance, owner):
        from database import db
        if owner is None:
            return self
        return db.session.query(owner)


class Base(DeclarativeBase):
    query = _QueryProperty()


class _Database:
    # 类型与工具（与 flask_sqlalchemy 同名导出，模型文件零改动）
    Model = Base
    Column = Column
    Integer = Integer
    String = String
    Text = Text
    Boolean = Boolean
    DateTime = DateTime
    Float = Float
    ForeignKey = ForeignKey
    JSON = JSON
    LargeBinary = LargeBinary
    UniqueConstraint = UniqueConstraint
    PrimaryKeyConstraint = PrimaryKeyConstraint
    Index = Index
    relationship = staticmethod(relationship)
    text = staticmethod(text)

    def __init__(self):
        self._engine = None
        self._failover = None
        self._session_factory = None
        self.session = None

    def init_app(self, app=None):
        self._init_engine()

    def _init_engine(self):
        if self._engine is not None:
            return
        connect_args = {'charset': 'utf8mb4', 'connect_timeout': 3} if 'mysql' in settings.DATABASE_URI else {}
        # 故障切换管理器：默认候选仅主库（单引擎，行为同改造前）；
        # 配置 DB_REPLICA_URIS 后按序启用自动切换。on_switch 用于切换后重绑 session。
        self._failover = FailoverEngine(
            settings.DATABASE_CANDIDATE_URIS,
            on_switch=self._rebind_session,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            echo=settings.DEBUG,
            connect_args=connect_args,
        )
        self._engine = self._failover.get_engine()
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False, future=True
        )
        self.session = scoped_session(self._session_factory)

    def _rebind_session(self, engine=None):
        """故障切换后，将 session 工厂重绑到新引擎，保证 db.session 透明跟随。"""
        if self._session_factory is None:
            return
        self._session_factory.configure(bind=engine or (self._failover.get_engine() if self._failover else None))

    @property
    def engine(self):
        if self._engine is None:
            self._init_engine()
        return self._failover.get_engine()

    def execute_with_failover(self, fn, max_retries=None):
        """对 fn(engine) 执行并自动故障切换重试（详见 database/failover.py）。"""
        if self._failover is None:
            self._init_engine()
        return self._failover.execute_with_failover(fn, max_retries)

    def create_all(self):
        from . import models  # noqa: F401  触发表注册
        try:
            from . import p1_models  # noqa: F401
        except Exception as e:  # pragma: no cover
            logger.warning(f"p1_models 导入跳过: {e}")
        try:
            from . import workflow_models  # noqa: F401  Phase R1 办案工作流模型
        except Exception as e:  # pragma: no cover
            logger.warning(f"workflow_models 导入跳过: {e}")
        Base.metadata.create_all(self.engine)

    def migrate(self):
        """G3 兼容迁移：为已存在的 cases/gangs 表补齐 department 列。

        create_all() 只建不存在的表、不会 ALTER 已有表，导致历史库缺少
        G3 新增的 department 列（现象：Unknown column 'cases.department'）。
        此处幂等补齐：先查 information_schema，缺失才 ALTER。表名/列名为
        可信字面量，故 ALTER 使用 f-string 安全；WHERE 绑定参数仅作取值。
        同时幂等补齐 cases.is_demo 列（演示数据标注）并回填历史种子案件。
        """
        targets = {
            "cases": "VARCHAR(100) NOT NULL DEFAULT ''",
            "gangs": "VARCHAR(100) NOT NULL DEFAULT ''",
        }
        # Phase R1：补齐 cases.lifecycle_status 列（ADR-18 办案状态机）
        lifecycle_targets = {
            "cases": ("lifecycle_status", "VARCHAR(32) NOT NULL DEFAULT '待立案'"),
        }
        # 演示数据标注列：cases.is_demo
        demo_targets = {
            "cases": ("is_demo", "BOOLEAN NOT NULL DEFAULT 0"),
        }
        try:
            with self.engine.connect() as conn:
                existing = {}
                for tbl in set(list(targets.keys()) + list(lifecycle_targets.keys()) + list(demo_targets.keys())):
                    res = conn.execute(
                        text(
                            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                        ),
                        {"t": tbl},
                    )
                    existing[tbl] = {r[0] for r in res}
                for tbl, spec in targets.items():
                    if "department" not in existing.get(tbl, set()):
                        conn.execute(
                            text(f"ALTER TABLE {tbl} ADD COLUMN department {spec}")
                        )
                        try:
                            conn.execute(
                                text(
                                    f"CREATE INDEX ix_{tbl}_department ON {tbl}(department)"
                                )
                            )
                        except Exception:
                            pass
                        logger.info(f"迁移：{tbl}.department 已补齐")
                # Phase R1：cases.lifecycle_status
                for tbl, (col, spec) in lifecycle_targets.items():
                    if col not in existing.get(tbl, set()):
                        conn.execute(
                            text(f"ALTER TABLE {tbl} ADD COLUMN {col} {spec}")
                        )
                        try:
                            conn.execute(
                                text(
                                    f"CREATE INDEX ix_{tbl}_{col} ON {tbl}({col})"
                                )
                            )
                        except Exception:
                            pass
                        logger.info(f"迁移：{tbl}.{col} 已补齐")
                # 演示数据标注列：cases.is_demo
                for tbl, (col, spec) in demo_targets.items():
                    if col not in existing.get(tbl, set()):
                        conn.execute(
                            text(f"ALTER TABLE {tbl} ADD COLUMN {col} {spec}")
                        )
                        try:
                            conn.execute(
                                text(
                                    f"CREATE INDEX ix_{tbl}_{col} ON {tbl}({col})"
                                )
                            )
                        except Exception:
                            pass
                        logger.info(f"迁移：{tbl}.{col} 已补齐")
                # 回填历史种子案件的 is_demo 标注（session_id 以 auto_seed 开头）
                conn.execute(
                    text(
                        "UPDATE cases SET is_demo = 1 "
                        "WHERE is_demo = 0 AND session_id LIKE 'auto_seed%'"
                    )
                )
                conn.commit()
        except Exception as e:  # pragma: no cover
            logger.warning(f"列迁移跳过: {e}")

    def drop_all(self):
        Base.metadata.drop_all(self.engine)

    def remove(self):
        if self.session is not None:
            self.session.remove()


db = _Database()


def init_db(app=None):
    """兼容历史调用 init_db(app)。不再依赖 Flask 应用上下文。"""
    db.init_app(app)
    try:
        db.create_all()
    except Exception as e:  # pragma: no cover
        logger.warning(f"建表跳过（数据库可能未就绪）: {e}")
    db.migrate()  # G3：补齐历史库缺失的 department 列
    logger.info("数据库初始化完成（SQLAlchemy 2.0，无 Flask 依赖）")
