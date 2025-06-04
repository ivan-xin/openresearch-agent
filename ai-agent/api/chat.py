"""
聊天相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from ..models.request import ChatRequest
from ..models.response import ChatResponse
from ..models.conversation import CreateConversationDTO, CreateMessageDTO, MessageRole
from ..services.conversation_service import conversation_service
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """处理聊天请求"""
    try:
        agent = req.app.state.agent
        logger.info("Received chat request", 
                   user_id=request.user_id,
                   conversation_id=request.conversation_id)
        
        # 如果没有conversation_id，创建新会话
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_dto = CreateConversationDTO(
                title=None,  # 会根据第一条消息自动生成
                initial_message=request.message
            )
            conversation = await conversation_service.create_conversation(conversation_dto)
            conversation_id = conversation.id
        else:
            # 添加用户消息到现有会话
            await conversation_service.add_message(CreateMessageDTO(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=request.message
            ))
        
        # 调用agent处理查询
        result = await agent.process_query(
            query=request.message,
            conversation_id=conversation_id,
            user_id=request.user_id
        )
        
        # 添加AI回复到会话
        await conversation_service.add_message(CreateMessageDTO(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=result["content"]
        ))
        
        return ChatResponse(
            message=result["content"],
            conversation_id=conversation_id,
            query_id=result.get("query_id"),
            metadata=result.get("metadata", {}),
            processing_time=result.get("processing_time", 0)
        )
        
    except Exception as e:
        logger.error("Chat request failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """流式聊天响应（未来扩展）"""
    logger.info("Stream chat request received but not implemented", 
               conversation_id=request.conversation_id)
    
    raise HTTPException(
        status_code=501, 
        detail="Streaming chat not implemented yet. Please use /chat endpoint instead."
    )
