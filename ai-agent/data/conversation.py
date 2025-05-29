"""
会话数据模型 - 扩展版
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class Conversation:
    """会话模型"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    messages: List['Message'] = field(default_factory=list)  # 添加消息列表
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息到会话"""
        from .message import Message
        
        message = Message(
            conversation_id=self.id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # 如果是第一条用户消息且没有标题，生成标题
        if not self.title and role == "user" and len([m for m in self.messages if m.role == "user"]) == 1:
            self.update_title_from_first_message(content)
    
    def get_recent_messages(self, limit: int = 10) -> List['Message']:
        """获取最近的消息"""
        return self.messages[-limit:] if self.messages else []
    
    def get_message_count(self) -> int:
        """获取消息总数"""
        return len(self.messages)
    
    def get_user_message_count(self) -> int:
        """获取用户消息数量"""
        return len([m for m in self.messages if m.role == "user"])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "message_count": self.get_message_count(),
            "messages": [msg.to_dict() for msg in self.messages] if hasattr(self, 'include_messages') else []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """从字典创建实例"""
        conversation = cls(
            id=data["id"],
            user_id=data["user_id"],
            title=data.get("title"),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) 
                      if isinstance(data["created_at"], str) 
                      else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
                      if isinstance(data["updated_at"], str)
                      else data["updated_at"],
            is_active=data.get("is_active", True)
        )
        
        # 如果包含消息数据，加载消息
        if "messages" in data:
            from .message import Message
            conversation.messages = [Message.from_dict(msg_data) for msg_data in data["messages"]]
        
        return conversation
    
    def update_title_from_first_message(self, first_message: str):
        """根据第一条消息生成标题"""
        if not self.title and first_message:
            # 简单的标题生成逻辑
            title = first_message[:50].strip()
            if len(first_message) > 50:
                title += "..."
            self.title = title
            self.updated_at = datetime.now()
