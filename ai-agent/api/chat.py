"""
聊天相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from  ..models.request import ChatRequest
from app.models.response import ChatResponse
from app.api.dependencies import get_agent
from app.core.agent import AcademicAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: AcademicAgent = Depends(get_agent)
) -> ChatResponse:
    """处理聊天请求"""
    try:
        logger.info("Received chat request", 
                   user_id=request.user_id,
                   conversation_id=request.conversation_id)
        
        result = await agent.process_query(
            query=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        
        return ChatResponse(
            message=result["content"],
            conversation_id=result["conversation_id"],
            query_id=result.get("query_id"),
            metadata=result.get("metadata", {}),
            processing_time=result.get("processing_time", 0)
        )
        
    except Exception as e:
        logger.error("Chat request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    agent: AcademicAgent = Depends(get_agent)
):
    """流式聊天响应（未来扩展）"""
    # TODO: 实现流式响应
    raise HTTPException(status_code=501, detail="Streaming not implemented yet")
