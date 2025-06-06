"""
MCP客户端服务 - stdio协议版本 - 简化版
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
        self.process: Optional[asyncio.subprocess.Process] = None
        self.available_tools: List[Dict[str, Any]] = []
        self._tools_loaded = False
        self._request_id = 0
        self._initialized = False
        self._lock = asyncio.Lock()  # 添加锁防止并发问题
    
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
        async with self._lock:
            if self._initialized:
                return
                
            try:
                logger.info("Starting MCP server process", 
                           command=mcp_config.actual_server_command,
                           cwd=mcp_config.mcp_cwd)
                
                # 检查工作目录是否存在
                if not os.path.exists(mcp_config.mcp_cwd):
                    raise Exception(f"MCP server directory not found: {mcp_config.mcp_cwd}")
                
                # 检查命令文件是否存在
                if not os.path.exists(mcp_config.mcp_command):
                    raise Exception(f"MCP command not found: {mcp_config.mcp_command}")
                
                # 设置环境变量
                env = os.environ.copy()
                env['PYTHONDONTWRITEBYTECODE'] = '1'
                env.pop('DEBUGPY_LAUNCHER_PORT', None)
                env.pop('PYDEVD_LOAD_VALUES_ASYNC', None)
                
                # 启动MCP服务器进程
                self.process = await asyncio.create_subprocess_exec(
                    *mcp_config.actual_server_command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=mcp_config.mcp_cwd,
                    env=env
                )
                
                logger.info("Process started", pid=self.process.pid)
                
                # 等待进程启动
                await asyncio.sleep(1)
                
                # 检查进程是否正常启动
                if self.process.returncode is not None:
                    stderr_output = ""
                    if self.process.stderr:
                        try:
                            stderr_data = await asyncio.wait_for(
                                self.process.stderr.read(1024), timeout=1.0
                            )
                            stderr_output = stderr_data.decode()
                        except:
                            pass
                    
                    logger.error("Process failed to start", 
                               stderr=stderr_output, 
                               return_code=self.process.returncode)
                    
                    raise Exception(f"MCP server process failed to start: {stderr_output}")
                
                # 发送初始化请求
                await self._send_initialize()
                
                # 加载可用工具
                await self._load_available_tools()
                
                self._initialized = True
                
                logger.info(
                    "MCP client initialized successfully",
                    tools_count=len(self.available_tools),
                    available_tools=[tool.get("name") for tool in self.available_tools]
                )
                
            except Exception as e:
                logger.error("Failed to initialize MCP client", error=str(e))
                await self.cleanup()
                raise
    
    async def _read_json_response(self) -> Dict[str, Any]:
        """读取JSON响应，过滤掉日志行"""
        if not self.process or not self.process.stdout:
            raise Exception("Process not available")
        
        max_attempts = 50
        attempt = 0
        
        while attempt < max_attempts:
            try:
                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=2.0
                )
                
                if not line:
                    raise Exception("No more data from server")
                
                line_str = line.decode().strip()
                logger.debug("Read line from MCP server", line=line_str[:200])
                
                # 尝试解析JSON
                try:
                    data = json.loads(line_str)
                    # 检查是否是JSON-RPC响应
                    if isinstance(data, dict) and data.get("jsonrpc") == "2.0":
                        logger.debug("Found JSON-RPC response", response_id=data.get("id"))
                        return data
                except json.JSONDecodeError:
                    # 不是JSON，可能是日志，继续读取
                    logger.debug("Non-JSON line, continuing...")
                
                attempt += 1
                
            except asyncio.TimeoutError:
                logger.debug("Timeout reading line, continuing...")
                attempt += 1
                continue
        
        raise Exception("No JSON-RPC response found after reading multiple lines")
    
    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送JSON-RPC请求"""
        if not self.process or not self.process.stdin:
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
            logger.debug("Sending MCP request", 
                        method=method, 
                        request_id=request_id,
                        params=params)
            
            self.process.stdin.write(request_line.encode())
            await self.process.stdin.drain()
            
            # 读取响应
            try:
                response = await asyncio.wait_for(
                    self._read_json_response(),
                    timeout=mcp_config.timeout
                )
            except asyncio.TimeoutError:
                raise Exception(f"MCP server response timeout for method: {method}")
            
            logger.debug("Received MCP response", 
                        response_id=response.get("id"),
                        has_result="result" in response,
                        has_error="error" in response)
            
            # 检查错误
            if "error" in response:
                error = response["error"]
                logger.error("MCP server returned error", 
                           method=method,
                           error_code=error.get('code'),
                           error_message=error.get('message'))
                raise Exception(f"MCP error: {error.get('message', 'Unknown error')}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error("Error sending MCP request", method=method, error=str(e))
            raise
    
    async def _send_notification(self, method: str, params: Dict[str, Any] = None):
        """发送通知（无响应）"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server process is not running")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        try:
            notification_line = json.dumps(notification) + "\n"
            logger.debug("Sending MCP notification", method=method)
            
            self.process.stdin.write(notification_line.encode())
            await self.process.stdin.drain()
            
        except Exception as e:
            logger.error("Error sending MCP notification", method=method, error=str(e))
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
        
        # 发送初始化完成通知
        await self._send_notification("notifications/initialized")
    
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
            # 设置默认工具列表作为备选
            self.available_tools = []
            self._tools_loaded = True
            logger.warning("Using empty tools list due to error")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具 - 直接调用MCP server"""
        if not self._initialized:
            await self.initialize()
        
        logger.info("Calling MCP tool", 
                   tool_name=tool_name, 
                   arguments=arguments)
        
        try:
            # 构建MCP工具调用参数
            params = {
                "name": tool_name,
                "arguments": arguments
            }
            
            # 发送工具调用请求到MCP server
            result = await self._send_request("tools/call", params)
            
            logger.info("MCP tool call successful", 
                       tool_name=tool_name,
                       result_type=type(result).__name__)
            
            return result
                    
        except Exception as e:
            logger.error("Error calling MCP tool", 
                        tool_name=tool_name, 
                        arguments=arguments,
                        error=str(e))
            raise
    
    # 便捷方法（可选，为了向后兼容和易用性）
    async def search_papers(self, query: str, limit: int = 10, fields: List[str] = None) -> Dict[str, Any]:
        """搜索论文 - 便捷方法"""
        arguments = {
            "query": query,
            "limit": limit
        }
        if fields:
            arguments["fields"] = fields
        
        return await self.call_tool("search_papers", arguments)
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """获取论文详情 - 便捷方法"""
        return await self.call_tool("get_paper_details", {"paper_id": paper_id})
    
    async def search_authors(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """搜索作者 - 便捷方法"""
        return await self.call_tool("search_authors", {"query": query, "limit": limit})
    
    async def get_author_details(self, author_id: str) -> Dict[str, Any]:
        """获取作者详情 - 便捷方法"""
        return await self.call_tool("get_author_details", {"author_id": author_id})
    
    async def get_citation_network(self, paper_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取引用网络 - 便捷方法"""
        return await self.call_tool("get_citation_network", {"paper_id": paper_id, "depth": depth})
    
    async def get_collaboration_network(self, author_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取合作网络 - 便捷方法"""
        return await self.call_tool("get_collaboration_network", {"author_id": author_id, "depth": depth})
    
    async def get_trending_papers(self, field: str = "", time_range: str = "1year") -> Dict[str, Any]:
        """获取热门论文 - 便捷方法"""
        return await self.call_tool("get_trending_papers", {"field": field, "time_range": time_range})
    
    # 重试机制
    async def call_tool_with_retry(self, tool_name: str, arguments: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """带重试机制的工具调用"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.debug("Attempting tool call", 
                           tool_name=tool_name, 
                           attempt=attempt + 1,
                           arguments=arguments)
                
                result = await self.call_tool(tool_name, arguments)
                
                if attempt > 0:
                    logger.info("Tool call succeeded after retry", 
                              tool_name=tool_name, 
                              attempt=attempt + 1)
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning("Tool call failed", 
                             tool_name=tool_name, 
                             attempt=attempt + 1, 
                             error=str(e))
                
                if attempt < max_retries - 1:
                    # 等待一段时间后重试
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info("Retrying after delay", delay=wait_time)
                    await asyncio.sleep(wait_time)
                    
                    # 如果进程死了，尝试重新初始化
                    if self.process and self.process.returncode is not None:
                        logger.warning("Process died, reinitializing...")
                        await self.cleanup()
                        await self.initialize()
        
        logger.error("Tool call failed after all retries", 
                    tool_name=tool_name, 
                    error=str(last_error))
        raise last_error
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self.available_tools.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # 检查进程状态
            process_running = self.process is not None and self.process.returncode is None
            
            # 尝试获取工具列表
            tools_accessible = False
            try:
                await self._send_request("tools/list")
                tools_accessible = True
            except:
                pass
            
            status = "healthy" if process_running and tools_accessible else "unhealthy"
            
            return {
                "status": status,
                "tools_count": len(self.available_tools),
                "process_running": process_running,
                "tools_accessible": tools_accessible,
                "available_tools": [tool.get("name") for tool in self.available_tools]
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "process_running": False,
                "tools_accessible": False
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("Cleaning up MCP client")
            
            if self.process:
                # 尝试优雅关闭
                if self.process.returncode is None:
                    try:
                        # 发送关闭通知
                        await asyncio.wait_for(
                            self._send_notification("notifications/shutdown"),
                            timeout=2.0
                        )
                    except:
                        pass
                    
                    # 关闭stdin
                    if self.process.stdin:
                        self.process.stdin.close()
                        await self.process.stdin.wait_closed()
                    
                    # 等待进程结束
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("Process did not terminate gracefully, killing")
                        self.process.kill()
                        await self.process.wait()
                
                self.process = None
            
            self._initialized = False
            self._tools_loaded = False
            
            logger.info("MCP client cleanup completed")
            
        except Exception as e:
            logger.error("Error during MCP client cleanup", error=str(e))

# 创建全局实例
mcp_client_stdio = MCPClient()

