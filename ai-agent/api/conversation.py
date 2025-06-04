"""
会话管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from models.response import ConversationResponse, ConversationListResponse
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/conversations", response_model=ConversationListResponse)
async def get_user_conversations(
    user_id: str = Query(..., description="用户ID"),
    req: Request = None
) -> ConversationListResponse:
    """获取用户的会话列表"""
    try:
        # 从应用状态获取agent
        agent = req.app.state.agent
        
        logger.info("Getting user conversations", user_id=user_id)
        
        conversations = await agent.get_user_conversations(user_id)
        
        return ConversationListResponse(
            conversations=conversations,
            total=len(conversations)
        )
        
    except Exception as e:
        logger.error("Failed to get user conversations", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    agent: AcademicAgent = Depends(get_agent)
) -> ConversationResponse:
    """获取特定会话的详细信息"""
    try:
        conversation = await agent.get_conversation_history(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse(**conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    agent: AcademicAgent = Depends(get_agent)
):
    """删除会话"""
    try:
        success = await agent.clear_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
