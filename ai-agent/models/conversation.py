"""
会话管理相关模型 - MVP版本（简化）
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    """消息实体模型"""
    id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="所属会话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    
    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "id": "msg_123456",
                "conversation_id": "conv_789",
                "role": "user",
                "content": "请帮我搜索关于Transformer架构的最新论文",
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {}
            }
        }
    }


class Conversation(BaseModel):
    """会话实体模型"""
    id: str = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    message_count: int = Field(default=0, description="消息总数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "conv_123456",
                "title": "Transformer架构研究",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "message_count": 6,
                "metadata": {}
            }
        }
    }

class ConversationWithMessages(BaseModel):
    """包含消息的完整会话模型"""
    conversation: Conversation = Field(..., description="会话信息")
    messages: List[Message] = Field(..., description="消息列表")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation": {
                    "id": "conv_123456",
                    "title": "Transformer架构研究",
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "message_count": 2,
                    "metadata": {}
                },
                "messages": []
            }
        }
    }

# 简化的DTO
class CreateConversationDTO(BaseModel):
    """创建会话DTO"""
    title: Optional[str] = Field(None, description="会话标题", max_length=200)
    initial_message: Optional[str] = Field(None, description="初始消息", max_length=2000)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "深度学习论文研究",
                "initial_message": "我想了解最新的深度学习论文"
            }
        }
    }

class CreateMessageDTO(BaseModel):
    """创建消息DTO"""
    conversation_id: str = Field(..., description="会话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容", min_length=1, max_length=5000)
    
    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "example": {
                "conversation_id": "conv_123456",
                "role": "user",
                "content": "请搜索关于BERT模型的论文"
            }
        }
    }
