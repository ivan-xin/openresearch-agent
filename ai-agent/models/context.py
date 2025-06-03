"""
上下文相关模型 - MVP版本
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class ConversationContext(BaseModel):
    """会话上下文模型"""
    conversation_id: str = Field(..., description="会话ID")
    recent_queries: List[str] = Field(default_factory=list, description="最近查询")
    search_history: List[Dict[str, Any]] = Field(default_factory=list, description="搜索历史")
    mentioned_entities: Dict[str, List[str]] = Field(default_factory=dict, description="提及的实体")
    research_focus: Optional[str] = Field(None, description="当前研究焦点")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "conv_123",
                "recent_queries": [
                    "transformer architecture",
                    "attention mechanism papers"
                ],
                "search_history": [
                    {
                        "query": "transformer",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "results_count": 25
                    }
                ],
                "mentioned_entities": {
                    "authors": ["Vaswani", "Attention"],
                    "papers": ["Attention Is All You Need"],
                    "concepts": ["transformer", "attention"]
                },
                "research_focus": "transformer_architecture"
            }
        }

class QueryContext(BaseModel):
    """查询上下文模型"""
    query: str = Field(..., description="用户查询")
    conversation_context: Optional[ConversationContext] = Field(None, description="会话上下文")
    previous_results: List[Dict[str, Any]] = Field(default_factory=list, description="之前的结果")
    
    class Config:
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "query": "找一些关于transformer的最新论文",
                "conversation_context": None,
                "previous_results": []
            }
        }
