"""
健康检查API路由 - MVP版本
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import asyncio
import time
from datetime import datetime

from services.conversation_service import conversation_service
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy", 
        "service": "ai-agent",
        "version": "1.0.0-mvp",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health/detailed")
async def detailed_health_check(req: Request):
    """详细健康检查"""
    start_time = time.time()
    health_details = {
        "status": "healthy",
        "service": "ai-agent",
        "version": "1.0.0-mvp",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        # 检查Agent状态
        agent_status = await _check_agent_health(req)
        health_details["checks"]["agent"] = agent_status
        
        # 检查ConversationService状态
        conversation_status = await _check_conversation_service_health()
        health_details["checks"]["conversation_service"] = conversation_status
        
        # 检查内存使用情况
        memory_status = await _check_memory_health()
        health_details["checks"]["memory"] = memory_status
        
        # 计算总体健康状态
        all_healthy = all(
            check.get("status") == "healthy" 
            for check in health_details["checks"].values()
        )
        
        if not all_healthy:
            health_details["status"] = "degraded"
        
        # 添加响应时间
        health_details["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return health_details
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "ai-agent",
            "version": "1.0.0-mvp",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }

@router.get("/health/readiness")
async def readiness_check(req: Request):
    """就绪状态检查 - 用于K8s readiness probe"""
    try:
        # 检查关键组件是否就绪
        checks = []
        
        # 检查Agent是否可用
        if hasattr(req.app.state, 'agent') and req.app.state.agent:
            try:
                # 简单的agent调用测试
                await asyncio.wait_for(
                    _test_agent_basic_function(req.app.state.agent), 
                    timeout=5.0
                )
                checks.append(("agent", True))
            except Exception as e:
                logger.warning("Agent readiness check failed", error=str(e))
                checks.append(("agent", False))
        else:
            checks.append(("agent", False))
        
        # 检查ConversationService是否可用
        try:
            await asyncio.wait_for(
                _test_conversation_service_basic_function(),
                timeout=3.0
            )
            checks.append(("conversation_service", True))
        except Exception as e:
            logger.warning("ConversationService readiness check failed", error=str(e))
            checks.append(("conversation_service", False))
        
        # 所有关键组件都就绪才返回成功
        all_ready = all(status for _, status in checks)
        
        if all_ready:
            return {
                "status": "ready",
                "service": "ai-agent",
                "checks": dict(checks)
            }
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "service": "ai-agent", 
                    "checks": dict(checks)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "service": "ai-agent",
                "error": str(e)
            }
        )

@router.get("/health/liveness")
async def liveness_check():
    """存活状态检查 - 用于K8s liveness probe"""
    try:
        # 简单的存活检查，主要确保进程还在运行
        current_time = datetime.now()
        
        return {
            "status": "alive",
            "service": "ai-agent",
            "timestamp": current_time.isoformat(),
            "uptime_check": "ok"
        }
        
    except Exception as e:
        logger.error("Liveness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "dead",
                "service": "ai-agent",
                "error": str(e)
            }
        )

# 辅助函数
async def _check_agent_health(req: Request) -> Dict[str, Any]:
    """检查Agent健康状态"""
    try:
        if not hasattr(req.app.state, 'agent') or not req.app.state.agent:
            return {
                "status": "unhealthy",
                "error": "Agent not initialized"
            }
        
        agent = req.app.state.agent
        
        # 尝试获取agent状态
        if hasattr(agent, 'get_agent_status'):
            agent_status = await agent.get_agent_status()
            return {
                "status": "healthy",
                "details": agent_status
            }
        else:
            # 如果没有get_agent_status方法，进行基本检查
            return {
                "status": "healthy",
                "details": {
                    "type": type(agent).__name__,
                    "initialized": True
                }
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def _check_conversation_service_health() -> Dict[str, Any]:
    """检查ConversationService健康状态"""
    try:
        # 获取统计信息来验证服务状态
        stats = await conversation_service.get_statistics()
        
        return {
            "status": "healthy",
            "details": {
                "total_conversations": stats.get("total_conversations", 0),
                "total_messages": stats.get("total_messages", 0),
                "service_type": "in_memory_storage"
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def _check_memory_health() -> Dict[str, Any]:
    """检查内存使用情况"""
    try:
        import psutil
        import os
        
        # 获取当前进程的内存使用情况
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # 设置内存使用警告阈值
        warning_threshold = 80.0  # 80%
        critical_threshold = 95.0  # 95%
        
        status = "healthy"
        if memory_percent > critical_threshold:
            status = "critical"
        elif memory_percent > warning_threshold:
            status = "warning"
        
        return {
            "status": status,
            "details": {
                "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
                "memory_percent": round(memory_percent, 2),
                "warning_threshold": warning_threshold,
                "critical_threshold": critical_threshold
            }
        }
        
    except ImportError:
        # 如果psutil不可用，返回基本信息
        return {
            "status": "unknown",
            "details": {
                "error": "psutil not available for memory monitoring"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def _test_agent_basic_function(agent) -> bool:
    """测试Agent基本功能"""
    try:
        required_methods = ['process_query']
        for method in required_methods:
            if not hasattr(agent, method):
                raise Exception(f"Agent missing required method: {method}")
        
        return True
        
    except Exception as e:
        logger.error("Agent basic function test failed", error=str(e))
        raise

async def _test_conversation_service_basic_function() -> bool:
    """测试ConversationService基本功能"""
    try:
        # 测试基本的统计功能
        await conversation_service.get_statistics()
        return True
        
    except Exception as e:
        logger.error("ConversationService basic function test failed", error=str(e))
        raise
