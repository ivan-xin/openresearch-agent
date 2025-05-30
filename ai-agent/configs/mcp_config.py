"""
MCP服务器配置
"""
from pydantic import BaseSettings, Field

class MCPConfig(BaseSettings):
    """MCP服务器配置"""
    
    host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    port: int = Field(default=8000, env="MCP_SERVER_PORT")
    timeout: int = Field(default=30, env="MCP_SERVER_TIMEOUT")
    max_retries: int = Field(default=3, env="MCP_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="MCP_RETRY_DELAY")
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 全局MCP配置实例
mcp_config = MCPConfig()
