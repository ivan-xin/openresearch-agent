"""
日志工具 - MVP版本
"""
import sys
import structlog
from typing import Any, Dict
from pathlib import Path

from app.configs.settings import settings

def configure_logging():
    """配置结构化日志"""
    
    # 配置structlog
    structlog.configure(
        processors=[
            # 添加时间戳
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            # 添加调用信息（仅在DEBUG模式下）
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FILENAME,
                           structlog.processors.CallsiteParameter.LINENO]
            ) if settings.debug else structlog.processors.CallsiteParameterAdder(parameters=[]),
            # JSON格式化（生产环境）或控制台格式化（开发环境）
            structlog.dev.ConsoleRenderer(colors=True) if settings.debug 
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str = None) -> structlog.BoundLogger:
    """获取日志记录器"""
    return structlog.get_logger(name)

class LoggerMixin:
    """日志混入类"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """获取当前类的日志记录器"""
        return structlog.get_logger(self.__class__.__name__)

def log_function_call(func_name: str, args: Dict[str, Any] = None, 
                     result: Any = None, error: Exception = None):
    """记录函数调用日志"""
    logger = get_logger("function_call")
    
    if error:
        logger.error(
            "Function call failed",
            function=func_name,
            args=args,
            error=str(error),
            error_type=type(error).__name__
        )
    else:
        logger.info(
            "Function call completed",
            function=func_name,
            args=args,
            result_type=type(result).__name__ if result is not None else None
        )

def log_api_request(method: str, path: str, status_code: int = None, 
                   duration: float = None, error: str = None):
    """记录API请求日志"""
    logger = get_logger("api")
    
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2) if duration else None
    }
    
    if error:
        log_data["error"] = error
        logger.error("API request failed", **log_data)
    else:
        logger.info("API request completed", **log_data)

# 初始化日志配置
configure_logging()
