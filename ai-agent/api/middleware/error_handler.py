"""
错误处理中间件
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from app.utils.logger import get_logger
from app.utils.exceptions import AgentException

logger = get_logger(__name__)

def add_error_handlers(app: FastAPI):
    """添加错误处理器"""
    
    @app.exception_handler(AgentException)
    async def agent_exception_handler(request: Request, exc: AgentException):
        logger.error("Agent exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "type": "agent_error"}
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning("HTTP exception", status_code=exc.status_code, detail=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "type": "http_error"}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", error=str(exc), path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "type": "internal_error"}
        )
