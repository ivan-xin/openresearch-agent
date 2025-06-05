"""
意图分析器 - 分析用户查询意图
"""
import json
from typing import Dict, Any, List
from models.intent import Intent, IntentType, IntentAnalysisResult
from services.llm_service import LLMService
from prompts import IntentPrompts
from utils.logger import get_logger

logger = get_logger(__name__)

class IntentAnalyzer:
    """意图分析器类"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.prompts = IntentPrompts()
    
    async def analyze(self, query: str, context: Dict[str, Any] = None) -> IntentAnalysisResult:
        """分析用户查询意图"""
        try:
            logger.info("Starting intent analysis", query=query)
            
            # 构建分析提示词
            analysis_prompt = self._build_analysis_prompt(query, context)
            
            # 调用LLM进行意图分析
            llm_response = await self.llm_service.analyze_intent(analysis_prompt, context)
            
            # 解析LLM响应
            intent_result = self._parse_llm_response(llm_response, query)
            
            logger.info("Intent analysis completed", 
                       intent_type=intent_result.primary_intent.type.value,
                       confidence=intent_result.primary_intent.confidence)
            
            return intent_result
            
        except Exception as e:
            logger.error("Intent analysis failed", error=str(e))
            # 返回默认的未知意图
            return self._create_fallback_intent(query)
    
    def _build_analysis_prompt(self, query: str, context: Dict[str, Any] = None) -> str:
        """构建意图分析提示词"""
        base_prompt = self.prompts.get_intent_analysis_prompt()
        
        # 添加上下文信息
        context_info = ""
        if context and context.get("recent_intents"):
            context_info = f"\n上下文：最近的意图包括 {context['recent_intents']}"
        
        return f"{base_prompt}\n\n用户查询：{query}{context_info}"
    
    def _parse_llm_response(self, llm_response: Dict[str, Any], original_query: str) -> IntentAnalysisResult:
        """解析LLM响应结果"""
        try:
            # 尝试解析JSON响应
            analysis_text = llm_response.get("analysis", "")
            
            # 简单的关键词匹配作为备选方案
            intent_data = self._extract_intent_from_text(analysis_text, original_query)
            
            # 创建主要意图 - 只使用基本参数
            primary_intent = Intent(
                type=IntentType(intent_data["intent_type"]),
                confidence=intent_data["confidence"],
                parameters=intent_data.get("parameters", {})
            )
            
            # 检查是否需要澄清
            needs_clarification = intent_data["confidence"] < 0.7
            clarification_questions = []
            if needs_clarification:
                clarification_questions = self._generate_clarification_questions(intent_data)
            
            return IntentAnalysisResult(
                primary_intent=primary_intent,
                secondary_intents=[],
                needs_clarification=needs_clarification,
                clarification_questions=clarification_questions
            )
            
        except Exception as e:
            logger.error("Failed to parse LLM response", error=str(e))
            return self._create_fallback_intent(original_query)

    def _create_fallback_intent(self, query: str) -> IntentAnalysisResult:
        """创建备选意图结果"""
        fallback_intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.1,
            parameters={}
        )
        
        return IntentAnalysisResult(
            primary_intent=fallback_intent,
            needs_clarification=True,
            clarification_questions=["抱歉，我没有完全理解您的需求。您能更具体地描述一下吗？"]
        )

    def _extract_intent_from_text(self, analysis_text: str, query: str) -> Dict[str, Any]:
        """从文本中提取意图信息"""
        # 关键词映射
        keyword_mapping = {
            "搜索论文": ("search_papers", 0.9),
            "查找论文": ("search_papers", 0.9),
            "论文搜索": ("search_papers", 0.9),
            "论文详情": ("get_paper_details", 0.9),
            "论文信息": ("get_paper_details", 0.8),
            "作者搜索": ("search_authors", 0.9),
            "查找作者": ("search_authors", 0.9),
            "作者信息": ("get_author_details", 0.9),
            "作者详情": ("get_author_details", 0.9),
            "引用关系": ("citation_analysis", 0.8),
            "引用分析": ("citation_analysis", 0.9),
            "合作关系": ("collaboration_analysis", 0.8),
            "合作网络": ("collaboration_analysis", 0.9),
            "研究趋势": ("trend_analysis", 0.9),
            "趋势分析": ("trend_analysis", 0.9),
            "研究全景": ("research_landscape", 0.8),
            "论文审核": ("paper_review", 0.9),
            "论文生成": ("paper_generation", 0.9)
        }
        
        # 默认值
        intent_type = "unknown"
        confidence = 0.3
        parameters = {}
        entities = []
        
        # 关键词匹配
        query_lower = query.lower()
        for keyword, (mapped_intent, mapped_confidence) in keyword_mapping.items():
            if keyword in query_lower:
                intent_type = mapped_intent
                confidence = mapped_confidence
                break
        
        # 提取实体（简单的实现）
        entities = self._extract_entities(query)
        
        # 提取参数
        parameters = self._extract_parameters(query, intent_type)
        
        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "parameters": parameters,
            "entities": entities
        }
    
    def _extract_entities(self, query: str) -> List[str]:
        """提取查询中的实体"""
        entities = []
        
        # 简单的实体识别（可以后续用NER模型替换）
        common_entities = [
            "机器学习", "深度学习", "人工智能", "自然语言处理",
            "计算机视觉", "数据挖掘", "神经网络", "强化学习"
        ]
        
        for entity in common_entities:
            if entity in query:
                entities.append(entity)
        
        return entities
    
    def _extract_parameters(self, query: str, intent_type: str) -> Dict[str, Any]:
        """根据意图类型提取参数"""
        parameters = {}
        
        if intent_type == "search_papers":
            # 提取搜索关键词
            if "关于" in query:
                keyword = query.split("关于")[1].split("的")[0].strip()
                parameters["query"] = keyword
            elif "搜索" in query:
                keyword = query.replace("搜索", "").replace("论文", "").strip()
                parameters["query"] = keyword
        
        elif intent_type == "search_authors":
            if "作者" in query:
                author_name = query.replace("搜索", "").replace("作者", "").strip()
                parameters["author_name"] = author_name
        
        return parameters
    
    def _generate_clarification_questions(self, intent_data: Dict[str, Any]) -> List[str]:
        """生成澄清问题"""
        questions = []
        
        if intent_data["intent_type"] == "search_papers" and not intent_data.get("parameters", {}).get("query"):
            questions.append("您想搜索什么主题的论文？")
        
        if intent_data["intent_type"] == "search_authors" and not intent_data.get("parameters", {}).get("author_name"):
            questions.append("您想查找哪位作者的信息？")
        
        return questions