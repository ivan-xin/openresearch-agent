"""
对话服务 - 数据库版本
"""
import uuid
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime

# API 模型
from models.conversation import (
    Conversation as ApiConversation, 
    Message as ApiMessage, 
    MessageRole, 
    ConversationWithMessages,
    CreateConversationDTO, 
    CreateMessageDTO
)

# 数据模型
from data.models.conversation import Conversation as DataConversation
from data.models.message import Message as DataMessage

from data.repositories.conversation_repository import conversation_repo
from data.repositories.message_repository import message_repo
from utils.id_generator import generate_conversation_id, generate_message_id

logger = structlog.get_logger()

class ConversationService:
    """对话服务 - 数据库版本"""
    
    def __init__(self):
        # 使用数据库存储，不再需要内存存储
        pass
    
    def _convert_data_to_api_conversation(self, data_conv: DataConversation) -> ApiConversation:
        """将数据模型转换为API模型"""
        return ApiConversation(
            id=data_conv.id,
            user_id=data_conv.user_id,
            title=data_conv.title,
            context=data_conv.context,
            is_active=data_conv.is_active,
            created_at=data_conv.created_at,
            updated_at=data_conv.updated_at,
            message_count=data_conv.message_count,
            metadata=data_conv.metadata
        )
    
    def _convert_data_to_api_message(self, data_msg: DataMessage) -> ApiMessage:
        """将数据模型转换为API模型"""
        return ApiMessage(
            id=data_msg.id,
            conversation_id=data_msg.conversation_id,
            role=MessageRole(data_msg.role),
            content=data_msg.content,
            created_at=data_msg.created_at,
            metadata=data_msg.metadata
        )
    
    async def create_conversation(self, dto: CreateConversationDTO, user_id: str) -> ApiConversation:
        """创建新会话"""
        try:
            # 生成会话ID
            conversation_id = generate_conversation_id()
            
            # 创建数据模型对象
            data_conversation = DataConversation(
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
            await conversation_repo.create(data_conversation)
            
            # 如果有初始消息，添加它
            if dto.initial_message:
                await self.add_message(CreateMessageDTO(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=dto.initial_message
                ))
                # 重新获取更新后的会话（包含消息计数）
                data_conversation = await conversation_repo.get_by_id(conversation_id)
            
            logger.info(
                "Conversation created successfully",
                conversation_id=conversation_id,
                title=data_conversation.title,
                user_id=user_id
            )
            
            # 转换为API模型返回
            return self._convert_data_to_api_conversation(data_conversation)
            
        except Exception as e:
            logger.error("Failed to create conversation", error=str(e))
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[ApiConversation]:
        """获取会话信息"""
        try:
            data_conversation = await conversation_repo.get_by_id(conversation_id)
            if not data_conversation:
                return None
                
            # 转换为API模型
            return self._convert_data_to_api_conversation(data_conversation)
        except Exception as e:
            logger.error("Failed to get conversation", conversation_id=conversation_id, error=str(e))
            return None
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Optional[ConversationWithMessages]:
        """获取包含消息的完整会话"""
        try:
            api_conversation = await self.get_conversation(conversation_id)
            if not api_conversation:
                return None
            
            data_messages = await message_repo.get_by_conversation_id(conversation_id)
            
            # 转换消息为API模型
            api_messages = [self._convert_data_to_api_message(data_msg) for data_msg in data_messages]
            
            return ConversationWithMessages(
                conversation=api_conversation,
                messages=api_messages
            )
        except Exception as e:
            logger.error("Failed to get conversation with messages", conversation_id=conversation_id, error=str(e))
            return None
    
    async def list_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> List[ApiConversation]:
        """获取用户的会话列表"""
        try:
            data_conversations = await conversation_repo.get_by_user_id(user_id, limit, offset)
            
            api_conversations = []
            for data_conv in data_conversations:
                # 如果没有标题，根据第一条用户消息生成
                if not data_conv.title or data_conv.title == "新的对话":
                    first_messages = await message_repo.get_by_conversation_id(data_conv.id, limit=5)
                    first_user_message = next((msg for msg in first_messages if msg.role == "user"), None)
                    if first_user_message:
                        new_title = first_user_message.content[:20] + ("..." if len(first_user_message.content) > 20 else "")
                        data_conv.title = new_title
                        await conversation_repo.update(data_conv)
                
                # 转换为API模型
                api_conversations.append(self._convert_data_to_api_conversation(data_conv))
            
            return api_conversations
            
        except Exception as e:
            logger.error("Failed to list conversations", user_id=user_id, error=str(e))
            return []
    
    async def add_message(self, dto: CreateMessageDTO) -> ApiMessage:
        """添加消息"""
        try:
            # 检查会话是否存在
            data_conversation = await conversation_repo.get_by_id(dto.conversation_id)
            if not data_conversation:
                raise ValueError(f"Conversation {dto.conversation_id} not found")
            
            # 生成消息ID
            message_id = generate_message_id()
            
            # 确保role是字符串
            role_str = dto.role.value if hasattr(dto.role, 'value') else str(dto.role)
            
            # 创建数据模型对象
            data_message = DataMessage(
                id=message_id,
                conversation_id=dto.conversation_id,
                role=role_str,
                content=dto.content,
                created_at=datetime.now(),
                metadata={}
            )
            
            # 保存消息到数据库
            await message_repo.create(data_message)
            
            # 更新会话统计
            data_conversation.message_count += 1
            data_conversation.updated_at = datetime.now()
            
            # 更新会话标题（如果是第一条用户消息且没有自定义标题）
            if (role_str == "user" and 
                data_conversation.message_count == 1 and 
                (not data_conversation.title or data_conversation.title == "新的对话")):
                data_conversation.title = dto.content[:20] + ("..." if len(dto.content) > 20 else "")
            
            await conversation_repo.update(data_conversation)
            
            logger.info(
                "Message added successfully",
                message_id=message_id,
                conversation_id=dto.conversation_id,
                role=role_str
            )
            
            # 转换为API模型返回
            return self._convert_data_to_api_message(data_message)
            
        except Exception as e:
            logger.error("Failed to add message", error=str(e))
            raise
    
    async def get_messages(self, conversation_id: str, 
                          limit: int = 50, offset: int = 0) -> List[ApiMessage]:
        """获取会话消息"""
        try:
            data_messages = await message_repo.get_by_conversation_id(conversation_id, limit, offset)
            return [self._convert_data_to_api_message(data_msg) for data_msg in data_messages]
        except Exception as e:
            logger.error("Failed to get messages", conversation_id=conversation_id, error=str(e))
            return []
    
    async def get_recent_messages(self, conversation_id: str, 
                                 count: int = 10) -> List[ApiMessage]:
        """获取最近的消息"""
        try:
            messages = await self.get_messages(conversation_id, limit=count)
            return messages[-count:] if messages else []
        except Exception as e:
            logger.error("Failed to get recent messages", conversation_id=conversation_id, error=str(e))
            return []
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """更新会话标题"""
        try:
            data_conversation = await conversation_repo.get_by_id(conversation_id)
            if not data_conversation:
                return False
            
            data_conversation.title = title
            data_conversation.updated_at = datetime.now()
            await conversation_repo.update(data_conversation)
            
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
    
    async def search_conversations(self, user_id: str, query: str, limit: int = 10) -> List[ApiConversation]:
        """搜索会话"""
        try:
            # 简单实现：获取用户所有会话，然后在内存中搜索
            # 生产环境应该在数据库层面实现全文搜索
            all_conversations = await self.list_conversations(user_id, limit=100)
            
            results = []
            query_lower = query.lower()
            
            for conversation in all_conversations:
                # 搜索标题
                if conversation.title and query_lower in conversation.title.lower():
                    results.append(conversation)
                    continue
                
                # 搜索消息内容
                messages = await self.get_messages(conversation.id, limit=50)
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
            conversations = await self.list_conversations(user_id, limit=1000)
            total_conversations = len(conversations)
            
            total_messages = 0
            for conversation in conversations:
                messages = await self.get_messages(conversation.id)
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
