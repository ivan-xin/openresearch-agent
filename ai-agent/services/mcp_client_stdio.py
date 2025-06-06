"""
MCP客户端服务 - stdio协议版本 - 修复日志过滤问题
"""
import asyncio
import json
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
import subprocess
import os

from configs.mcp_config import mcp_config
from models.task import Task, TaskResult, TaskStatus

logger = structlog.get_logger()

class MCPClient:
    """MCP客户端 - stdio协议"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.available_tools: List[Dict[str, Any]] = []
        self._tools_loaded = False
        self._request_id = 0
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
    
    def _get_next_request_id(self) -> int:
        """获取下一个请求ID"""
        self._request_id += 1
        return self._request_id
    
    async def initialize(self):
        """初始化MCP客户端"""
        try:
            logger.info("Starting MCP server process", 
                       command=mcp_config.server_command,
                       cwd=mcp_config.mcp_cwd)
            
            # 检查工作目录是否存在
            if not os.path.exists(mcp_config.mcp_cwd):
                raise Exception(f"MCP server directory not found: {mcp_config.mcp_cwd}")
            
            # 检查命令文件是否存在
            if not os.path.exists(mcp_config.mcp_command):
                raise Exception(f"MCP command not found: {mcp_config.mcp_command}")
            
            # 启动MCP服务器进程
            self.process = subprocess.Popen(
                mcp_config.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                cwd=mcp_config.mcp_cwd
            )
            
            logger.info("Process started", pid=self.process.pid)
            
            # 等待进程启动
            await asyncio.sleep(2)
            
            # 检查进程是否正常启动
            if self.process.poll() is not None:
                stderr_output = self.process.stderr.read() if self.process.stderr else ""
                stdout_output = self.process.stdout.read() if self.process.stdout else ""
                
                logger.error("Process failed to start", 
                           stderr=stderr_output, 
                           stdout=stdout_output,
                           return_code=self.process.poll())
                
                raise Exception(f"MCP server process failed to start: {stderr_output}")
            
            # 发送初始化请求
            await self._send_initialize()
            
            # 加载可用工具
            await self._load_available_tools()
            
            logger.info(
                "MCP client initialized successfully",
                tools_count=len(self.available_tools)
            )
            
        except Exception as e:
            logger.error("Failed to initialize MCP client", error=str(e))
            await self.cleanup()
            raise
    
    def _is_json_rpc_response(self, line: str) -> bool:
        """检查是否是 JSON-RPC 响应"""
        try:
            data = json.loads(line.strip())
            return "jsonrpc" in data and ("result" in data or "error" in data)
        except:
            return False
    
    async def _read_json_rpc_response(self) -> str:
        """读取 JSON-RPC 响应，过滤掉日志行"""
        max_attempts = 50  # 最多读取50行
        attempt = 0
        
        while attempt < max_attempts:
            try:
                line = await asyncio.wait_for(
                    asyncio.to_thread(self.process.stdout.readline),
                    timeout=1.0  # 每行1秒超时
                )
                
                if not line:
                    break
                
                logger.debug("Read line from MCP server", line=line.strip())
                
                # 检查是否是 JSON-RPC 响应
                if self._is_json_rpc_response(line):
                    logger.debug("Found JSON-RPC response", line=line.strip())
                    return line
                
                # 如果是日志行，继续读取下一行
                attempt += 1
                
            except asyncio.TimeoutError:
                logger.debug("Timeout reading line, continuing...")
                attempt += 1
                continue
        
        raise Exception("No JSON-RPC response found after reading multiple lines")
    
    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送JSON-RPC请求"""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server process is not running")
        
        request_id = self._get_next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            # 发送请求
            request_line = json.dumps(request) + "\n"
            logger.debug("Sending MCP request", method=method, request_id=request_id)
            
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
            
            # 读取响应 - 使用新的过滤方法
            try:
                response_line = await asyncio.wait_for(
                    self._read_json_rpc_response(),
                    timeout=mcp_config.timeout
                )
            except asyncio.TimeoutError:
                raise Exception(f"MCP server response timeout for method: {method}")
            
            if not response_line:
                raise Exception("No response from MCP server")
            
            logger.debug("Received MCP response", response=response_line.strip())
            
            response = json.loads(response_line.strip())
            
            # 检查错误
            if "error" in response:
                error = response["error"]
                raise Exception(f"MCP error: {error.get('message', 'Unknown error')}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error("Error sending MCP request", method=method, error=str(e))
            raise
    
    async def _send_initialize(self):
        """发送初始化请求"""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "ai-agent",
                "version": "1.0.0"
            }
        }
        
        result = await self._send_request("initialize", params)
        logger.info("MCP server initialized", capabilities=result.get("capabilities", {}))
    
    async def _load_available_tools(self):
        """加载可用工具列表"""
        try:
            result = await self._send_request("tools/list")
            self.available_tools = result.get("tools", [])
            self._tools_loaded = True
            
            logger.info(
                "Available tools loaded",
                tools=[tool.get("name") for tool in self.available_tools]
            )
                    
        except Exception as e:
            logger.error("Error loading available tools", error=str(e))
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        try:
            params = {
                "name": tool_name,
                "arguments": arguments
            }
            
            logger.info("Calling MCP tool", tool_name=tool_name, arguments=arguments)
            
            result = await self._send_request("tools/call", params)
            
            logger.info("MCP tool call successful", tool_name=tool_name)
            
            return result
                    
        except Exception as e:
            logger.error("Error calling MCP tool", tool_name=tool_name, error=str(e))
            raise
    
    async def call_tool_with_retry(self, tool_name: str, 
                                  arguments: Dict[str, Any]) -> Dict[str, Any]:
        """带重试的工具调用"""
        last_error = None
        
        for attempt in range(mcp_config.max_retries):
            try:
                return await self.call_tool(tool_name, arguments)
                
            except Exception as e:
                last_error = e
                if attempt < mcp_config.max_retries - 1:
                    wait_time = mcp_config.retry_delay * (2 ** attempt)
                    logger.warning(
                        "MCP tool call failed, retrying",
                        tool_name=tool_name,
                        attempt=attempt + 1,
                        wait_time=wait_time,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)
        
        raise last_error
    
    # 便捷方法
    async def search_papers(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """搜索论文"""
        return await self.call_tool_with_retry(
            "search_papers",
            {"query": query, "limit": limit}
        )
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """获取论文详情"""
        return await self.call_tool_with_retry(
            "get_paper_details",
            {"paper_id": paper_id}
        )
    
    async def search_authors(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """搜索作者"""
        return await self.call_tool_with_retry(
            "search_authors",
            {"query": query, "limit": limit}
        )
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self.available_tools.copy()
    
    def is_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        return any(tool.get("name") == tool_name for tool in self.available_tools)
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.process:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
                
                logger.info("MCP server process terminated")
                
        except Exception as e:
            logger.error("Error during MCP client cleanup", error=str(e))

# 全局MCP客户端实例
mcp_client_stdio = MCPClient()
