"""
响应生成提示词模板
"""

class ResponsePrompts:
    """响应生成提示词类"""
    
    def __init__(self):
        self.response_strategies = {
            "paper_list": "论文列表展示",
            "paper_detail": "论文详情展示", 
            "author_list": "作者列表展示",
            "author_detail": "作者详情展示",
            "network_analysis": "网络分析结果",
            "trend_report": "趋势分析报告",
            "landscape_overview": "研究全景概览",
            "review_report": "论文审核报告",
            "generation_guide": "论文生成指导",
            "clarification": "澄清询问",
            "general": "通用回复"
        }
    
    def get_response_generation_prompt(self, strategy: str) -> str:
        """根据策略获取响应生成提示词"""
        base_prompt = self._get_base_response_prompt()
        strategy_prompt = self._get_strategy_specific_prompt(strategy)
        
        return f"{base_prompt}\n\n{strategy_prompt}"
    
    def _get_base_response_prompt(self) -> str:
        """获取基础响应生成提示词"""
        return """你是一个专业的学术研究AI助手，需要根据用户查询和分析结果生成自然、专业的回复。

                回复要求：
                1. 语言自然流畅，符合中文表达习惯
                2. 内容专业准确，体现学术研究的严谨性
                3. 结构清晰，重点突出
                4. 根据数据量适当调整详细程度
                5. 提供有价值的洞察和建议
                6. 保持友好和帮助性的语调

                请基于提供的结构化数据生成回复，确保信息准确且易于理解。"""
    
    def _get_strategy_specific_prompt(self, strategy: str) -> str:
        """获取特定策略的提示词"""
        strategy_prompts = {
            "paper_list": self._get_paper_list_prompt(),
            "paper_detail": self._get_paper_detail_prompt(),
            "author_list": self._get_author_list_prompt(),
            "author_detail": self._get_author_detail_prompt(),
            "network_analysis": self._get_network_analysis_prompt(),
            "trend_report": self._get_trend_report_prompt(),
            "landscape_overview": self._get_landscape_overview_prompt(),
            "review_report": self._get_review_report_prompt(),
            "generation_guide": self._get_generation_guide_prompt(),
            "clarification": self._get_clarification_prompt(),
            "general": self._get_general_prompt()
        }
        
        return strategy_prompts.get(strategy, strategy_prompts["general"])
    
    def _get_paper_list_prompt(self) -> str:
        """论文列表展示提示词"""
        return """针对论文搜索结果，请：
                1. 总结搜索结果的整体情况（总数、主要特点）
                2. 突出显示最相关或最重要的几篇论文
                3. 分析论文的时间分布、作者分布等特征
                4. 识别研究热点和趋势
                5. 提供进一步探索的建议

                格式建议：
                - 开头简要总结搜索结果
                - 重点介绍3-5篇代表性论文
                - 分析整体特征和趋势
                - 结尾提供后续建议"""
    
    def _get_paper_detail_prompt(self) -> str:
        """论文详情展示提示词"""
        return """针对论文详情，请：
                1. 清晰介绍论文的基本信息（标题、作者、发表时间等）
                2. 概括论文的主要贡献和创新点
                3. 分析论文的学术影响力（引用情况、重要性）
                4. 介绍作者背景和研究方向
                5. 提供相关研究的探索建议

                重点关注：
                - 论文的核心价值和贡献
                - 在该领域的地位和影响
                - 与其他相关工作的关系"""
    
    def _get_author_list_prompt(self) -> str:
        """作者列表展示提示词"""
        return """针对作者搜索结果，请：
                1. 总结找到的作者数量和整体特征
                2. 突出介绍最相关或最活跃的作者
                3. 分析作者的机构分布和研究领域
                4. 识别该领域的核心研究者
                5. 提供深入了解的建议

                关注要点：
                - 作者的学术声誉和影响力
                - 研究方向和专业领域
                - 机构背景和合作网络"""
    
    def _get_author_detail_prompt(self) -> str:
        """作者详情展示提示词"""
        return """针对作者详情，请：
                1. 全面介绍作者的学术背景和成就
                2. 概括主要研究方向和贡献
                3. 分析学术影响力和声誉指标
                4. 介绍重要的合作关系和网络
                5. 总结该作者在领域中的地位

                重点展示：
                - 代表性工作和重要贡献
                - 学术轨迹和发展历程
                - 在学术界的影响和地位"""
    
    def _get_network_analysis_prompt(self) -> str:
        """网络分析结果提示词"""
        return """针对网络分析结果，请：
                1. 解释网络的整体结构和特征
                2. 识别网络中的关键节点和核心群体
                3. 分析连接模式和关系强度
                4. 发现有趣的网络现象和规律
                5. 提供网络优化或利用的建议

                分析重点：
                - 网络的规模和密度
                - 中心性和影响力分布
                - 社区结构和聚类特征
                - 网络演化和发展趋势"""
    
    def _get_trend_report_prompt(self) -> str:
        """趋势分析报告提示词"""
        return """针对趋势分析结果，请：
                1. 总结研究领域的整体发展趋势
                2. 识别热点话题和新兴方向
                3. 分析技术演进和方法变化
                4. 预测未来可能的发展方向
                5. 提供研究机会和建议

                报告结构：
                - 趋势概览和主要发现
                - 热点分析和案例说明
                - 发展阶段和演进路径
                - 未来展望和研究建议"""
    
    def _get_landscape_overview_prompt(self) -> str:
        """研究全景概览提示词"""
        return """针对研究全景分析，请：
                1. 描绘该领域的整体研究图景
                2. 介绍主要研究方向和分支
                3. 分析不同方向的发展状况
                4. 识别研究空白和机会点
                5. 提供全面的研究指导

                全景要素：
                - 领域边界和核心问题
                - 主要研究范式和方法
                - 重要机构和研究团队
                - 发展历程和里程碑
                - 未来挑战和机遇"""
    
    def _get_review_report_prompt(self) -> str:
        """论文审核报告提示词"""
        return """针对论文审核，请：
                1. 客观评估论文的学术质量
                2. 分析论文的创新性和贡献
                3. 指出论文的优点和不足
                4. 提供具体的改进建议
                5. 给出综合评价和建议

                审核维度：
                - 研究问题的重要性和新颖性
                - 方法的科学性和合理性
                - 实验设计和结果分析
                - 写作质量和表达清晰度
                - 学术规范和引用完整性"""
    
    def _get_generation_guide_prompt(self) -> str:
        """论文生成指导提示词"""
        return """针对论文生成需求，请：
                1. 分析研究主题的可行性
                2. 提供论文结构和大纲建议
                3. 推荐相关文献和参考资料
                4. 指导研究方法和技术路线
                5. 提供写作技巧和注意事项

                指导内容：
                - 研究问题的定义和范围
                - 文献调研的方向和重点
                - 研究方法的选择和应用
                - 论文结构和章节安排
                - 写作规范和学术标准"""
    
    def _get_clarification_prompt(self) -> str:
        """澄清询问提示词"""
        return """当需要澄清用户意图时，请：
                1. 友好地说明理解上的困难
                2. 具体指出需要澄清的方面
                3. 提供多个选择或示例
                4. 引导用户提供更多信息
                5. 保持耐心和帮助性的态度

                澄清策略：
                - 重述理解的部分内容
                - 提出具体的澄清问题
                - 提供相关的选项或示例
                - 鼓励用户详细描述需求"""
    
    def _get_general_prompt(self) -> str:
        """通用回复提示词"""
        return """对于一般性查询，请：
                1. 根据可用信息提供最佳回复
                2. 承认信息的局限性
                3. 提供相关的背景知识
                4. 建议获取更多信息的途径
                5. 保持专业和有帮助的态度

                回复原则：
                - 基于事实，避免推测
                - 承认不确定性
                - 提供有价值的相关信息
                - 引导用户获得更好的帮助"""
    
    def get_error_response_prompt(self) -> str:
        """错误响应提示词"""
        return """当出现错误时，请：
                1. 友好地道歉并说明情况
                2. 简要解释可能的原因
                3. 提供解决问题的建议
                4. 鼓励用户重新尝试
                5. 保持积极和支持性的语调

                错误处理原则：
                - 承担责任，不推卸给用户
                - 提供具体的解决方案
                - 保持专业和友好的态度
                - 鼓励继续使用服务"""
    
    def get_follow_up_prompt(self, intent_type: str) -> str:
        """获取后续建议提示词"""
        follow_up_templates = {
            "search_papers": [
                "查看具体论文的详细信息和摘要",
                "分析这些论文的作者合作网络",
                "探索相关研究领域的发展趋势",
                "了解高被引论文的核心贡献"
            ],
            "search_authors": [
                "深入了解作者的研究轨迹和代表作",
                "分析作者之间的合作关系网络",
                "探索作者所在机构的研究实力",
                "关注作者的最新研究动态"
            ],
            "trend_analysis": [
                "深入分析特定技术方向的演进",
                "比较不同时间段的研究热点变化",
                "探索新兴研究方向的发展机会",
                "分析技术趋势对产业的影响"
            ],
            "citation_analysis": [
                "分析引用网络的演化模式",
                "识别具有突破性影响的关键论文",
                "探索跨领域的引用关系",
                "预测未来的研究发展方向"
            ]
        }
        
        suggestions = follow_up_templates.get(intent_type, [
            "进一步细化您的研究问题",
            "探索相关的研究领域",
            "了解最新的研究进展",
            "寻找合适的合作机会"
        ])
        
        return f"基于当前分析，建议您可以：\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
