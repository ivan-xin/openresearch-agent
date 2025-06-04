"""
数据仓库层 - 统一导出
"""

from .conversation_repository import ConversationRepository, conversation_repo
from .message_repository import MessageRepository, message_repo

# 导出仓库类和实例
__all__ = [
    "ConversationRepository",
    "MessageRepository",
    "conversation_repo", 
    "message_repo"
]

repositories = {
    "conversation": conversation_repo,
    "message": message_repo
}
