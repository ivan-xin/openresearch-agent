"""
应用配置管理 - 改进版
"""
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = Field(default="AI-Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")
    
    # 数据库配置
    # database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # 会话配置
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")  # 会话超时时间（秒）
    max_conversation_length: int = Field(default=100, env="MAX_CONVERSATION_LENGTH")  # 最大对话长度

    # 缓存配置 - 新增
    # cache_type: str = Field(default="memory", env="CACHE_TYPE")
    # cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局配置实例
settings = Settings()
