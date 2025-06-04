"""
API响应模型 - MVP版本
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str = Field(..., description="AI回复消息")
    conversation_id: str = Field(..., description="会话ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="响应元数据")
    processing_time: float = Field(0, description="处理时间（秒）")
    intent_type: Optional[str] = Field(None, description="识别的意图类型")
    confidence: Optional[float] = Field(None, description="意图识别置信度")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "我找到了以下关于Transformer架构的最新论文：\n\n1. **Attention Is All You Need** - Vaswani et al. (2017)\n   - 引用次数: 50,000+\n   - 摘要: 提出了完全基于注意力机制的Transformer模型...",
                "conversation_id": "conv_123456",
                "metadata": {
                    "sources_count": 5,
                    "search_terms": ["transformer", "attention mechanism"],
                    "tools_used": ["search_papers"]
                },
                "processing_time": 2.5,
                "intent_type": "search_papers",
                "confidence": 0.95
            }
        }
    }

class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str = Field(..., description="消息ID")
    role: str = Field(..., description="消息角色 (user/assistant)")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="消息时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "msg_123",
                "role": "user",
                "content": "请帮我搜索关于深度学习的论文",
                "timestamp": "2024-01-15T10:30:00Z",
                "metadata": {
                    "intent_type": "search_papers",
                    "confidence": 0.9
                }
            }
        }
    }

class ConversationResponse(BaseModel):
    """会话响应模型"""
    conversation_id: str = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    message_count: int = Field(..., description="消息总数")
    messages: List[MessageResponse] = Field(..., description="消息列表")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "conv_123",
                "title": "深度学习论文搜索",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "message_count": 4,
                "messages": []
            }
        }
    }

class ConversationSummary(BaseModel):
    """会话摘要模型"""
    conversation_id: str = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    message_count: int = Field(..., description="消息总数")
    last_message: Optional[str] = Field(None, description="最后一条消息")
    last_message_role: Optional[str] = Field(None, description="最后一条消息的角色")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "conv_123",
                "title": "深度学习论文搜索",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "message_count": 4,
                "last_message": "感谢您的帮助！",
                "last_message_role": "user"
            }
        }
    }

class ConversationListResponse(BaseModel):
    """会话列表响应模型"""
    conversations: List[ConversationSummary] = Field(..., description="会话列表")
    total: int = Field(..., description="总会话数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    has_more: bool = Field(default=False, description="是否有更多数据")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversations": [],
                "total": 25,
                "page": 1,
                "page_size": 20,
                "has_more": True
            }
        }
    }

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_type: str = Field(default="general_error", description="错误类型")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="错误时间")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "Intent analysis failed",
                "error_code": "INTENT_001",
                "error_type": "intent_error",
                "details": {
                    "query": "用户查询内容",
                    "confidence": 0.3
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: Optional[str] = Field(None, description="服务版本")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="检查时间")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "openresearch-agent",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "details": {
                    "mcp_server": "connected",
                    "llm_service": "ready"
                }
            }
        }
    }
