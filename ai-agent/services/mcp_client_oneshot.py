"""
MCP客户端服务 - 一次性调用版本（修复响应解析）
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
    """MCP客户端 - 一次性调用模式"""
    
    def __init__(self):
        self.available_tools: List[Dict[str, Any]] = []
        self._tools_loaded = False
    
    async def initialize(self):
        """初始化MCP客户端"""
        try:
            logger.info("Initializing MCP client (one-shot mode)")
            
            # 检查路径
            if not os.path.exists(mcp_config.mcp_cwd):
                raise Exception(f"MCP server directory not found: {mcp_config.mcp_cwd}")
            
            if not os.path.exists(mcp_config.mcp_command):
                raise Exception(f"MCP command not found: {mcp_config.mcp_command}")
            
            if not os.path.exists(mcp_config.mcp_python):
                raise Exception(f"MCP Python interpreter not found: {mcp_config.mcp_python}")
            
            # 测试连接并加载工具
            await self._load_available_tools()
            
            logger.info("MCP client initialized successfully", tools_count=len(self.available_tools))
            
        except Exception as e:
            logger.error("Failed to initialize MCP client", error=str(e))
            raise
    
    def _parse_mcp_responses(self, stdout: str) -> List[Dict[str, Any]]:
        """解析MCP服务器输出，提取所有JSON-RPC响应"""
        responses = []
        if not stdout:
            return responses
        
        # 按行解析输出
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                # 检查是否是 JSON-RPC 响应（包含 jsonrpc 字段）
                if isinstance(data, dict) and data.get("jsonrpc") == "2.0":
                    if "error" in data:
                        error = data["error"]
                        raise Exception(f"MCP error: {error.get('message', 'Unknown error')}")
                    elif "result" in data or "id" in data:
                        logger.debug("Found JSON-RPC response", response_id=data.get("id"))
                        responses.append(data)
            except json.JSONDecodeError:
                # 这行不是 JSON，可能是日志，跳过
                continue
        
        return responses
    
    async def _execute_mcp_session(self, requests: List[str], target_request_id: int = None) -> Dict[str, Any]:
        """执行完整的MCP会话（多个请求）"""
        try:
            logger.debug("Executing MCP session", request_count=len(requests))
            
            # 使用正确的命令
            command = mcp_config.actual_server_command
            logger.debug("Using command", command=command, cwd=mcp_config.mcp_cwd)
            
            # 启动进程，设置环境变量
            env = os.environ.copy()
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            env.pop('DEBUGPY_LAUNCHER_PORT', None)
            env.pop('PYDEVD_LOAD_VALUES_ASYNC', None)
            
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=mcp_config.mcp_cwd,
                env=env
            )
            
            # 准备输入 - 所有请求一次性发送
            input_data = '\n'.join(requests) + '\n'
            logger.debug("Sending requests", input_preview=input_data[:200])
            
            # 使用 communicate
            try:
                stdout, stderr = process.communicate(
                    input=input_data, 
                    timeout=mcp_config.timeout
                )
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise Exception("MCP server request timeout")
            
            logger.debug("Process completed", 
                        return_code=process.returncode,
                        stdout_lines=len(stdout.split('\n')) if stdout else 0,
                        has_stderr=bool(stderr))
            
            # 解析所有响应
            responses = self._parse_mcp_responses(stdout)
            logger.debug("Found responses", response_count=len(responses))
            
            # 如果指定了目标请求ID，返回对应的响应
            if target_request_id is not None:
                for response in responses:
                    if response.get("id") == target_request_id:
                        return response.get("result", {})
            
            # 否则返回最后一个有结果的响应
            for response in reversed(responses):
                if "result" in response:
                    return response.get("result", {})
            
            # 如果没有找到有效响应，但进程成功执行，返回空结果
            if process.returncode == 0 or process.returncode == 1:  # 1 可能是正常的退出码
                logger.warning("No JSON-RPC responses found, but process completed")
                return {}
            
            # 进程失败
            logger.error("MCP server failed", 
                       return_code=process.returncode,
                       stderr=stderr[:500] if stderr else None)
            raise Exception(f"MCP server failed with return code {process.returncode}")
            
        except Exception as e:
            logger.error("MCP session failed", error=str(e))
            raise
    
    async def _load_available_tools(self):
        """加载可用工具列表"""
        try:
            logger.info("Loading available tools...")
            
            # 构建完整的MCP会话请求
            requests = [
                # 1. Initialize
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "clientInfo": {"name": "ai-agent", "version": "1.0.0"}
                    }
                }),
                # 2. Initialized notification (no id for notifications)
                json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }),
                # 3. List tools
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                })
            ]
            
            logger.debug("Sending MCP initialization sequence")
            result = await self._execute_mcp_session(requests, target_request_id=2)
            logger.debug("Tools list result", result=result)
            
            self.available_tools = result.get("tools", [])
            self._tools_loaded = True
            
            logger.info("Available tools loaded", 
                       tools=[tool.get("name") for tool in self.available_tools])
                    
        except Exception as e:
            logger.error("Error loading available tools", error=str(e))
            # 设置默认工具列表（基于服务器日志输出）
            self.available_tools = [
                {"name": "search_authors", "description": "Search for authors"},
                {"name": "get_author_details", "description": "Get author details"},
                {"name": "get_author_papers", "description": "Get author papers"},
                {"name": "search_papers", "description": "Search for papers"},
                {"name": "get_paper_details", "description": "Get paper details"},
                {"name": "get_paper_citations", "description": "Get paper citations"},
                {"name": "get_citation_network", "description": "Get citation network"},
                {"name": "get_collaboration_network", "description": "Get collaboration network"},
                {"name": "get_trending_papers", "description": "Get trending papers"},
                {"name": "get_top_keywords", "description": "Get top keywords"}
            ]
            self._tools_loaded = True
            logger.info("Using default tools list", tools=[t["name"] for t in self.available_tools])
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        try:
            # 构建完整的MCP会话请求
            requests = [
                # 1. Initialize
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "clientInfo": {"name": "ai-agent", "version": "1.0.0"}
                    }
                }),
                # 2. Initialized notification
                json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }),
                # 3. Call tool
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                })
            ]
            
            logger.info("Calling MCP tool (one-shot)", tool_name=tool_name, arguments=arguments)
            
            result = await self._execute_mcp_session(requests, target_request_id=3)
            
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
        logger.info("MCP client cleanup completed (one-shot mode)")

# 全局MCP客户端实例
mcp_client_oneshot = MCPClient()
