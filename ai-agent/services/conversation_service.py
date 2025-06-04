"""
会话管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional

from ..models.conversation import (
    Conversation, 
    ConversationWithMessages, 
    CreateConversationDTO,
    Message
)
from ..models.response import ConversationResponse, ConversationListResponse
from ..services.conversation_service import conversation_service
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationDTO,
    user_id: str = Query(..., description="用户ID")
) -> ConversationResponse:
    """创建新会话"""
    try:
        logger.info("Creating new conversation", user_id=user_id, title=request.title)
        
        # 直接调用conversation_service
        conversation = await conversation_service.create_conversation(request)
        
        return ConversationResponse(
            conversation=conversation,
            messages=[]
        )
        
    except Exception as e:
        logger.error("Failed to create conversation", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=ConversationListResponse)
async def get_user_conversations(
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100),
    offset: int = Query(0, description="偏移量", ge=0)
) -> ConversationListResponse:
    """获取用户的会话列表"""
    try:
        logger.info("Getting user conversations", user_id=user_id, limit=limit, offset=offset)
        
        # 调用conversation_service获取会话列表
        conversations = await conversation_service.list_conversations(limit=limit, offset=offset)
        
        # 注意：当前conversation_service是全局的，没有按用户过滤
        # 在生产环境中需要添加用户过滤逻辑
        
        return ConversationListResponse(
            conversations=conversations,
            total=len(conversations),
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error("Failed to get user conversations", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="用户ID")
) -> ConversationResponse:
    """获取特定会话的详细信息"""
    try:
        logger.info("Getting conversation details", conversation_id=conversation_id, user_id=user_id)
        
        # 调用conversation_service获取会话详情
        conversation_data = await conversation_service.get_conversation_with_messages(conversation_id)
        
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse(
            conversation=conversation_data.conversation,
            messages=conversation_data.messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    title: str = Query(..., description="新标题", max_length=200),
    user_id: str = Query(..., description="用户ID")
):
    """更新会话标题"""
    try:
        logger.info("Updating conversation", conversation_id=conversation_id, user_id=user_id)
        
        # 调用conversation_service更新标题
        success = await conversation_service.update_conversation_title(conversation_id, title)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation updated successfully", "conversation_id": conversation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="用户ID")
):
    """删除会话"""
    try:
        logger.info("Deleting conversation", conversation_id=conversation_id, user_id=user_id)
        
        # 调用conversation_service删除会话
        success = await conversation_service.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete conversation", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=100),
    offset: int = Query(0, description="偏移量", ge=0)
):
    """获取会话的消息列表"""
    try:
        logger.info("Getting conversation messages", 
                   conversation_id=conversation_id, 
                   user_id=user_id,
                   limit=limit, 
                   offset=offset)
        
        # 调用conversation_service获取消息
        messages = await conversation_service.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "messages": messages,
            "conversation_id": conversation_id,
            "total": len(messages),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to get conversation messages", 
                    conversation_id=conversation_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/search")
async def search_conversations(
    query: str = Query(..., description="搜索关键词", min_length=1),
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(10, description="返回数量限制", ge=1, le=50)
):
    """搜索会话"""
    try:
        logger.info("Searching conversations", query=query, user_id=user_id, limit=limit)
        
        # 调用conversation_service搜索
        conversations = await conversation_service.search_conversations(query, limit)
        
        return {
            "conversations": conversations,
            "query": query,
            "total": len(conversations),
            "limit": limit
        }
        
    except Exception as e:
        logger.error("Failed to search conversations", query=query, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/statistics")
async def get_conversation_statistics(
    user_id: str = Query(..., description="用户ID")
):
    """获取会话统计信息"""
    try:
        logger.info("Getting conversation statistics", user_id=user_id)
        
        # 调用conversation_service获取统计
        stats = await conversation_service.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get conversation statistics", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
