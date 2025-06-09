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
    timeout: int = Field(default=60, env="MCP_SERVER_TIMEOUT")
    max_retries: int = Field(default=3, env="MCP_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="MCP_RETRY_DELAY")
    
    # 日志配置
    enable_debug_log: bool = Field(default=True, env="MCP_ENABLE_DEBUG_LOG")
    debug_log_file: str = Field(default="logs/mcp_debug.log", env="MCP_DEBUG_LOG_FILE")
    
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
    def debug_log_path(self) -> str:
        """调试日志文件完整路径"""
        if os.path.isabs(self.debug_log_file):
            return self.debug_log_file
        
        # 相对路径处理
        full_path = os.path.join(self.mcp_cwd, self.debug_log_file)
        
        # 确保目录存在
        log_dir = os.path.dirname(full_path)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                print(f"Created log directory: {log_dir}")
            except Exception as e:
                print(f"Failed to create log directory {log_dir}: {e}")
        
        return full_path


    
    @property
    def actual_server_command(self) -> List[str]:
        """实际的服务器命令（使用正确的Python路径）"""
        return [self.mcp_python, self.mcp_command]
        
    @property
    def server_command_with_log_redirect(self) -> List[str]:
        """带日志重定向的服务器命令"""
        if self.enable_debug_log:
            log_path = self.debug_log_path
            print(f"Using log file: {log_path}")
            
            # 同时重定向stdout和stderr到日志文件
            return [
                "bash", "-c", 
                f'"{self.mcp_python}" "{self.mcp_command}" 2>> "{log_path}"'
            ]
        return self.actual_server_command

    
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
