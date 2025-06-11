"""
意图分析器 - 分析用户查询意图
"""
import json
import re
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
            logger.info("Parsing LLM response", response_keys=list(llm_response.keys()))
            
            # 1. 优先尝试解析LLM返回的结构化数据
            if "intent_type" in llm_response:
                # LLM直接返回了意图类型
                intent_type = llm_response["intent_type"]
                confidence = llm_response.get("confidence", 0.8)
                parameters = llm_response.get("parameters", {})
                entities = llm_response.get("entities", [])
                
                logger.info("Found structured intent in LLM response", 
                           intent_type=intent_type, 
                           confidence=confidence)
                
            elif "analysis" in llm_response:
                # LLM返回了分析文本，尝试从中提取结构化信息
                analysis_text = llm_response["analysis"]
                
                # 尝试解析JSON格式的分析结果
                try:
                    if isinstance(analysis_text, str):
                        # 尝试直接解析整个字符串为JSON
                        try:
                            analysis_data = json.loads(analysis_text)
                        except json.JSONDecodeError:
                            # 如果直接解析失败，尝试提取JSON部分
                            # 查找可能的JSON对象（以{开始，以}结束）
                            start_idx = analysis_text.find('{')
                            if start_idx != -1:
                                # 找到最后一个匹配的}
                                brace_count = 0
                                end_idx = -1
                                for i in range(start_idx, len(analysis_text)):
                                    if analysis_text[i] == '{':
                                        brace_count += 1
                                    elif analysis_text[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_idx = i
                                            break
                                
                                if end_idx != -1:
                                    json_str = analysis_text[start_idx:end_idx + 1]
                                    analysis_data = json.loads(json_str)
                                else:
                                    raise json.JSONDecodeError("No complete JSON found", analysis_text, 0)
                            else:
                                raise json.JSONDecodeError("No JSON found", analysis_text, 0)
                        
                        intent_type = analysis_data.get("intent_type", "unknown")
                        confidence = analysis_data.get("confidence", 0.7)
                        parameters = analysis_data.get("parameters", {})
                        entities = analysis_data.get("entities", [])
                        
                        logger.info("Parsed JSON from analysis text", 
                                   intent_type=intent_type, 
                                   confidence=confidence)
                    else:
                        # analysis_text 本身就是字典
                        intent_type = analysis_text.get("intent_type", "unknown")
                        confidence = analysis_text.get("confidence", 0.7)
                        parameters = analysis_text.get("parameters", {})
                        entities = analysis_text.get("entities", [])
                        
                except (json.JSONDecodeError, AttributeError) as e:
                    # JSON解析失败，回退到关键词匹配
                    logger.warning("Failed to parse JSON from analysis, falling back to keyword matching", 
                                 error=str(e))
                    intent_data = self._extract_intent_from_text(analysis_text, original_query)
                    intent_type = intent_data["intent_type"]
                    confidence = intent_data["confidence"]
                    parameters = intent_data["parameters"]
                    entities = intent_data["entities"]
            else:
                # 没有找到预期的字段，回退到关键词匹配
                logger.warning("No expected fields in LLM response, falling back to keyword matching")
                intent_data = self._extract_intent_from_text("", original_query)
                intent_type = intent_data["intent_type"]
                confidence = intent_data["confidence"] * 0.5  # 降低置信度
                parameters = intent_data["parameters"]
                entities = intent_data["entities"]
            
            # 2. 验证和标准化意图类型
            try:
                intent_type_enum = IntentType(intent_type)
                logger.info("Intent Type Enum: ", intent_type=intent_type_enum.value)
            except ValueError:
                logger.warning("Invalid intent type from LLM: ", intent_type=intent_type)
                # 尝试映射到已知的意图类型
                intent_type_enum = self._map_to_known_intent(intent_type, original_query)
                confidence *= 0.8  # 降低置信度
            
            # 3. 创建主要意图
            primary_intent = Intent(
                type=intent_type_enum,
                confidence=confidence,
                parameters=parameters
            )
            
            # 4. 检查是否需要澄清
            needs_clarification = self._should_clarify(intent_type_enum, confidence, parameters)
            clarification_questions = []
            if needs_clarification:
                clarification_questions = self._generate_clarification_questions({
                    "intent_type": intent_type_enum.value,
                    "confidence": confidence,
                    "parameters": parameters
                })
            
            logger.info("Intent parsing completed", 
                       intent_type=intent_type_enum.value,
                       confidence=confidence,
                       needs_clarification=needs_clarification)
            
            return IntentAnalysisResult(
                primary_intent=primary_intent,
                secondary_intents=[],
                needs_clarification=needs_clarification,
                clarification_questions=clarification_questions
            )
            
        except Exception as e:
            logger.error("Failed to parse LLM response", error=str(e))
            return self._create_fallback_intent(original_query)

    def _should_clarify(self, intent_type: IntentType, confidence: float, parameters: Dict[str, Any]) -> bool:
        """判断是否需要澄清"""
        # 置信度过低时需要澄清
        if confidence < 0.7:
            return True
        
        # 定义需要必要参数的意图类型
        intents_requiring_params = {
            IntentType.SEARCH_PAPERS: ["query"],
            IntentType.GET_PAPER_DETAILS: ["paper_id","paper_title", "title", "query"],  # 至少需要其中一个
            IntentType.GET_PAPER_CITATIONS: ["paper_id","paper_title", "title", "query"],
            IntentType.SEARCH_AUTHORS: ["query", "author_name"],
            IntentType.GET_AUTHOR_DETAILS: ["query", "author_name", "author_id"],
            IntentType.GET_AUTHOR_PAPERS: ["author_name", "author_id"],
        }
        
        # 不需要必要参数的意图类型
        intents_not_requiring_params = {
            IntentType.GENERAL_CHAT,
            IntentType.GET_TRENDING_PAPERS,  # 可以返回全领域热门
            IntentType.GET_TOP_KEYWORDS,     # 可以返回全领域关键词
            IntentType.CITATION_NETWORK,     # 可以提供通用网络分析
            IntentType.COLLABORATION_NETWORK,
            IntentType.UNKNOWN
        }
        
        # 如果是不需要参数的意图，直接返回False
        if intent_type in intents_not_requiring_params:
            return False
        
        # 检查需要参数的意图是否有必要参数
        if intent_type in intents_requiring_params:
            required_params = intents_requiring_params[intent_type]
            # 检查是否至少有一个必要参数存在且不为空
            has_required_param = any(
                parameters.get(param) and str(parameters.get(param)).strip() 
                for param in required_params
            )
            return not has_required_param
        
        # 对于其他意图，如果没有参数则需要澄清
        return not parameters or not any(v for v in parameters.values() if v)


    def _map_to_known_intent(self, intent_type: str, query: str) -> IntentType:
        """将未知的意图类型映射到已知的意图类型"""
        intent_mapping = {
            # 论文相关
            "paper_search": IntentType.SEARCH_PAPERS,
            "search_paper": IntentType.SEARCH_PAPERS,
            "find_papers": IntentType.SEARCH_PAPERS,
            "paper_details": IntentType.GET_PAPER_DETAILS,
            "get_paper": IntentType.GET_PAPER_DETAILS,
            "paper_info": IntentType.GET_PAPER_DETAILS,

            # 作者相关
            "author_search": IntentType.SEARCH_AUTHORS,
            "search_author": IntentType.SEARCH_AUTHORS,
            "find_authors": IntentType.SEARCH_AUTHORS,
            "author_details": IntentType.GET_AUTHOR_DETAILS,
            "get_author_details": IntentType.GET_AUTHOR_DETAILS,
            "author_profile": IntentType.GET_AUTHOR_DETAILS,
            "author_info": IntentType.GET_AUTHOR_DETAILS,
            "get_author": IntentType.SEARCH_AUTHORS,
            "author_papers": IntentType.GET_AUTHOR_PAPERS,
            "get_author_papers": IntentType.GET_AUTHOR_PAPERS,

            # 网络分析
            # "citation": IntentType.CITATION_NETWORK,
            # "citations": IntentType.CITATION_NETWORK,
            # "citation_network": IntentType.CITATION_NETWORK,
            # "citation_analysis": IntentType.CITATION_NETWORK,
            # "collaboration": IntentType.COLLABORATION_NETWORK,
            # "collaborations": IntentType.COLLABORATION_NETWORK,
            # "collaboration_network": IntentType.COLLABORATION_NETWORK,

            # 趋势分析
            "trending_papers": IntentType.GET_TRENDING_PAPERS,
            "trending": IntentType.GET_TRENDING_PAPERS,
            "trends": IntentType.GET_TRENDING_PAPERS,
            "trend": IntentType.GET_TRENDING_PAPERS,
            "research_trends": IntentType.GET_TRENDING_PAPERS,
            "research_landscape": IntentType.GET_TRENDING_PAPERS,
            "top_keywords": IntentType.GET_TOP_KEYWORDS,
            "keywords": IntentType.GET_TOP_KEYWORDS,

            # 通用
            "chat": IntentType.GENERAL_CHAT,
            "general": IntentType.GENERAL_CHAT,

            # 未知意图
            "unknown": IntentType.UNKNOWN,
            "unclear": IntentType.UNKNOWN,
        }
        
        # 尝试直接映射
        mapped_intent = intent_mapping.get(intent_type.lower())
        if mapped_intent:
            return mapped_intent
        
        # 尝试部分匹配
        for key, value in intent_mapping.items():
            if key in intent_type.lower() or intent_type.lower() in key:
                return value
        
        # 最后回退到关键词分析
        intent_data = self._extract_intent_from_text("", query)
        logger.info(f"map_to_known_intent ** Intent Data: {intent_data}")
        
        try:
            return IntentType(intent_data["intent_type"])
        except ValueError:
            return IntentType.UNKNOWN

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
            
            # 论文详情
            (["论文", "详情"], "get_paper_details", 0.9),
            (["论文", "信息"], "get_paper_details", 0.8),

            # 论文引用
            (["论文", "引用"], "get_paper_citations", 0.9),
            (["引用", "关系"], "get_paper_citations", 0.8),


            # 作者搜索相关
            (["搜索", "作者"], "search_authors", 0.9),
            (["查找", "作者"], "search_authors", 0.9),
            (["作者", "信息"], "search_authors", 0.9),
            (["作者", "搜索"], "search_authors", 0.9),
            (["作者", "详情"], "search_authors", 0.9),

            # 作者论文
            (["作者", "论文"], "get_author_papers", 0.9),
            (["作者", "研究"], "get_author_papers", 0.9),

            # 趋势分析
            (["热门", "论文"], "get_trending_papers", 0.9),
            (["趋势", "论文"], "get_trending_papers", 0.8),
            (["热门", "关键词"], "get_top_keywords", 0.9),
            (["关键词", "分析"], "get_top_keywords", 0.8),
            (["研究", "趋势"], "get_trending_papers", 0.7), 

            # 通用对话
            (["你好"], "general_chat", 0.9),
            (["聊天"], "general_chat", 0.8),
            (["对话"], "general_chat", 0.8),
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
                "引用": ("get_paper_citations", 0.6),
                "热门": ("get_trending_papers", 0.6),
                "趋势": ("get_trending_papers", 0.6),
                "关键词": ("get_top_keywords", 0.6),
                "合作": ("collaboration_network", 0.6),
                "网络": ("citation_network", 0.5),
                "详情": ("get_paper_details", 0.5),
                "信息": ("get_paper_details", 0.5),
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
            "计算机视觉", "数据挖掘", "神经网络", "强化学习",
            "区块链", "物联网", "云计算", "大数据", "算法",
            "软件工程", "数据库", "网络安全", "分布式系统"
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
            query_clean = query.lower()
            
            # 移除常见的停用词
            stop_words = ["搜索", "查找", "论文", "相关", "的", "关于", "有关", "找"]
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
            # 提取作者名称
            query_clean = query.lower()
            stop_words = ["搜索", "查找", "作者", "的", "信息", "详情"]
            for stop_word in stop_words:
                query_clean = query_clean.replace(stop_word, " ")
            
            author_name = query_clean.strip()
            if author_name:
                # parameters["author_name"] = author_name
                parameters["query"] = author_name  # 同时设置 query 参数
                
        elif intent_type == "get_paper_details":
            # 尝试提取论文ID或标题
            if "id:" in query.lower():
                paper_id = query.lower().split("id:")[1].strip()
                parameters["paper_id"] = paper_id
            else:
                # 如果没有明确的ID，将整个查询作为搜索条件
                parameters["query"] = query
                
        elif intent_type == "get_author_papers":
            # 提取作者ID或名称
            if "id:" in query.lower():
                author_id = query.lower().split("id:")[1].strip()
                parameters["author_id"] = author_id
            else:
                # 提取作者名称
                query_clean = query.lower()
                stop_words = ["作者", "论文", "的", "获取", "查看"]
                for stop_word in stop_words:
                    query_clean = query_clean.replace(stop_word, " ")
                
                author_name = query_clean.strip()
                if author_name:
                    parameters["author_name"] = author_name
                    
        elif intent_type == "get_paper_citations":
            # 提取论文ID
            if "id:" in query.lower():
                paper_id = query.lower().split("id:")[1].strip()
                parameters["paper_id"] = paper_id
            else:
                parameters["query"] = query
                
        elif intent_type == "get_trending_papers":
            # 提取研究领域
            entities = self._extract_entities(query)
            if entities:
                parameters["field"] = entities[0]  # 使用第一个识别的实体
            else:
                # 尝试从查询中提取领域信息
                query_clean = query.lower()
                stop_words = ["热门", "论文", "趋势", "的", "在", "领域"]
                for stop_word in stop_words:
                    query_clean = query_clean.replace(stop_word, " ")
                
                field = query_clean.strip()
                if field:
                    parameters["field"] = field
                    
        elif intent_type == "get_top_keywords":
            # 提取研究领域
            entities = self._extract_entities(query)
            if entities:
                parameters["field"] = entities[0]
            else:
                query_clean = query.lower()
                stop_words = ["热门", "关键词", "的", "在", "领域"]
                for stop_word in stop_words:
                    query_clean = query_clean.replace(stop_word, " ")
                
                field = query_clean.strip()
                if field:
                    parameters["field"] = field
        
        # 为所有意图添加通用参数
        parameters["original_query"] = query
        
        return parameters
    

    def _generate_clarification_questions(self, intent_data: Dict[str, Any]) -> List[str]:
        """生成澄清问题"""
        questions = []
        intent_type = intent_data.get("intent_type", "unknown")
        parameters = intent_data.get("parameters", {})
        
        if intent_type == "search_papers" and not parameters.get("query"):
            questions.append("您想搜索什么主题的论文？请提供更具体的关键词。")
            
        elif intent_type == "search_authors" and not parameters.get("author_name") and not parameters.get("query"):
            questions.append("您想查找哪位作者的信息？请提供作者姓名。")
            
        elif intent_type == "get_paper_details" and not parameters.get("paper_id") and not parameters.get("query"):
            questions.append("请提供论文的ID或标题，以便获取详细信息。")
            
        elif intent_type == "get_author_papers" and not parameters.get("author_id") and not parameters.get("author_name"):
            questions.append("请提供作者的ID或姓名，以便查看其论文列表。")
            
        elif intent_type == "get_paper_citations" and not parameters.get("paper_id") and not parameters.get("query"):
            questions.append("请提供论文的ID或标题，以便分析其引用关系。")
            
        elif intent_type == "get_trending_papers" and not parameters.get("field"):
            questions.append("您想查看哪个研究领域的热门论文？")
            
        elif intent_type == "get_top_keywords" and not parameters.get("field"):
            questions.append("您想查看哪个研究领域的热门关键词？")
            
        elif intent_type == "unknown":
            questions.append("抱歉，我没有完全理解您的需求。您是想要：")
            questions.append("1. 搜索论文？")
            questions.append("2. 查找作者信息？")
            questions.append("3. 分析引用关系？")
            questions.append("4. 查看研究趋势？")
            questions.append("请告诉我您的具体需求。")
        
        return questions