"""
AI Agent 应用入口
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# 导入统一的API路由
from api.routes import api_router
from api.middleware.error_handler import add_error_handlers
from api.middleware.logging import add_logging_middleware

# 数据层
from data import initialize_data_layer, cleanup_data_layer
from core import AcademicAgent

# 配置和工具
from configs.settings import settings
from utils.logger import get_logger

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
        # 1. 初始化数据层
        logger.info("Initializing data layer...")
        data_success = await initialize_data_layer()
        if not data_success:
            raise Exception("Failed to initialize data layer")
        logger.info("Data layer initialized successfully")
        
        # 2. 初始化Agent
        logger.info("Initializing AI Agent...")
        agent_instance = AcademicAgent()
        await agent_instance.initialize()
        app.state.agent = agent_instance
        logger.info("AI Agent initialized successfully")
        
        # 3. 应用就绪
        logger.info("AI Agent application started successfully")
        yield
        
    except Exception as e:
        logger.error("Failed to initialize AI Agent application", error=str(e))
        raise
    finally:
        # 关闭时清理
        logger.info("Shutting down AI Agent application...")
        
        # 清理Agent
        if agent_instance:
            try:
                await agent_instance.cleanup()
                logger.info("AI Agent cleanup completed")
            except Exception as e:
                logger.error("Error during agent cleanup", error=str(e))
        
        # 清理数据层
        try:
            await cleanup_data_layer()
            logger.info("Data layer cleanup completed")
        except Exception as e:
            logger.error("Error during data layer cleanup", error=str(e))
        
        logger.info("AI Agent application shutdown completed")

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Agent for Academic Research - MVP Version",
        debug=settings.debug,
        lifespan=lifespan,
        # API文档配置
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # 添加中间件（顺序很重要）
    add_error_handlers(app)
    add_logging_middleware(app)
    
    # 注册API路由 - 现在只需要一行！
    app.include_router(api_router, prefix="/api/v1")
    
    # 调试：打印所有路由
    if settings.debug:
        logger.info("=== Registered Routes ===")
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = list(route.methods)
                logger.info(f"  {methods} -> {route.path}")
        logger.info("========================")

    # 添加根路径处理
    @app.get("/", tags=["root"])
    async def root():
        """根路径 - 服务信息"""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs_url": "/docs" if settings.debug else "disabled",
            "api_prefix": "/api/v1"
        }
    
    # 添加API信息路径
    @app.get("/api", tags=["root"])
    async def api_info():
        """API信息"""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "api_version": "v1",
            "endpoints": {
                "health": "/api/v1/health",
                "chat": "/api/v1/chat", 
                "conversations": "/api/v1/conversations"
            }
        }
    
    return app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    # 开发环境运行配置
    uvicorn_config = {
        "app": "main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": settings.debug,
        "log_level": settings.log_level.lower(),
        "access_log": True,
        "use_colors": True,
    }
    
    # 如果是生产环境，添加额外配置
    if not settings.debug:
        uvicorn_config.update({
            "workers": 1,  # MVP版本使用单进程
            "reload": False,
            "access_log": False,
        })
    
    logger.info("Starting AI Agent server...")
    logger.info(f"Server will be available at: http://{settings.host}:{settings.port}")
    logger.info(f"API documentation: http://{settings.host}:{settings.port}/docs")
    
    uvicorn.run(**uvicorn_config)
