"""
会话数据访问层
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from data.database import db_manager
from data.models.conversation import Conversation
from utils.logger import get_logger

logger = get_logger(__name__)

class ConversationRepository:
    """会话数据访问类"""
    
    async def create(self, conversation: Conversation) -> Conversation:
        """创建新会话"""
        try:
            async with db_manager.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO conversations (id, user_id, title, context, created_at, updated_at, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    conversation.id,
                    conversation.user_id,
                    conversation.title,
                    json.dumps(conversation.context),
                    conversation.created_at,
                    conversation.updated_at,
                    conversation.is_active
                )
            
            logger.info("Conversation created", conversation_id=conversation.id)
            return conversation
            
        except Exception as e:
            logger.error("Failed to create conversation", error=str(e))
            raise
    
    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """根据ID获取会话"""
        try:
            async with db_manager.get_connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, user_id, title, context, created_at, updated_at, is_active
                    FROM conversations
                    WHERE id = $1 AND is_active = TRUE
                    """,
                    conversation_id
                )
            
            if row:
                return Conversation(
                    id=str(row["id"]),  # 确保UUID转换为字符串
                    user_id=row["user_id"],
                    title=row["title"],
                    context=row["context"] or {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    is_active=row["is_active"]
                )
            
            return None
            
        except Exception as e:
            logger.error("Failed to get conversation", conversation_id=conversation_id, error=str(e))
            raise
    
    async def get_by_user_id(self, user_id: str, limit: int = 50) -> List[Conversation]:
        """获取用户的会话列表"""
        try:
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, title, context, created_at, updated_at, is_active
                    FROM conversations
                    WHERE user_id = $1 AND is_active = TRUE
                    ORDER BY updated_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit
                )
            
            conversations = []
            for row in rows:
                conversations.append(Conversation(
                    id=str(row["id"]),  # 确保UUID转换为字符串
                    user_id=row["user_id"],
                    title=row["title"],
                    context=row["context"] or {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    is_active=row["is_active"]
                ))
            
            return conversations
            
        except Exception as e:
            logger.error("Failed to get user conversations", user_id=user_id, error=str(e))
            raise
    
    async def update(self, conversation: Conversation) -> Conversation:
        """更新会话"""
        try:
            conversation.updated_at = datetime.now()
            
            async with db_manager.get_connection() as conn:
                result = await conn.execute(
                    """
                    UPDATE conversations
                    SET title = $2, context = $3, updated_at = $4
                    WHERE id = $1
                    """,
                    conversation.id,
                    conversation.title,
                    json.dumps(conversation.context),
                    conversation.updated_at
                )
            
            logger.debug("Conversation updated", conversation_id=conversation.id)
            return conversation
            
        except Exception as e:
            logger.error("Failed to update conversation", conversation_id=conversation.id, error=str(e))
            raise
    
    async def delete(self, conversation_id: str) -> bool:
        """删除会话（软删除）"""
        try:
            async with db_manager.get_connection() as conn:
                result = await conn.execute(
                    """
                    UPDATE conversations
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE id = $1
                    """,
                    conversation_id
                )
            
            # 检查是否更新了记录
            rows_affected = int(result.split()[-1]) if result.split() else 0
            success = rows_affected > 0
            
            if success:
                logger.info("Conversation deleted", conversation_id=conversation_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to delete conversation", conversation_id=conversation_id, error=str(e))
            raise
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """清理旧会话"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            async with db_manager.get_connection() as conn:
                result = await conn.execute(
                    """
                    UPDATE conversations
                    SET is_active = FALSE
                    WHERE updated_at < $1 AND is_active = TRUE
                    """,
                    cutoff_date
                )
            
            # 解析更新的行数
            rows_affected = int(result.split()[-1]) if result.split() else 0
            logger.info("Old conversations cleaned up", count=rows_affected, days=days)
            
            return rows_affected
            
        except Exception as e:
            logger.error("Failed to cleanup old conversations", error=str(e))
            raise

# 全局会话仓库实例
conversation_repo = ConversationRepository()
