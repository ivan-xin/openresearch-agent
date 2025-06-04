"""
错误处理中间件
"""
from fastapi import FastAPI, HTTPException
from ...utils.exceptions import (
    BusinessError, 
    business_error_handler,
    http_error_handler,
    general_error_handler
)

def add_error_handlers(app: FastAPI):
    """添加错误处理器"""
    
    # 业务错误处理（包括AgentError等子类）
    app.add_exception_handler(BusinessError, business_error_handler)
    
    # HTTP错误处理
    app.add_exception_handler(HTTPException, http_error_handler)
    
    # 通用错误处理
    app.add_exception_handler(Exception, general_error_handler)
