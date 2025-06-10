"""
意图分析相关模型 - 专注于学术研究场景
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass

class IntentType(Enum):
    """学术研究意图类型枚举"""
    # 论文相关
    SEARCH_PAPERS = "search_papers"
    GET_PAPER_DETAILS = "get_paper_details"
    GET_PAPER_CITATIONS = "get_paper_citations"

    # 作者相关
    SEARCH_AUTHORS = "search_authors"
    GET_AUTHOR_DETAILS = "search_authors"
    GET_AUTHOR_PAPERS = "get_author_papers"
    
    # 网络分析
    CITATION_NETWORK = "citation_network"
    COLLABORATION_NETWORK = "collaboration_network"
    
    # 趋势分析
    GET_TRENDING_PAPERS = "get_trending_papers"
    GET_TOP_KEYWORDS = "get_top_keywords"
    RESEARCH_TRENDS = "unknown"  # todo
    RESEARCH_LANDSCAPE = "unknown"  # todo

    # 通用对话
    GENERAL_CHAT = "general_chat"
    
    # 未知意图
    UNKNOWN = "unknown"

@dataclass
class Intent:
    """单个意图"""
    type: IntentType
    confidence: float = 0.0
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "confidence": self.confidence,
            "parameters": self.parameters
        }

class IntentAnalysisResult(BaseModel):
    """意图分析结果"""
    primary_intent: Intent
    confidence_threshold: float = Field(default=0.7)
    needs_clarification: bool = Field(default=False)
    clarification_question: Optional[str] = Field(default=None)
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def is_confident(self) -> bool:
        """判断是否有足够的置信度"""
        return self.primary_intent.confidence >= self.confidence_threshold
    
    @property
    def is_academic_query(self) -> bool:
        """判断是否为学术查询"""
        academic_intents = {
            IntentType.SEARCH_PAPERS,
            IntentType.GET_PAPER_DETAILS,
            IntentType.SEARCH_AUTHORS,
            IntentType.GET_AUTHOR_DETAILS,
            IntentType.CITATION_NETWORK,
            IntentType.COLLABORATION_NETWORK,
            IntentType.RESEARCH_TRENDS,
            IntentType.RESEARCH_LANDSCAPE
        }
        return self.primary_intent.type in academic_intents
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "primary_intent": self.primary_intent.to_dict(),
            "confidence_threshold": self.confidence_threshold,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "extracted_entities": self.extracted_entities,
            "is_confident": self.is_confident,
            "is_academic_query": self.is_academic_query
        }

# 预定义的意图模板
class IntentTemplates:
    """意图模板类"""
    
    @staticmethod
    def search_papers(query: str, confidence: float = 0.8) -> Intent:
        """搜索论文意图"""
        return Intent(
            type=IntentType.SEARCH_PAPERS,
            confidence=confidence,
            parameters={"query": query}
        )
    
    @staticmethod
    def search_authors(query: str, confidence: float = 0.8) -> Intent:
        """搜索作者意图"""
        return Intent(
            type=IntentType.SEARCH_AUTHORS,
            confidence=confidence,
            parameters={"query": query}
        )
    
    @staticmethod
    def get_author_details(query: str, confidence: float = 0.8) -> Intent:
        """获取作者详情意图 - 使用相同的search_authors工具"""
        return Intent(
            type=IntentType.GET_AUTHOR_DETAILS,
            confidence=confidence,
            parameters={
                "query": query,
                "detailed": True,  # 标记为详细查询
                "include_coauthors": True,
                "include_papers": True
            }
        )
    
    @staticmethod
    def get_paper_details(paper_id: str, confidence: float = 0.9) -> Intent:
        """获取论文详情意图"""
        return Intent(
            type=IntentType.GET_PAPER_DETAILS,
            confidence=confidence,
            parameters={"title": paper_id}
        )
    
    @staticmethod
    def general_chat(confidence: float = 0.6) -> Intent:
        """通用对话意图"""
        return Intent(
            type=IntentType.GENERAL_CHAT,
            confidence=confidence,
            parameters={}
        )
    
    @staticmethod
    def unknown(confidence: float = 0.3) -> Intent:
        """未知意图"""
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=confidence,
            parameters={}
        )
