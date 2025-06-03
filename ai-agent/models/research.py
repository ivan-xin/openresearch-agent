"""
学术研究相关结果模型
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class PaperInfo(BaseModel):
    """论文信息模型"""
    id: str = Field(..., description="论文ID")
    title: str = Field(..., description="论文标题")
    authors: List[str] = Field(..., description="作者列表")
    year: Optional[int] = Field(None, description="发表年份")
    venue: Optional[str] = Field(None, description="发表会议/期刊")
    citations: Optional[int] = Field(None, description="引用次数")
    abstract: Optional[str] = Field(None, description="摘要")
    url: Optional[str] = Field(None, description="论文链接")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "paper_123",
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
                "year": 2017,
                "venue": "NeurIPS",
                "citations": 50000,
                "abstract": "The dominant sequence transduction models...",
                "url": "https://arxiv.org/abs/1706.03762"
            }
        }

class AuthorInfo(BaseModel):
    """作者信息模型"""
    id: str = Field(..., description="作者ID")
    name: str = Field(..., description="作者姓名")
    affiliation: Optional[str] = Field(None, description="所属机构")
    h_index: Optional[int] = Field(None, description="H指数")
    paper_count: Optional[int] = Field(None, description="论文数量")
    citation_count: Optional[int] = Field(None, description="总引用数")
    research_interests: List[str] = Field(default_factory=list, description="研究兴趣")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "author_123",
                "name": "Ashish Vaswani",
                "affiliation": "Google Research",
                "h_index": 45,
                "paper_count": 50,
                "citation_count": 100000,
                "research_interests": ["machine learning", "natural language processing", "attention mechanisms"]
            }
        }

class SearchResult(BaseModel):
    """搜索结果模型"""
    query: str = Field(..., description="搜索查询")
    total_count: int = Field(..., description="总结果数")
    papers: List[PaperInfo] = Field(default_factory=list, description="论文列表")
    authors: List[AuthorInfo] = Field(default_factory=list, description="作者列表")
    search_time: float = Field(..., description="搜索耗时")
    filters: Dict[str, Any] = Field(default_factory=dict, description="应用的过滤器")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "transformer attention mechanism",
                "total_count": 1500,
                "papers": [],
                "authors": [],
                "search_time": 1.2,
                "filters": {
                    "year_range": [2017, 2024],
                    "min_citations": 10
                }
            }
        }

class NetworkNode(BaseModel):
    """网络节点模型"""
    id: str = Field(..., description="节点ID")
    label: str = Field(..., description="节点标签")
    type: str = Field(..., description="节点类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="节点属性")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "paper_123",
                "label": "Attention Is All You Need",
                "type": "paper",
                "properties": {
                    "year": 2017,
                    "citations": 50000,
                    "venue": "NeurIPS"
                }
            }
        }

class NetworkEdge(BaseModel):
    """网络边模型"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    type: str = Field(..., description="边类型")
    weight: Optional[float] = Field(None, description="边权重")
    properties: Dict[str, Any] = Field(default_factory=dict, description="边属性")
    
    class Config:
        schema_extra = {
            "example": {
                "source": "paper_123",
                "target": "paper_456",
                "type": "citation",
                "weight": 1.0,
                "properties": {
                    "citation_context": "building upon the transformer architecture"
                }
            }
        }

class NetworkAnalysisResult(BaseModel):
    """网络分析结果模型"""
    nodes: List[NetworkNode] = Field(..., description="网络节点")
    edges: List[NetworkEdge] = Field(..., description="网络边")
    metrics: Dict[str, Any] = Field(..., description="网络指标")
    analysis_type: str = Field(..., description="分析类型")
    
    class Config:
        schema_extra = {
            "example": {
                "nodes": [],
                "edges": [],
                "metrics": {
                    "node_count": 50,
                    "edge_count": 75,
                    "density": 0.15,
                    "clustering_coefficient": 0.3
                },
                "analysis_type": "citation_network"
            }
        }

class TrendData(BaseModel):
    """趋势数据模型"""
    period: str = Field(..., description="时间周期")
    value: float = Field(..., description="数值")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    class Config:
        schema_extra = {
            "example": {
                "period": "2023",
                "value": 1500.0,
                "metadata": {
                    "paper_count": 1500,
                    "top_keywords": ["transformer", "attention", "bert"]
                }
            }
        }

class TrendAnalysisResult(BaseModel):
    """趋势分析结果模型"""
    topic: str = Field(..., description="分析主题")
    time_range: Dict[str, str] = Field(..., description="时间范围")
    trends: List[TrendData] = Field(..., description="趋势数据")
    analysis_type: str = Field(..., description="分析类型")
    insights: List[str] = Field(default_factory=list, description="分析洞察")
    
    class Config:
        schema_extra = {
            "example": {
                "topic": "transformer architecture",
                "time_range": {"start": "2017", "end": "2024"},
                "trends": [],
                "analysis_type": "research_trends",
                "insights": [
                    "Transformer论文数量在2020年后快速增长",
                    "注意力机制成为研究热点"
                ]
            }
        }
