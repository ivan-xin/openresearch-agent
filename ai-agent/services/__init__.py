"""
服务层包 - MVP版本
"""
from .llm_service import llm_service, LLMService
from .conversation_service import conversation_service, ConversationService

# MCP客户端 - 两种协议版本
from .mcp_client_http import mcp_client as mcp_client_http, MCPClient as MCPClientHTTP
from .mcp_client_stdio import mcp_client_stdio, MCPClient as MCPClientStdio
from .mcp_client_oneshot import mcp_client_oneshot,MCPClient   as MCPClientOneshot

# 默认使用 stdio 协议（推荐）
mcp_client = mcp_client_oneshot
MCPClient = MCPClientOneshot

__all__ = [
    # LLM服务
    "llm_service",
    "LLMService",
    
    # MCP客户端 - 默认 stdio 版本
    "mcp_client_http", 
    "MCPClient",
    
    # MCP客户端 - HTTP 版本（备用）
    "mcp_client_http",
    "MCPClientHTTP",
    
    # MCP客户端 - stdio 版本
    "mcp_client_stdio",
    "MCPClientStdio",
    
    # 对话服务
    "conversation_service",
    "ConversationService"
]
