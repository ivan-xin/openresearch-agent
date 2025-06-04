"""
MCP客户端服务 - MVP版本
"""
import asyncio
import aiohttp
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime

from configs.mcp_config import mcp_config
from models.task import Task, TaskResult, TaskStatus

logger = structlog.get_logger()

class MCPClient:
    """MCP客户端"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []
        self._tools_loaded = False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
    
    async def initialize(self):
        """初始化MCP客户端"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=mcp_config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 加载可用工具
            await self._load_available_tools()
            
            logger.info(
                "MCP client initialized successfully",
                base_url=mcp_config.base_url,
                tools_count=len(self.available_tools)
            )
            
        except Exception as e:
            logger.error("Failed to initialize MCP client", error=str(e))
            raise
    
    async def _load_available_tools(self):
        """加载可用工具列表"""
        try:
            url = f"{mcp_config.base_url}/tools"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.available_tools = data.get("tools", [])
                    self._tools_loaded = True
                    
                    logger.info(
                        "Available tools loaded",
                        tools=[tool.get("name") for tool in self.available_tools]
                    )
                else:
                    logger.warning(
                        "Failed to load tools",
                        status=response.status,
                        response=await response.text()
                    )
                    
        except Exception as e:
            logger.error("Error loading available tools", error=str(e))
            # 继续运行，但工具列表为空
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        try:
            if not self.session:
                raise RuntimeError("MCP client not initialized")
            
            # 构建请求数据
            request_data = {
                "name": tool_name,
                "arguments": arguments
            }
            
            url = f"{mcp_config.base_url}/tools/call"
            
            logger.info(
                "Calling MCP tool",
                tool_name=tool_name,
                arguments=arguments
            )
            
            # 发送请求
            async with self.session.post(url, json=request_data) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    logger.info(
                        "MCP tool call successful",
                        tool_name=tool_name,
                        status=response.status
                    )
                    return response_data
                else:
                    error_msg = response_data.get("error", f"HTTP {response.status}")
                    logger.error(
                        "MCP tool call failed",
                        tool_name=tool_name,
                        status=response.status,
                        error=error_msg
                    )
                    raise Exception(f"Tool call failed: {error_msg}")
                    
        except Exception as e:
            logger.error(
                "Error calling MCP tool",
                tool_name=tool_name,
                error=str(e)
            )
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
                    wait_time = mcp_config.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        "MCP tool call failed, retrying",
                        tool_name=tool_name,
                        attempt=attempt + 1,
                        wait_time=wait_time,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "MCP tool call failed after all retries",
                        tool_name=tool_name,
                        attempts=mcp_config.max_retries,
                        error=str(e)
                    )
        
        # 所有重试都失败了
        raise last_error
    
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
    
    async def get_author_details(self, author_id: str) -> Dict[str, Any]:
        """获取作者详情"""
        return await self.call_tool_with_retry(
            "get_author_details",
            {"author_id": author_id}
        )
    
    async def get_citation_network(self, paper_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取引用网络"""
        return await self.call_tool_with_retry(
            "get_citation_network",
            {"paper_id": paper_id, "depth": depth}
        )
    
    async def get_collaboration_network(self, author_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取合作网络"""
        return await self.call_tool_with_retry(
            "get_collaboration_network",
            {"author_id": author_id, "depth": depth}
        )
    
    async def get_research_trends(self, topic: str, time_range: str = "5y") -> Dict[str, Any]:
        """获取研究趋势"""
        return await self.call_tool_with_retry(
            "get_research_trends",
            {"topic": topic, "time_range": time_range}
        )
    
    async def analyze_research_landscape(self, field: str) -> Dict[str, Any]:
        """分析研究全景"""
        return await self.call_tool_with_retry(
            "analyze_research_landscape",
            {"field": field}
        )
    
    async def execute_task(self, task: Task) -> TaskResult:
        """执行MCP任务"""
        try:
            task.status = TaskStatus.RUNNING
            start_time = datetime.now()
            
            logger.info("Executing MCP task", task_id=task.id, task_name=task.name)
            
            # 获取任务参数
            tool_name = task.parameters.get("tool_name")
            arguments = task.parameters.get("arguments", {})
            
            if not tool_name:
                raise ValueError("Tool name is required for MCP task")
            
            # 调用工具
            result_data = await self.call_tool_with_retry(tool_name, arguments)
            
            # 计算执行时间
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            task.status = TaskStatus.COMPLETED
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                data=result_data,
                execution_time=execution_time,
                metadata={
                    "tool_name": tool_name,
                    "arguments": arguments
                }
            )
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            
            logger.error("MCP task execution failed", task_id=task.id, error=str(e))
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e)
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self.session:
                return {
                    "status": "unhealthy",
                    "error": "Client not initialized"
                }
            
            # 检查服务器连接
            url = f"{mcp_config.base_url}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return {
                        "status": "healthy",
                        "server_url": mcp_config.base_url,
                        "tools_loaded": self._tools_loaded,
                        "tools_count": len(self.available_tools)
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"Server returned status {response.status}"
                    }
                    
        except Exception as e:
            logger.error("MCP health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self.available_tools.copy()
    
    def is_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        return any(tool.get("name") == tool_name for tool in self.available_tools)
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.session:
                await self.session.close()
                logger.info("MCP client session closed successfully")
        except Exception as e:
            logger.error("Error during MCP client cleanup", error=str(e))

# 全局MCP客户端实例
mcp_client = MCPClient()

