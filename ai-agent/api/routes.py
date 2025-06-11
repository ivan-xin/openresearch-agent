"""
API路由统一管理 - 支持多版本
"""
from fastapi import APIRouter

# 导入各个版本的路由模块
from .v1 import chat as chat_v1
from .v1 import conversation as conversation_v1
from .v2 import chat as chat_v2
from .v2 import conversation as conversation_v2
from .health import router as health_router

# 创建版本路由器
api_v1_router = APIRouter()
api_v2_router = APIRouter()

# 注册 V1 路由
api_v1_router.include_router(
    health_router,
    prefix="/health",
    tags=["health-v1"],
    responses={
        200: {"description": "Success"},
        503: {"description": "Service Unavailable"}
    }
)

api_v1_router.include_router(
    chat_v1.router,
    # prefix="/chat",
    tags=["chat-v1"],
    responses={
        200: {"description": "Success"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"}
    }
)

api_v1_router.include_router(
    conversation_v1.router,
    # prefix="/conversations",
    tags=["conversation-v1"], 
    responses={
        200: {"description": "Success"},
        404: {"description": "Not Found"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"}
    }
)

# 注册 V2 路由
api_v2_router.include_router(
    health_router,  # health 路由在两个版本中共享
    prefix="/health",
    tags=["health-v2"],
    responses={
        200: {"description": "Success"},
        503: {"description": "Service Unavailable"}
    }
)

api_v2_router.include_router(
    chat_v2.router,
    # prefix="/chat",
    tags=["chat-v2"],
    responses={
        200: {"description": "Success"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"}
    }
)

api_v2_router.include_router(
    conversation_v2.router,
    # prefix="/conversations",
    tags=["conversation-v2"], 
    responses={
        200: {"description": "Success"},
        404: {"description": "Not Found"},
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"}
    }
)

# 导出版本路由器
__all__ = ["api_v1_router", "api_v2_router"]
