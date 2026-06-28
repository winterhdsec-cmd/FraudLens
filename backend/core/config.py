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
    ENV: str = Field(default="production", alias="ENV")
    
    # 数据库配置
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
    
    # LLM 配置
    LLM_PROVIDER: str = Field(default="deepseek", alias="LLM_PROVIDER")
    DEEPSEEK_API_KEY: str = Field(default="", alias="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=2000, alias="LLM_MAX_TOKENS")
    
    # 安全配置
    JWT_SECRET_KEY: str = Field(default="", alias="JWT_SECRET_KEY")
    RATE_LIMIT_REQUESTS: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # 秒
    
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
    def REDIS_URI(self) -> str:
        """生成Redis URI"""
        if self.REDIS_PASSWORD:
            return f'redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'
        return f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()
