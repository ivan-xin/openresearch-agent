"""
MCP服务器配置
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class MCPConfig(BaseSettings):
    """MCP服务器配置"""
    
    # MCP 服务器启动配置 - 模仿 Claude Desktop 方式
    mcp_command: str = Field(
        default="/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server/venv/bin/python",
        env="MCP_COMMAND"
    )
    mcp_args: List[str] = Field(
        default=["/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server/src/main.py"],
        env="MCP_ARGS"
    )
    mcp_cwd: str = Field(
        default="/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server",
        env="MCP_CWD"
    )
    
    # 其他配置
    timeout: int = Field(default=30, env="MCP_TIMEOUT")
    max_retries: int = Field(default=3, env="MCP_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="MCP_RETRY_DELAY")
    
    @property
    def server_command(self) -> List[str]:
        """获取完整的服务器启动命令"""
        return [self.mcp_command] + self.mcp_args
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }

# 全局MCP配置实例
mcp_config = MCPConfig()
