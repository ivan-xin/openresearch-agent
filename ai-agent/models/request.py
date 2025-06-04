"""
API请求模型 - MVP版本
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
import re

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(
        ..., 
        description="用户消息", 
        min_length=1, 
        max_length=2000
    )
    conversation_id: Optional[str] = Field(
        None, 
        description="会话ID，新会话时为空",
        max_length=100
    )
    user_id: str = Field(
        ...,
        description="用户ID",
        max_length=100
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="附加元数据"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """验证消息内容"""
        if not v.strip():
            raise ValueError('Message cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('conversation_id')
    @classmethod
    def validate_conversation_id(cls, v):
        """验证会话ID格式"""
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Conversation ID can only contain letters, numbers, underscores and hyphens')
        return v
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        """验证用户ID"""
        if not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "请帮我搜索关于Transformer架构的最新论文",
                "conversation_id": "conv_123456",
                "user_id": "user_789",
                "metadata": {
                    "source": "web_ui",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    }
