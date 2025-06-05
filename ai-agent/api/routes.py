"""
API路由统一管理
"""
from fastapi import APIRouter

# 导入各个路由模块
from . import chat
from . import conversation
from . import health

# 创建主路由器
api_router = APIRouter()

# 注册各个子路由
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
    responses={
        200: {"description": "Success"},
        503: {"description": "Service Unavailable"}
    }
)

api_router.include_router(
    chat.router,
    # prefix="/chat", 
    tags=["chat"],
    responses={
        200: {"description": "Success"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"}
    }
)

api_router.include_router(
    conversation.router,
    prefix="/conversations",
    tags=["conversation"], 
    responses={
        200: {"description": "Success"},
        404: {"description": "Not Found"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"}
    }
)

# 导出主路由器
__all__ = ["api_router"]
