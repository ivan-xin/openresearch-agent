"""
会话数据模型
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
    context: Optional[str] = None  # 添加 context 字段
    is_active: bool = True  # 添加 is_active 字段
    message_count: int = 0  # 添加 message_count 字段
    metadata: Dict[str, Any] = field(default_factory=dict)  # 添加 metadata 字段
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "context": self.context,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            title=data.get("title"),
            context=data.get("context"),
            is_active=data.get("is_active", True),
            message_count=data.get("message_count", 0),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) 
                      if isinstance(data["created_at"], str) 
                      else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
                      if isinstance(data["updated_at"], str)
                      else data["updated_at"]
        )
    
    def update_title_from_first_message(self, first_message: str):
        """根据第一条消息生成标题"""
        if not self.title and first_message:
            # 简单的标题生成逻辑
            title = first_message[:50].strip()
            if len(first_message) > 50:
                title += "..."
            self.title = title
