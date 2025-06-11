"""
API包 - 路由和中间件
"""
# 修改为绝对导入，支持多版本
from api.v1.chat import router as chat_router_v1
from api.v1.conversation import router as conversation_router_v1
from api.v2.chat import router as chat_router_v2
from api.v2.conversation import router as conversation_router_v2
from .health import router as health_router

__all__ = [
    "chat_router_v1",
    "conversation_router_v1",
    "chat_router_v2", 
    "conversation_router_v2",
    "health_router"
]
