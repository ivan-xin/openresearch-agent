"""
应用配置
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """应用设置"""
    
    # 应用基础配置
    app_name: str = Field(default="AI-Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # 数据库配置
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # 缓存配置
    cache_type: str = Field(default="memory", env="CACHE_TYPE")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    # 会话配置
    max_conversation_length: int = Field(default=100, env="MAX_CONVERSATION_LENGTH")
    
    # MCP服务器配置
    mcp_server_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(default=8000, env="MCP_SERVER_PORT")
    mcp_server_timeout: int = Field(default=30, env="MCP_SERVER_TIMEOUT")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }

# 全局设置实例
settings = Settings()
