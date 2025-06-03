"""
简化的上下文管理器 - 基于PostgreSQL
"""
from typing import Optional, List
from data.models.conversation import Conversation
from data.models.message import Message
from .repositories.conversation_repository import conversation_repo
from .repositories.message_repository import message_repo
from data.database import db_manager
from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class ContextManager:
    """上下文管理器"""
    
    async def initialize(self):
        """初始化上下文管理器"""
        try:
            # 初始化数据库
            await db_manager.initialize()
            
            # 创建数据表
            await db_manager.create_tables()
            
            logger.info("Context manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize context manager", error=str(e))
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取会话及其消息"""
        try:
            # 获取会话基本信息
            conversation = await conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return None
            
            # 获取会话消息
            messages = await message_repo.get_by_conversation_id(
                conversation_id, 
                limit=settings.max_conversation_length
            )
            
            # 将消息添加到会话对象（这里需要扩展Conversation模型）
            conversation.messages = messages
            
            return conversation
            
        except Exception as e:
            logger.error("Failed to get conversation", conversation_id=conversation_id, error=str(e))
            return None
    
    async def create_conversation(self, user_id: str, conversation_id: Optional[str] = None) -> Conversation:
        """创建新会话"""
        try:
            conversation = Conversation(
                id=conversation_id or str(uuid.uuid4()),
                user_id=user_id
            )
            
            await conversation_repo.create(conversation)
            conversation.messages = []  # 初始化空消息列表
            
            logger.info("New conversation created", conversation_id=conversation.id, user_id=user_id)
            return conversation
            
        except Exception as e:
            logger.error("Failed to create conversation", user_id=user_id, error=str(e))
            raise
    
    async def update_conversation(self, conversation: Conversation):
        """更新会话"""
        try:
            # 更新会话基本信息
            await conversation_repo.update(conversation)
            
            # 如果有新消息，保存消息
            if hasattr(conversation, 'messages') and conversation.messages:
                # 获取已存在的消息数量
                existing_messages = await message_repo.get_by_conversation_id(conversation.id)
                existing_count = len(existing_messages)
                
                # 只保存新消息
                new_messages = conversation.messages[existing_count:]
                for message in new_messages:
                    message.conversation_id = conversation.id
                    await message_repo.create(message)
            
            logger.debug("Conversation updated", conversation_id=conversation.id)
            
        except Exception as e:
            logger.error("Failed to update conversation", conversation_id=conversation.id, error=str(e))
            raise
    
    async def add_message(self, conversation_id: str, role: str, content: str, metadata: dict = None) -> Message:
        """添加消息到会话"""
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            await message_repo.create(message)
            
            # 更新会话的更新时间
            conversation = await conversation_repo.get_by_id(conversation_id)
            if conversation:
                await conversation_repo.update(conversation)
            
            logger.debug("Message added", conversation_id=conversation_id, role=role)
            return message
            
        except Exception as e:
            logger.error("Failed to add message", conversation_id=conversation_id, error=str(e))
            raise
    
    async def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Conversation]:
        """获取用户的会话列表"""
        try:
            conversations = await conversation_repo.get_by_user_id(user_id, limit)
            
            # 为每个会话加载最近的几条消息作为预览
            for conversation in conversations:
                messages = await message_repo.get_by_conversation_id(conversation.id, limit=5)
                conversation.messages = messages
                
                # 如果没有标题，根据第一条用户消息生成
                if not conversation.title and messages:
                    first_user_message = next((msg for msg in messages if msg.role == "user"), None)
                    if first_user_message:
                        conversation.update_title_from_first_message(first_user_message.content)
                        await conversation_repo.update(conversation)
            
            return conversations
            
        except Exception as e:
            logger.error("Failed to get user conversations", user_id=user_id, error=str(e))
            raise
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        try:
            # 删除会话消息
            await message_repo.delete_by_conversation_id(conversation_id)
            
            # 软删除会话
            success = await conversation_repo.delete(conversation_id)
            
            if success:
                logger.info("Conversation deleted", conversation_id=conversation_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to delete conversation", conversation_id=conversation_id, error=str(e))
            return False
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """清理旧会话"""
        try:
            cleaned_count = await conversation_repo.cleanup_old_conversations(days)
            logger.info("Old conversations cleanup completed", cleaned_count=cleaned_count)
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup old conversations", error=str(e))
            return 0
    
    async def get_conversation_stats(self, user_id: str) -> dict:
        """获取用户会话统计"""
        try:
            conversations = await conversation_repo.get_by_user_id(user_id, limit=1000)
            
            total_conversations = len(conversations)
            total_messages = 0
            
            for conversation in conversations:
                messages = await message_repo.get_by_conversation_id(conversation.id)
                total_messages += len(messages)
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "average_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
            }
            
        except Exception as e:
            logger.error("Failed to get conversation stats", user_id=user_id, error=str(e))
            return {}
    
    async def cleanup(self):
        """清理资源"""
        try:
            await db_manager.close()
            logger.info("Context manager cleanup completed")
            
        except Exception as e:
            logger.error("Error during context manager cleanup", error=str(e))

