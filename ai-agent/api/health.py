"""
健康检查API路由
"""
from fastapi import APIRouter, Depends
from app.api.dependencies import get_agent
from app.core.agent import AcademicAgent

router = APIRouter()

@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy", "service": "ai-agent"}

@router.get("/health/detailed")
async def detailed_health_check(agent: AcademicAgent = Depends(get_agent)):
    """详细健康检查"""
    try:
        agent_status = await agent.get_agent_status()
        return {
            "status": "healthy",
            "service": "ai-agent",
            "details": agent_status
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ai-agent",
            "error": str(e)
        }
