"""
异常处理 - MVP版本
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from utils.logger import get_logger
from utils.time_utils import now_ms

logger = get_logger("exceptions")

class BusinessError(Exception):
    """业务错误基类"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class AgentError(BusinessError):
    """Agent相关错误"""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code)

class ValidationError(BusinessError):
    """验证错误"""
    def __init__(self, message: str):
        super().__init__(message, 422)

async def business_error_handler(request: Request, exc: BusinessError):
    """业务错误处理"""
    logger.warning("Business error", error=exc.message, path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"message": exc.message, "type": type(exc).__name__},
            "timestamp": now_ms()
        }
    )

async def http_error_handler(request: Request, exc: HTTPException):
    """HTTP错误处理"""
    logger.warning("HTTP error", status=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"message": str(exc.detail), "type": "HTTPException"},
            "timestamp": now_ms()
        }
    )

async def general_error_handler(request: Request, exc: Exception):
    """通用错误处理"""
    logger.error("Unexpected error", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"message": "服务器内部错误", "type": "InternalError"},
            "timestamp": now_ms()
        }
    )
