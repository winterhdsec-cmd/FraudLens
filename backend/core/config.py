"""
统一配置管理
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "FraudLens"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = Field(default=False, alias="DEBUG")
    ENV: str = Field(default="production", alias="ENV")  # dev / staging / production
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")  # DEBUG / INFO / WARNING / ERROR
    
    # 数据库配置
    DB_REPLICA_URIS: str = Field(default="", alias="DB_REPLICA_URIS")  # 逗号分隔的故障切换候选（host:port 或完整 mysql URI；留空=单库，退化为现状）
    DB_USER: str = Field(default="root", alias="DB_USER")
    DB_PASSWORD: str = Field(default="", alias="DB_PASSWORD")
    DB_HOST: str = Field(default="localhost", alias="DB_HOST")
    DB_PORT: int = Field(default=3306, alias="DB_PORT")
    DB_NAME: str = Field(default="fraudlens", alias="DB_NAME")
    
    # Redis 配置
    REDIS_HOST: str = Field(default="localhost", alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT")
    REDIS_DB: int = Field(default=0, alias="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    # Redis Sentinel（HA 透明故障转移，G14 后续项）：非空即启用哨兵模式
    REDIS_SENTINEL_HOSTS: str = Field(default="", alias="REDIS_SENTINEL_HOSTS")  # "host1:26379,host2:26379"
    REDIS_SENTINEL_SERVICE_NAME: str = Field(default="mymaster", alias="REDIS_SENTINEL_SERVICE_NAME")
    # 内置 Redis（零依赖启动）：1=启动时自动探测/拉起 vendor/redis 便携版（仅 Windows 生效）
    REDIS_AUTOSTART: str = Field(default="0", alias="REDIS_AUTOSTART")
    REDIS_EMBEDDED_MAXMEM: str = Field(default="256mb", alias="REDIS_EMBEDDED_MAXMEM")
    
    # LLM 配置
    LLM_PROVIDER: str = Field(default="deepseek", alias="LLM_PROVIDER")
    DEEPSEEK_API_KEY: str = Field(default="", alias="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=2000, alias="LLM_MAX_TOKENS")
    
    # 安全配置
    JWT_SECRET_KEY: str = Field(default="", alias="JWT_SECRET_KEY")
    RATE_LIMIT_REQUESTS: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")  # 单 user/IP 每分钟上限（G6）
    RATE_LIMIT_WINDOW: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # 秒
    CORS_ALLOWED_ORIGINS: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")  # 逗号分隔白名单（G4）
    TLS_ENABLED: str = Field(default="0", alias="TLS_ENABLED")  # 开启后下发 HSTS + 80→443（G1）
    DISABLE_CLOUD_LLM: str = Field(default="1", alias="DISABLE_CLOUD_LLM")  # 默认关闭云端 LLM（数据不出域，G2）
    CLOUD_LLM_MASK: str = Field(default="1", alias="CLOUD_LLM_MASK")  # 启用云端 LLM 时强制脱敏（G2）

    # 可观测 / 分布式追踪（G10, docs/09 #C46）：默认关闭；仅 OTEL_ENABLED=1 且装了
    # requirements-otel.txt 时才真正导出追踪。零依赖即可运行，绝不因缺包崩溃。
    OTEL_ENABLED: str = Field(default="0", alias="OTEL_ENABLED")  # 1=启用 OpenTelemetry 追踪
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://otel-collector:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_SERVICE_NAME: str = Field(default="fraudlens-backend", alias="OTEL_SERVICE_NAME")
    
    # Agent 配置
    AGENT_MAX_ITERATIONS: int = Field(default=10, alias="AGENT_MAX_ITERATIONS")
    AGENT_TIMEOUT: int = Field(default=300, alias="AGENT_TIMEOUT")  # 秒
    REFLECTION_ENABLED: bool = Field(default=True, alias="REFLECTION_ENABLED")
    
    # 聚类配置
    CLUSTER_MIN_SIZE: int = Field(default=2, alias="CLUSTER_MIN_SIZE")
    CLUSTER_EPSILON: float = Field(default=0.5, alias="CLUSTER_EPSILON")
    ADAPTIVE_CLUSTERING: bool = Field(default=True, alias="ADAPTIVE_CLUSTERING")
    
    # 向量模型配置
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-large-zh-v1.5", alias="EMBEDDING_MODEL")
    EMBEDDING_DIM: int = Field(default=1024, alias="EMBEDDING_DIM")
    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = Field(default=50 * 1024 * 1024, alias="MAX_UPLOAD_SIZE")  # 50MB
    ALLOWED_EXTENSIONS: list = Field(default=["txt", "docx", "pdf", "png", "jpg", "jpeg"], alias="ALLOWED_EXTENSIONS")
    
    # CORS 配置
    CORS_ORIGINS: list = Field(default=["*"], alias="CORS_ORIGINS")
    
    @property
    def DATABASE_URI(self) -> str:
        """生成数据库URI"""
        return f'mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4'

    @property
    def DATABASE_CANDIDATE_URIS(self) -> list:
        """故障切换候选 URI 列表（主库在前，副本/新主库在后）。

        留空 DB_REPLICA_URIS 时仅返回主库单节点，故障切换管理器退化为单引擎，
        行为与改造前完全一致；配置副本后才启用自动切换。
        """
        primary = self.DATABASE_URI
        if not self.DB_REPLICA_URIS.strip():
            return [primary]
        cands = [primary]
        for item in self.DB_REPLICA_URIS.split(','):
            item = item.strip()
            if not item:
                continue
            if item.startswith('mysql'):
                cands.append(item)
            elif ':' in item:
                host, _, port = item.partition(':')
                cands.append(
                    f'mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{host}:{port}/{self.DB_NAME}?charset=utf8mb4'
                )
        return cands
    
    @property
    def REDIS_URI(self) -> str:
        """生成Redis URI；哨兵模式下返回 redis+sentinel:// 形式（客户端自动跟随新主）。"""
        if self.REDIS_SENTINEL_HOSTS:
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            return f'redis+sentinel://{auth}{self.REDIS_SENTINEL_HOSTS}/{self.REDIS_SENTINEL_SERVICE_NAME}/{self.REDIS_DB}'
        if self.REDIS_PASSWORD:
            return f'redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'
        return f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._apply_env_profile()

    def _apply_env_profile(self):
        """按 ENV 应用环境差异化默认值（仅在对应环境变量未显式设置时覆盖）。

        仅作为低优先级的「环境默认」，任何显式环境变量都优先。
        """
        profile = _ENV_PROFILES.get((self.ENV or "production").lower())
        if not profile:
            return
        for key, value in profile.items():
            if os.getenv(key) is None:
                try:
                    object.__setattr__(self, key, value)
                except Exception:
                    pass

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 环境差异化默认值（仅当对应环境变量未显式设置时应用，详见 Settings._apply_env_profile）
_ENV_PROFILES = {
    "dev": {
        "DEBUG": True,
        "LOG_LEVEL": "DEBUG",
        "RATE_LIMIT_REQUESTS": 0,          # 0 = 开发期不限流
        "CORS_ALLOWED_ORIGINS": "*",
        "DISABLE_CLOUD_LLM": "1",          # 数据不出域（开发默认）
    },
    "staging": {
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "RATE_LIMIT_REQUESTS": 120,
        "TLS_ENABLED": "1",                # 启用 HSTS（需配合证书）
    },
    "prod": {
        "DEBUG": False,
        "LOG_LEVEL": "WARNING",
        "RATE_LIMIT_REQUESTS": 60,
        "TLS_ENABLED": "1",                # 启用 HSTS（需配合证书）
    },
}


# 全局配置实例
settings = Settings()
