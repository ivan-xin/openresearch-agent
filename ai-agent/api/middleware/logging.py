"""
日志中间件
"""
import time
import uuid
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from ...utils.logger import get_logger

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # 将请求ID添加到请求状态中
        request.state.request_id = request_id
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                process_time=f"{process_time:.3f}s"
            )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录异常信息
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(exc),
                process_time=f"{process_time:.3f}s",
                exc_info=True
            )
            
            raise exc

def add_logging_middleware(app: FastAPI):
    """添加日志中间件"""
    app.add_middleware(LoggingMiddleware)
