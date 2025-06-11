"""
会话管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional

from models.response import ConversationResponse, ConversationListResponse
from services.conversation_service import conversation_service
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/conversations/{user_id}", response_model=ConversationResponse)
async def get_user_conversation(
    user_id: str,
    include_messages: bool = Query(True, description="是否包含消息列表")
) -> ConversationResponse:
    """获取用户的会话"""
    try:
        logger.info("Getting user conversation", user_id=user_id, include_messages=include_messages)
        
        conversation = await conversation_service.get_user_conversation(user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if include_messages:
            conversation_with_messages = await conversation_service.get_conversation_with_messages(conversation.id)
            return ConversationResponse(
                conversation=conversation_with_messages.conversation,
                messages=conversation_with_messages.messages
            )
        else:
            return ConversationResponse(conversation=conversation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user conversation", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{user_id}")
async def delete_user_conversation(user_id: str):
    """删除用户会话"""
    try:
        logger.info("Deleting user conversation", user_id=user_id)
        
        conversation = await conversation_service.get_user_conversation(user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        success = await conversation_service.delete_conversation(conversation.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete user conversation", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/conversations/{user_id}/title")
async def update_user_conversation_title(
    user_id: str,
    title: str = Query(..., description="新的会话标题")
):
    """更新用户会话标题"""
    try:
        logger.info("Updating user conversation title", user_id=user_id, title=title)
        
        conversation = await conversation_service.get_user_conversation(user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        success = await conversation_service.update_conversation_title(conversation.id, title)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation title updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user conversation title", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{user_id}/messages")
async def get_user_conversation_messages(
    user_id: str,
    limit: int = Query(50, description="返回消息数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """获取用户会话消息列表"""
    try:
        logger.info("Getting user conversation messages", 
                   user_id=user_id, 
                   limit=limit, 
                   offset=offset)
        
        conversation = await conversation_service.get_user_conversation(user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = await conversation_service.get_messages(
            conversation_id=conversation.id,
            limit=limit,
            offset=offset
        )
        
        return {
            "messages": messages,
            "total": len(messages),
            "conversation_id": conversation.id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user conversation messages", 
                    user_id=user_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{user_id}/statistics")
async def get_user_conversation_statistics(user_id: str):
    """获取用户会话统计信息"""
    try:
        logger.info("Getting user conversation statistics", user_id=user_id)
        
        conversation = await conversation_service.get_user_conversation(user_id)
        if not conversation:
            return {
                "user_id": user_id,
                "statistics": {
                    "total_messages": 0,
                    "conversation_exists": False
                }
            }
        
        statistics = await conversation_service.get_statistics(user_id)
        
        return {
            "user_id": user_id,
            "statistics": statistics
        }
        
    except Exception as e:
        logger.error("Failed to get user conversation statistics", 
                    user_id=user_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
