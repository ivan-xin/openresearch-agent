"""
日志工具 - MVP版本
"""
import sys
import structlog
from typing import Any, Dict
from pathlib import Path

from configs.settings import settings

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

# 初始化日志配置
configure_logging()
