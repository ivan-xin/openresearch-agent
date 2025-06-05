"""
对话服务 - 数据库版本
"""
import uuid
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.conversation import (
    Conversation, Message, MessageRole, ConversationWithMessages,
    CreateConversationDTO, CreateMessageDTO
)
from models.context import ConversationContext
from data.repositories.conversation_repository import conversation_repo
from data.repositories.message_repository import message_repo
from utils.id_generator import generate_conversation_id, generate_message_id
logger = structlog.get_logger()

class ConversationService:
    """对话服务 - 数据库版本"""
    
    def __init__(self):
        # 使用数据库存储，不再需要内存存储
        pass
    
    async def create_conversation(self, dto: CreateConversationDTO, user_id: str) -> Conversation:
        """创建新会话"""
        try:
            # 生成会话ID
            conversation_id = generate_conversation_id()
            
            # 创建会话对象
            conversation = Conversation(
                id=conversation_id,
                user_id=user_id,
                title=dto.title or "新的对话",
                context=getattr(dto, 'context', None),
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                message_count=0,
                metadata={}
            )
            
            # 保存到数据库
            await conversation_repo.create(conversation)
            
            # 如果有初始消息，添加它
            if dto.initial_message:
                await self.add_message(CreateMessageDTO(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=dto.initial_message
                ))
            
            logger.info(
                "Conversation created successfully",
                conversation_id=conversation_id,
                title=conversation.title,
                user_id=user_id
            )
            
            return conversation
            
        except Exception as e:
            logger.error("Failed to create conversation", error=str(e))
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取会话信息"""
        try:
            return await conversation_repo.get_by_id(conversation_id)
        except Exception as e:
            logger.error("Failed to get conversation", conversation_id=conversation_id, error=str(e))
            return None
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Optional[ConversationWithMessages]:
        """获取包含消息的完整会话"""
        try:
            conversation = await conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return None
            
            messages = await message_repo.get_by_conversation_id(conversation_id)
            
            return ConversationWithMessages(
                conversation=conversation,
                messages=messages
            )
        except Exception as e:
            logger.error("Failed to get conversation with messages", conversation_id=conversation_id, error=str(e))
            return None
    
    async def list_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Conversation]:
        """获取用户的会话列表"""
        try:
            conversations = await conversation_repo.get_by_user_id(user_id, limit, offset)
            
            # 为每个会话更新消息计数
            for conversation in conversations:
                messages = await message_repo.get_by_conversation_id(conversation.id, limit=1)
                conversation.message_count = len(await message_repo.get_by_conversation_id(conversation.id))
                
                # 如果没有标题，根据第一条用户消息生成
                if not conversation.title or conversation.title == "新的对话":
                    first_messages = await message_repo.get_by_conversation_id(conversation.id, limit=5)
                    first_user_message = next((msg for msg in first_messages if msg.role == MessageRole.USER), None)
                    if first_user_message:
                        new_title = first_user_message.content[:20] + ("..." if len(first_user_message.content) > 20 else "")
                        conversation.title = new_title
                        await conversation_repo.update(conversation)
            
            return conversations
            
        except Exception as e:
            logger.error("Failed to list conversations", user_id=user_id, error=str(e))
            return []
    
    async def add_message(self, dto: CreateMessageDTO) -> Message:
        """添加消息"""
        try:
            # 检查会话是否存在
            conversation = await conversation_repo.get_by_id(dto.conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {dto.conversation_id} not found")
            
            # 生成消息ID
            message_id = generate_message_id()
            
            # 创建消息对象
            message = Message(
                id=message_id,
                conversation_id=dto.conversation_id,
                role=dto.role,
                content=dto.content,
                timestamp=datetime.now(),
                metadata={}
            )
            
            # 保存消息到数据库
            await message_repo.create(message)
            
            # 更新会话统计
            conversation.message_count += 1
            conversation.updated_at = datetime.now()
            
            # 更新会话标题（如果是第一条用户消息且没有自定义标题）
            if (dto.role == MessageRole.USER and 
                conversation.message_count == 1 and 
                (not conversation.title or conversation.title == "新的对话")):
                conversation.title = dto.content[:20] + ("..." if len(dto.content) > 20 else "")
            
            await conversation_repo.update(conversation)
            
            logger.info(
                "Message added successfully",
                message_id=message_id,
                conversation_id=dto.conversation_id,
                role=dto.role.value
            )
            
            return message
            
        except Exception as e:
            logger.error("Failed to add message", error=str(e))
            raise
    
    async def get_messages(self, conversation_id: str, 
                          limit: int = 50, offset: int = 0) -> List[Message]:
        """获取会话消息"""
        try:
            return await message_repo.get_by_conversation_id(conversation_id, limit, offset)
        except Exception as e:
            logger.error("Failed to get messages", conversation_id=conversation_id, error=str(e))
            return []
    
    async def get_recent_messages(self, conversation_id: str, 
                                 count: int = 10) -> List[Message]:
        """获取最近的消息"""
        try:
            messages = await message_repo.get_by_conversation_id(conversation_id, limit=count)
            return messages[-count:] if messages else []
        except Exception as e:
            logger.error("Failed to get recent messages", conversation_id=conversation_id, error=str(e))
            return []
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """更新会话标题"""
        try:
            conversation = await conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return False
            
            conversation.title = title
            conversation.updated_at = datetime.now()
            await conversation_repo.update(conversation)
            
            logger.info(
                "Conversation title updated",
                conversation_id=conversation_id,
                new_title=title
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update conversation title", error=str(e))
            return False
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        try:
            # 删除会话消息
            await message_repo.delete_by_conversation_id(conversation_id)
            
            # 软删除会话
            success = await conversation_repo.delete(conversation_id)
            
            if success:
                logger.info("Conversation deleted successfully", conversation_id=conversation_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to delete conversation", conversation_id=conversation_id, error=str(e))
            return False
    
    async def get_conversation_history_for_llm(self, conversation_id: str, 
                                             max_messages: int = 10) -> List[Dict[str, str]]:
        """获取用于LLM的对话历史格式"""
        try:
            messages = await self.get_recent_messages(conversation_id, max_messages)
            
            # 转换为LLM格式
            llm_messages = []
            for message in messages:
                role = "user" if message.role == MessageRole.USER else "assistant"
                llm_messages.append({
                    "role": role,
                    "content": message.content
                })
            
            return llm_messages
            
        except Exception as e:
            logger.error("Failed to get conversation history for LLM", error=str(e))
            return []
    
    async def search_conversations(self, user_id: str, query: str, limit: int = 10) -> List[Conversation]:
        """搜索会话"""
        try:
            # 简单实现：获取用户所有会话，然后在内存中搜索
            # 生产环境应该在数据库层面实现全文搜索
            all_conversations = await conversation_repo.get_by_user_id(user_id, limit=100)
            
            results = []
            query_lower = query.lower()
            
            for conversation in all_conversations:
                # 搜索标题
                if conversation.title and query_lower in conversation.title.lower():
                    results.append(conversation)
                    continue
                
                # 搜索消息内容
                messages = await message_repo.get_by_conversation_id(conversation.id, limit=50)
                for message in messages:
                    if query_lower in message.content.lower():
                        results.append(conversation)
                        break
            
            return results[:limit]
            
        except Exception as e:
            logger.error("Failed to search conversations", error=str(e))
            return []
    
    async def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        try:
            conversations = await conversation_repo.get_by_user_id(user_id, limit=1000)
            total_conversations = len(conversations)
            
            total_messages = 0
            for conversation in conversations:
                messages = await message_repo.get_by_conversation_id(conversation.id)
                total_messages += len(messages)
            
            # 计算平均消息数
            avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "avg_messages_per_conversation": round(avg_messages, 2)
            }
            
        except Exception as e:
            logger.error("Failed to get statistics", error=str(e))
            return {}

# 全局对话服务实例
conversation_service = ConversationService()
