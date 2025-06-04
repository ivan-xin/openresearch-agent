"""
响应工具 - MVP版本
"""
from typing import Any, Dict
from fastapi import HTTPException
from utils.time_utils import now_ms

def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """成功响应"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": now_ms()
    }

def error_response(message: str, code: str = "ERROR") -> Dict[str, Any]:
    """错误响应"""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message
        },
        "timestamp": now_ms()
    }

def not_found_error(resource: str = "资源"):
    """404错误"""
    raise HTTPException(
        status_code=404,
        detail=f"{resource}不存在"
    )

def validation_error(message: str):
    """验证错误"""
    raise HTTPException(
        status_code=422,
        detail=message
    )

def internal_error(message: str = "服务器内部错误"):
    """500错误"""
    raise HTTPException(
        status_code=500,
        detail=message
    )
