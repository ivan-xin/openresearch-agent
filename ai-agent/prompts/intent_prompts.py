"""
意图分析提示词模板
"""

class IntentPrompts:
    """意图分析提示词类"""
    
    def __init__(self):
        self.intent_types = {
            "search_papers": "搜索论文",
            "get_paper_details": "获取论文详情", 
            "search_authors": "搜索作者",
            "get_author_details": "获取作者详情",
            "citation_analysis": "引用分析",
            "collaboration_analysis": "合作关系分析",
            "trend_analysis": "研究趋势分析",
            "get_top_keywords": "获取热门话题或者关键词",
            "research_landscape": "研究全景分析",
            "paper_review": "论文审核",
            "paper_generation": "论文生成",
            "unknown": "未知意图"
        }
    
    def get_intent_analysis_prompt(self) -> str:
        """获取意图分析的基础提示词"""
        return f"""你是一个专业的学术研究AI助手，需要分析用户的查询意图。

                支持的意图类型包括：
                {self._format_intent_types()}

                请分析用户的查询，识别其主要意图，并提供以下信息：
                1. 意图类型（从上述类型中选择最匹配的）
                2. 置信度（0-1之间的数值）
                3. 关键参数（如搜索关键词、作者名称等）
                4. 实体信息（如研究领域、机构名称等）

                分析要求：
                - 准确识别用户的核心需求
                - 考虑学术研究的专业性
                - 提取有用的参数和实体
                - 如果意图不明确，标记需要澄清

                请用中文回复，格式清晰。"""
    
    def get_clarification_prompt(self, intent_type: str) -> str:
        """获取澄清问题的提示词"""
        clarification_templates = {
            "search_papers": "您想搜索什么主题或关键词的论文？请提供更具体的研究领域或关键词。",
            "search_authors": "您想查找哪位作者的信息？请提供作者的姓名或相关信息。",
            "citation_analysis": "您想分析哪篇论文或哪个研究领域的引用关系？",
            "collaboration_analysis": "您想分析哪些作者或机构之间的合作关系？",
            "trend_analysis": "您想了解哪个研究领域的发展趋势？请指定具体的研究方向。",
            "research_landscape": "您想了解哪个研究领域的整体情况？",
            "paper_review": "您想审核哪篇论文？请提供论文标题或相关信息。",
            "paper_generation": "您想生成什么主题的论文？请提供研究方向和具体要求。",
            "unknown": "抱歉，我没有完全理解您的需求。您能更具体地描述一下您想要做什么吗？"
        }
        
        return clarification_templates.get(intent_type, clarification_templates["unknown"])
    
    def get_context_prompt(self, recent_intents: list) -> str:
        """获取上下文相关的提示词"""
        if not recent_intents:
            return ""
        
        recent_intent_str = ", ".join([intent.get("type", "unknown") for intent in recent_intents[-3:]])
        return f"""
                上下文信息：
                用户最近的查询意图包括：{recent_intent_str}
                请结合这些上下文信息来更准确地分析当前查询的意图。
                """
    
    def get_entity_extraction_prompt(self) -> str:
        """获取实体提取的提示词"""
        return """请从用户查询中提取以下类型的实体：
                1. 研究领域/主题（如：机器学习、深度学习、自然语言处理等）
                2. 作者姓名
                3. 机构名称
                4. 期刊/会议名称
                5. 时间范围
                6. 论文标题或关键词

                请准确识别并分类这些实体。"""
    
    def get_parameter_extraction_prompt(self, intent_type: str) -> str:
        """根据意图类型获取参数提取提示词"""
        parameter_templates = {
            "search_papers": "请提取搜索相关的参数：查询关键词、研究领域、时间范围、作者限制等。",
            "search_authors": "请提取作者搜索相关的参数：作者姓名、机构、研究领域等。",
            "citation_analysis": "请提取引用分析相关的参数：目标论文、分析类型、时间范围等。",
            "collaboration_analysis": "请提取合作分析相关的参数：目标作者/机构、分析维度、时间范围等。",
            "trend_analysis": "请提取趋势分析相关的参数：研究领域、时间范围、分析粒度等。",
            "get_top_keywords": "请提取热门话题分析相关的参数：目标研究领域、时间范围、关键词数量、热度指标等。",
            "research_landscape": "请提取研究全景相关的参数：研究领域、分析维度、详细程度等。"
        }
        
        return parameter_templates.get(intent_type, "请提取查询中的关键参数。")
    
    def _format_intent_types(self) -> str:
        """格式化意图类型列表"""
        formatted_types = []
        for key, description in self.intent_types.items():
            formatted_types.append(f"- {key}: {description}")
        return "\n".join(formatted_types)
    
    def get_confidence_evaluation_prompt(self) -> str:
        """获取置信度评估提示词"""
        return """置信度评估标准：
                - 0.9-1.0: 意图非常明确，关键信息完整
                - 0.7-0.9: 意图较为明确，但可能缺少部分细节
                - 0.5-0.7: 意图基本明确，但需要进一步澄清
                - 0.3-0.5: 意图模糊，需要用户提供更多信息
                - 0.0-0.3: 意图不明确，无法准确判断用户需求
        请根据用户查询的明确程度和完整性来评估置信度。"""
    
    def get_multi_intent_prompt(self) -> str:
        """获取多意图分析提示词"""
        return """如果用户查询包含多个意图，请：
                1. 识别主要意图（最重要的需求）
                2. 识别次要意图（附加的需求）
                3. 分析意图之间的关联性
                4. 建议处理顺序

                例如："搜索机器学习相关论文，并分析其引用趋势"包含搜索论文和趋势分析两个意图。"""
