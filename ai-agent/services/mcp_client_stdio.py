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
                # 使用带日志重定向的命令
                # if mcp_config.enable_debug_log:
                #     command = mcp_config.server_command_with_log_redirect
                #     # 确保日志目录存在
                #     log_dir = os.path.dirname(mcp_config.debug_log_path)
                #     os.makedirs(log_dir, exist_ok=True)
                #     logger.info("Using log redirection", 
                #             log_file=mcp_config.debug_log_path)
                # else:
                command = mcp_config.actual_server_command
                
                logger.info("Starting MCP server process", 
                        command=command,
                        cwd=mcp_config.mcp_cwd,
                        debug_log_enabled=mcp_config.enable_debug_log)
                
                # 检查工作目录是否存在
                if not os.path.exists(mcp_config.mcp_cwd):
                    raise Exception(f"MCP server directory not found: {mcp_config.mcp_cwd}")
                
                # 检查命令文件是否存在
                if not os.path.exists(mcp_config.mcp_command):
                    raise Exception(f"MCP command not found: {mcp_config.mcp_command}")
                
                # 设置环境变量
                env = os.environ.copy()
                env['PYTHONDONTWRITEBYTECODE'] = '1'
                env['PYTHONUNBUFFERED'] = '1'

                # 移除可能影响MCP进程的调试变量
                env.pop('DEBUGPY_LAUNCHER_PORT', None)
                env.pop('PYDEVD_LOAD_VALUES_ASYNC', None)
                
                # 启动MCP服务器进程
                self.process = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,  # 保留用于错误处理
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
                    available_tools=[tool.get("name") for tool in self.available_tools],
                    log_file=mcp_config.debug_log_path if mcp_config.enable_debug_log else None
                )
                
            except Exception as e:
                logger.error("Failed to initialize MCP client", error=str(e))
                await self.cleanup()
                raise

    
    async def _read_stderr(self) -> str:
        """读取stderr输出"""
        if not self.process or not self.process.stderr:
            return ""
        
        try:
            stderr_data = await asyncio.wait_for(
                self.process.stderr.read(2048), timeout=1.0
            )
            return stderr_data.decode()
        except:
            return ""
        
    async def _read_json_response(self) -> Dict[str, Any]:
        """读取JSON响应，过滤掉日志行"""
        if not self.process or not self.process.stdout:
            raise Exception("Process not available")
        
        # 首先检查进程状态
        if self.process.returncode is not None:
            logger.error("Process already terminated", return_code=self.process.returncode)
            raise Exception(f"MCP server process terminated: {self.process.returncode}")
        
        collected_lines = []
        start_time = asyncio.get_event_loop().time()
        max_wait_time = min(mcp_config.timeout, 60.0)  # 最多等待60秒
        
        logger.debug("Starting to read JSON response", max_wait_time=max_wait_time)
        
        # 简化逻辑：一直循环直到找到响应或超时
        while True:
            # 检查总时间是否超时
            elapsed_time = asyncio.get_event_loop().time() - start_time
            if elapsed_time >= max_wait_time:
                logger.error("Total timeout exceeded while waiting for JSON-RPC response",
                            elapsed_time=elapsed_time,
                            max_wait_time=max_wait_time,
                            lines_collected=len(collected_lines))
                break
            
            try:
                # 剩余时间
                remaining_time = max_wait_time - elapsed_time
                # 单次读取超时：最多5秒，但不超过剩余时间
                line_timeout = min(5.0, remaining_time)
                
                if line_timeout <= 0:
                    logger.warning("No time remaining")
                    break
                
                logger.debug("Reading line from stdout", 
                            timeout=line_timeout,
                            elapsed_time=elapsed_time)
                
                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=line_timeout
                )
                
                # 检查是否有数据
                if not line:
                    # 没有数据，检查进程状态
                    if self.process.returncode is not None:
                        stderr_output = await self._read_stderr()
                        logger.error("MCP server process terminated", 
                            return_code=self.process.returncode,
                            stderr=stderr_output)
                        raise Exception(f"MCP server process terminated: {self.process.returncode}")
                    else:
                        # 进程还活着但没有数据，可能是暂时的
                        logger.debug("No data available, continuing...")
                        await asyncio.sleep(0.1)  # 短暂等待
                        continue
                
                line_str = line.decode().strip()
                
                # 跳过空行
                if not line_str:
                    continue
                
                # 记录非空行
                collected_lines.append(line_str)
                logger.debug("Received line", 
                            line_preview=line_str[:100],
                            total_lines=len(collected_lines))
                
                # 尝试解析JSON
                try:
                    data = json.loads(line_str)
                    logger.debug("Successfully parsed JSON", data_type=type(data).__name__)
                    
                    # 检查是否是有效的响应
                    if isinstance(data, dict):
                        # 标准JSON-RPC响应
                        if data.get("jsonrpc") == "2.0":
                            logger.info("Found JSON-RPC response", 
                                    response_id=data.get("id"),
                                    elapsed_time=elapsed_time)
                            return data  # 找到有效响应，退出循环
                        
                        # MCP工具响应格式
                        elif ("content" in data and isinstance(data.get("content"), list)) or \
                            ("isError" in data) or \
                            ("result" in data and "error" not in data and "jsonrpc" not in data):
                            logger.info("Found MCP response, wrapping as JSON-RPC",
                                    elapsed_time=elapsed_time)
                            return {  # 找到有效响应，退出循环
                                "jsonrpc": "2.0",
                                "id": getattr(self, '_current_request_id', 1),
                                "result": data
                            }
                        else:
                            # 是JSON但不是预期格式，继续读取
                            logger.debug("JSON found but not expected format")
                            
                except json.JSONDecodeError:
                    # 不是JSON，可能是日志，继续读取
                    logger.debug("Skipping non-JSON line", 
                            line_preview=line_str[:50])
                
                # 每读取20行输出一次状态
                if len(collected_lines) % 20 == 0:
                    logger.info("Still reading lines", 
                            lines_read=len(collected_lines),
                            elapsed_time=elapsed_time)
                
            except asyncio.TimeoutError:
                logger.debug("Timeout reading line", 
                            timeout=line_timeout,
                            elapsed_time=elapsed_time)
                
                # 检查进程状态
                if self.process.returncode is not None:
                    stderr_output = await self._read_stderr()
                    logger.error("Process died during timeout", 
                                return_code=self.process.returncode)
                    raise Exception(f"MCP server process died: {self.process.returncode}")
                
                # 超时但进程还活着，继续尝试
                continue
            
            except Exception as e:
                logger.error("Unexpected error while reading", error=str(e))
                break
        
        # 如果到这里，说明超时或出错了
        stderr_output = await self._read_stderr()
        elapsed_time = asyncio.get_event_loop().time() - start_time
        
        logger.error("Failed to get JSON-RPC response", 
                    elapsed_time=elapsed_time,
                    lines_collected=len(collected_lines),
                    process_alive=self.process.returncode is None)
        
        # 输出调试信息
        if collected_lines:
            logger.error("Sample collected lines",
                        first_3=collected_lines[:3],
                        last_3=collected_lines[-3:] if len(collected_lines) > 3 else [])
        
        if stderr_output:
            logger.error("Stderr output", stderr=stderr_output[:500])
        
        raise Exception(f"No JSON-RPC response received within {max_wait_time}s. "
                    f"Read {len(collected_lines)} lines. "
                    f"Process alive: {self.process.returncode is None}")

    
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
            
            # 检查进程状态
            if self.process.returncode is not None:
                stderr_output = await self._read_stderr()
                logger.error("Process died before response", 
                            return_code=self.process.returncode,
                            stderr=stderr_output)
                raise Exception(f"MCP server process died: {self.process.returncode}")
            
            # 读取响应 - 使用更合理的超时时间
            try:
                # 对于初始化等重要操作使用更长超时，普通操作使用较短超时
                # timeout = 30.0 if method in ["initialize", "tools/list"] else min(mcp_config.timeout, 30.0)
                
                # 对于初始化等重要操作使用更长超时
                if method in ["initialize", "tools/list"]:
                    timeout = 45.0  # 增加初始化超时时间
                elif method == "tools/call":
                    timeout = min(mcp_config.timeout * 2, 60.0)  # 工具调用使用较长超时
                else:
                    timeout = min(mcp_config.timeout, 30.0)
                
                response = await asyncio.wait_for(
                    self._read_json_response(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # 增强超时错误处理
                stderr_output = await self._read_stderr()
                process_alive = self.process.returncode is None
                
                logger.error("MCP server response timeout", 
                            method=method, 
                            timeout=timeout,
                            process_alive=process_alive,
                            stderr=stderr_output[:500] if stderr_output else None,
                            request_id=request_id)
                
                # 如果进程死了，抛出更具体的错误
                if not process_alive:
                    raise Exception(f"MCP server process died during {method} request (return code: {self.process.returncode})")
                else:
                    raise Exception(f"MCP server response timeout for method: {method} (timeout: {timeout}s)")
            
            # 检查错误
            if "error" in response:
                error = response["error"]
                logger.error("MCP server returned error", error=error, method=method)
                raise Exception(f"MCP error: {error.get('message', 'Unknown error')}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error("Error sending MCP request", 
                        method=method, 
                        error=str(e),
                        process_alive=self.process.returncode is None if self.process else False)
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
                "arguments": arguments,
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
        # 根据 MCP 服务器的实际期望，可能需要同时发送 query 和 name 参数
        arguments = {
            "query": query,      # 主要参数
            "name": query,       # 备用参数，以防服务器期望这个字段
            "limit": limit,
            "include_coauthors": True
        }
        
        result = await self.call_tool("search_authors", arguments)
        
        # 如果是 MCP 格式，提取实际数据
        if result.get("mcp_format") and "authors" in result:
            return {
                "authors": result["authors"],
                "count": result.get("count", len(result.get("authors", []))),
                "query": query,
                "limit": limit
            }
        
        return result
    
    async def get_author_details(self, author_id: str) -> Dict[str, Any]:
        """获取作者详情 - 便捷方法"""
        return await self.search_authors(query=author_id, limit=1)
    
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

