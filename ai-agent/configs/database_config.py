"""
数据库配置
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class DatabaseConfig(BaseSettings):
    """数据库配置"""
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    database: str = Field(default="aiagent", env="DB_NAME")
    username: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    
    # 连接池配置
    min_connections: int = Field(default=1, env="DB_MIN_CONNECTIONS")
    max_connections: int = Field(default=10, env="DB_MAX_CONNECTIONS")
    connection_timeout: int = Field(default=30, env="DB_CONNECTION_TIMEOUT")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"  # 允许额外字段
    }
    
    @property
    def database_url(self) -> str:
        """构建数据库URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

# 全局数据库配置实例
database_config = DatabaseConfig()
