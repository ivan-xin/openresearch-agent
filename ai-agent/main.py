"""
AI Agent 应用入口
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.routes import chat, conversation, health
from app.api.middleware.error_handler import add_error_handlers
from app.api.middleware.logging import add_logging_middleware
from app.core.agent import AcademicAgent
from app.configs.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 全局Agent实例
agent_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent_instance
    
    # 启动时初始化
    logger.info("Starting AI Agent application")
    try:
        agent_instance = AcademicAgent()
        await agent_instance.initialize()
        app.state.agent = agent_instance
        logger.info("AI Agent initialized successfully")
        yield
    except Exception as e:
        logger.error("Failed to initialize AI Agent", error=str(e))
        raise
    finally:
        # 关闭时清理
        if agent_instance:
            await agent_instance.cleanup()
        logger.info("AI Agent application shutdown completed")

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # 添加中间件
    add_error_handlers(app)
    add_logging_middleware(app)
    
    # 注册路由
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
    app.include_router(conversation.router, prefix="/api/v1", tags=["conversation"])
    
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
