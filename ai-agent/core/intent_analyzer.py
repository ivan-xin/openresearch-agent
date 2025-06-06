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
            # llm_response = await self.llm_service.analyze_intent(analysis_prompt, context)
            try:
                llm_response = await self.llm_service.analyze_intent(analysis_prompt)
            except Exception as llm_error:
                logger.warning("LLM intent analysis failed, falling back to keyword matching", 
                            error=str(llm_error))
                # 直接使用关键词匹配作为备选
                llm_response = {"analysis": ""}
            
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
            
            # 修复：只传递 IntentAnalysisResult 支持的参数
            return IntentAnalysisResult(
                primary_intent=primary_intent,
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
        # 改进的关键词映射 - 使用更灵活的匹配
        keyword_patterns = [
            # 论文搜索相关
            (["搜索", "论文"], "search_papers", 0.9),
            (["查找", "论文"], "search_papers", 0.9),
            (["论文", "搜索"], "search_papers", 0.9),
            (["找", "论文"], "search_papers", 0.8),
            (["相关论文"], "search_papers", 0.9),
            
            # 作者搜索相关
            (["搜索", "作者"], "search_authors", 0.9),
            (["查找", "作者"], "search_authors", 0.9),
            (["作者", "信息"], "get_author_details", 0.9),
            
            # 其他意图...
        ]
        
        # 默认值
        intent_type = "unknown"
        confidence = 0.3
        parameters = {}
        
        # 改进的匹配逻辑
        query_lower = query.lower()
        
        for keywords, mapped_intent, mapped_confidence in keyword_patterns:
            # 检查所有关键词是否都在查询中
            if all(keyword in query_lower for keyword in keywords):
                intent_type = mapped_intent
                confidence = mapped_confidence
                break
        
        # 如果没有精确匹配，尝试单个关键词匹配
        if intent_type == "unknown":
            single_keyword_mapping = {
                "论文": ("search_papers", 0.7),
                "作者": ("search_authors", 0.7),
                "搜索": ("search_papers", 0.6),  # 默认搜索为论文搜索
                "查找": ("search_papers", 0.6),
            }
            
            for keyword, (mapped_intent, mapped_confidence) in single_keyword_mapping.items():
                if keyword in query_lower:
                    intent_type = mapped_intent
                    confidence = mapped_confidence
                    break
        
        # 提取实体和参数
        entities = self._extract_entities(query)
        parameters = self._extract_parameters(query, intent_type)
        
        logger.info("Intent extraction result", 
            intent_type=intent_type,
            confidence=confidence,
            parameters=parameters)
        
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
            # 改进的关键词提取
            query_clean = query.lower()
            
            # 移除常见的停用词
            stop_words = ["搜索", "查找", "论文", "相关", "的", "关于"]
            for stop_word in stop_words:
                query_clean = query_clean.replace(stop_word, " ")
            
            # 提取剩余的关键词
            keywords = [word.strip() for word in query_clean.split() if word.strip()]
            if keywords:
                parameters["query"] = " ".join(keywords)
            else:
                # 如果没有提取到关键词，使用原始查询
                parameters["query"] = query
        
        elif intent_type == "search_authors":
            # 类似的作者名提取逻辑
            query_clean = query.lower()
            stop_words = ["搜索", "查找", "作者", "的"]
            for stop_word in stop_words:
                query_clean = query_clean.replace(stop_word, " ")
            
            author_name = query_clean.strip()
            if author_name:
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