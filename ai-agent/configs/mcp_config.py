"""
MCP服务器配置
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json
import os

class MCPConfig(BaseSettings):
    """MCP服务器配置"""
    
    # stdio 协议配置
    server_command: List[str] = Field(
        default=["python", "/path/to/openresearch-mcp-server/src/main.py"],
        env="MCP_SERVER_COMMAND"
    )

    host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    port: int = Field(default=8000, env="MCP_SERVER_PORT")
    timeout: int = Field(default=30, env="MCP_SERVER_TIMEOUT")
    max_retries: int = Field(default=3, env="MCP_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="MCP_RETRY_DELAY")
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def mcp_cwd(self) -> str:
        """MCP服务器工作目录"""
        return "/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server"
    
    @property
    def mcp_command(self) -> str:
        """MCP服务器主文件路径"""
        return os.path.join(self.mcp_cwd, "src/main.py")
    
    @property
    def mcp_python(self) -> str:
        """MCP服务器Python解释器路径"""
        return os.path.join(self.mcp_cwd, "venv/bin/python")
    
    @property
    def actual_server_command(self) -> List[str]:
        """实际的服务器命令（使用正确的Python路径）"""
        return [self.mcp_python, self.mcp_command]
    
    def model_post_init(self, __context):
        """初始化后处理"""
        # 如果环境变量中有 MCP_SERVER_COMMAND，尝试解析
        if hasattr(self, '_env_server_command'):
            try:
                if isinstance(self._env_server_command, str):
                    self.server_command = json.loads(self._env_server_command)
            except:
                pass
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }

# 全局MCP配置实例
mcp_config = MCPConfig()
