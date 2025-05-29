"""
响应整合器 - 整合执行结果并生成最终响应
"""
from typing import Dict, Any, List
from models.intent import IntentAnalysisResult, IntentType
from services.llm_service import LLMService
from prompts.response_prompts import ResponsePrompts
from utils.logger import get_logger

logger = get_logger(__name__)

class ResponseIntegrator:
    """响应整合器类"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.prompts = ResponsePrompts()
    
    async def integrate(self, 
                       query: str,
                       intent_result: IntentAnalysisResult,
                       execution_results: Dict[str, Any],
                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """整合执行结果并生成最终响应"""
        try:
            logger.info("Starting response integration", intent=intent_result.primary_intent.type.value)
            
            # 1. 数据预处理
            processed_data = self._process_execution_results(execution_results)
            
            # 2. 根据意图类型选择响应策略
            response_strategy = self._select_response_strategy(intent_result.primary_intent.type)
            
            # 3. 生成结构化响应
            structured_response = await self._generate_structured_response(
                query, intent_result, processed_data, response_strategy
            )
            
            # 4. 生成自然语言响应
            natural_response = await self._generate_natural_response(
                query, structured_response, intent_result
            )
            
            # 5. 添加元数据和建议
            final_response = self._enhance_response(
                natural_response, structured_response, intent_result
            )
            
            logger.info("Response integration completed")
            return final_response
            
        except Exception as e:
            logger.error("Response integration failed", error=str(e))
            return self._create_error_response(str(e))
    
    def _process_execution_results(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """处理和清理执行结果"""
        processed = {}
        
        for task_id, result in execution_results.items():
            if isinstance(result, dict) and not result.get("error"):
                # 提取有用的数据
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and content:
                        processed[task_id] = content[0].get("text", "") if content[0].get("type") == "text" else content
                    else:
                        processed[task_id] = content
                else:
                    processed[task_id] = result
            else:
                logger.warning("Task result contains error", task_id=task_id, error=result.get("error"))
        
        return processed
    
    def _select_response_strategy(self, intent_type: IntentType) -> str:
        """根据意图类型选择响应策略"""
        strategy_mapping = {
            IntentType.SEARCH_PAPERS: "paper_list",
            IntentType.GET_PAPER_DETAILS: "paper_detail",
            IntentType.SEARCH_AUTHORS: "author_list",
            IntentType.GET_AUTHOR_DETAILS: "author_detail",
            IntentType.CITATION_ANALYSIS: "network_analysis",
            IntentType.COLLABORATION_ANALYSIS: "network_analysis",
            IntentType.TREND_ANALYSIS: "trend_report",
            IntentType.RESEARCH_LANDSCAPE: "landscape_overview",
            IntentType.PAPER_REVIEW: "review_report",
            IntentType.PAPER_GENERATION: "generation_guide",
            IntentType.UNKNOWN: "clarification"
        }
        
        return strategy_mapping.get(intent_type, "general")
    
    async def _generate_structured_response(self,
                                          query: str,
                                          intent_result: IntentAnalysisResult,
                                          processed_data: Dict[str, Any],
                                          strategy: str) -> Dict[str, Any]:
        """生成结构化响应"""
        structured_response = {
            "strategy": strategy,
            "data": processed_data,
            "summary": {},
            "insights": [],
            "recommendations": []
        }
        
        if strategy == "paper_list":
            structured_response.update(self._structure_paper_list_response(processed_data))
        elif strategy == "paper_detail":
            structured_response.update(self._structure_paper_detail_response(processed_data))
        elif strategy == "author_list":
            structured_response.update(self._structure_author_list_response(processed_data))
        elif strategy == "author_detail":
            structured_response.update(self._structure_author_detail_response(processed_data))
        elif strategy == "network_analysis":
            structured_response.update(self._structure_network_analysis_response(processed_data))
        elif strategy == "trend_report":
            structured_response.update(self._structure_trend_report_response(processed_data))
        elif strategy == "landscape_overview":
            structured_response.update(self._structure_landscape_response(processed_data))
        elif strategy == "review_report":
            structured_response.update(self._structure_review_response(processed_data))
        elif strategy == "generation_guide":
            structured_response.update(self._structure_generation_response(processed_data))
        
        return structured_response
    
    def _structure_paper_list_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化论文列表响应"""
        papers = []
        total_count = 0
        
        for task_result in data.values():
            if isinstance(task_result, dict) and "papers" in task_result:
                papers.extend(task_result["papers"])
                total_count = task_result.get("total", len(papers))
        
        return {
            "summary": {
                "total_papers": total_count,
                "returned_papers": len(papers),
                "top_authors": self._extract_top_authors(papers),
                "publication_years": self._extract_publication_years(papers)
            },
            "insights": [
                f"找到 {total_count} 篇相关论文",
                f"最活跃的作者包括：{', '.join(self._extract_top_authors(papers)[:3])}",
                f"主要发表年份：{self._get_year_distribution(papers)}"
            ],
            "recommendations": [
                "建议查看引用次数最高的论文",
                "可以进一步分析作者合作网络",
                "建议关注最新发表的论文"
            ]
        }
    
    def _structure_paper_detail_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化论文详情响应"""
        paper_details = {}
        
        for task_result in data.values():
            if isinstance(task_result, dict) and "paper" in task_result:
                paper_details = task_result["paper"]
                break
        
        return {
            "summary": {
                "title": paper_details.get("title", ""),
                "authors": paper_details.get("authors", []),
                "publication_year": paper_details.get("year", ""),
                "citation_count": paper_details.get("citations", 0),
                "venue": paper_details.get("venue", "")
            },
            "insights": [
                f"该论文发表于 {paper_details.get('year', '未知')} 年",
                f"被引用 {paper_details.get('citations', 0)} 次",
                f"作者包括：{', '.join(paper_details.get('authors', [])[:3])}"
            ],
            "recommendations": [
                "可以查看该论文的引用网络",
                "建议了解作者的其他相关工作",
                "可以分析该论文在领域中的影响力"
            ]
        }
    
    def _structure_author_list_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化作者列表响应"""
        authors = []
        
        for task_result in data.values():
            if isinstance(task_result, dict) and "authors" in task_result:
                authors.extend(task_result["authors"])
        
        return {
            "summary": {
                "total_authors": len(authors),
                "top_institutions": self._extract_top_institutions(authors),
                "research_areas": self._extract_research_areas(authors)
            },
            "insights": [
                f"找到 {len(authors)} 位相关作者",
                f"主要机构：{', '.join(self._extract_top_institutions(authors)[:3])}",
                f"研究领域分布：{self._get_area_distribution(authors)}"
            ],
            "recommendations": [
                "建议查看高产作者的详细信息",
                "可以分析作者间的合作关系",
                "关注不同机构的研究重点"
            ]
        }
    
    def _structure_network_analysis_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化网络分析响应"""
        network_data = {}
        
        for task_result in data.values():
            if isinstance(task_result, dict) and ("nodes" in task_result or "edges" in task_result):
                network_data = task_result
                break
        
        nodes_count = len(network_data.get("nodes", []))
        edges_count = len(network_data.get("edges", []))
        
        return {
            "summary": {
                "nodes_count": nodes_count,
                "edges_count": edges_count,
                "network_density": edges_count / (nodes_count * (nodes_count - 1)) if nodes_count > 1 else 0,
                "key_nodes": self._identify_key_nodes(network_data)
            },
            "insights": [
                f"网络包含 {nodes_count} 个节点和 {edges_count} 条边",
                f"网络密度为 {edges_count / (nodes_count * (nodes_count - 1)):.3f}" if nodes_count > 1 else "网络密度无法计算",
                f"关键节点：{', '.join(self._identify_key_nodes(network_data)[:3])}"
            ],
            "recommendations": [
                "建议关注网络中的核心节点",
                "可以分析网络的社区结构",
                "探索节点间的最短路径"
            ]
        }
    
    def _structure_trend_report_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化趋势报告响应"""
        trend_data = {}
        
        for task_result in data.values():
            if isinstance(task_result, dict) and "trends" in task_result:
                trend_data = task_result
                break
        
        return {
            "summary": {
                "time_period": trend_data.get("time_period", ""),
                "trending_topics": trend_data.get("trending_topics", []),
                "growth_areas": trend_data.get("growth_areas", []),
                "declining_areas": trend_data.get("declining_areas", [])
            },
            "insights": [
                f"分析时间段：{trend_data.get('time_period', '未指定')}",
                f"热门话题：{', '.join(trend_data.get('trending_topics', [])[:3])}",
                f"增长领域：{', '.join(trend_data.get('growth_areas', [])[:3])}"
            ],
            "recommendations": [
                "关注新兴研究方向",
                "考虑跨学科研究机会",
                "追踪技术发展趋势"
            ]
        }
    
    async def _generate_natural_response(self,
                                       query: str,
                                       structured_response: Dict[str, Any],
                                       intent_result: IntentAnalysisResult) -> str:
        """生成自然语言响应"""
        try:
            # 构建响应生成提示词
            response_prompt = self._build_response_prompt(
                query, structured_response, intent_result
            )
            
            # 调用LLM生成自然语言响应
            natural_response = await self.llm_service.generate_response(
                structured_response, query
            )
            
            return natural_response
            
        except Exception as e:
            logger.error("Natural response generation failed", error=str(e))
            return self._create_fallback_response(structured_response)
    
    def _build_response_prompt(self,
                             query: str,
                             structured_response: Dict[str, Any],
                             intent_result: IntentAnalysisResult) -> str:
        """构建响应生成提示词"""
        strategy = structured_response.get("strategy", "general")
        base_prompt = self.prompts.get_response_generation_prompt(strategy)
        
        context = f"""
用户查询：{query}
意图类型：{intent_result.primary_intent.type.value}
数据摘要：{structured_response.get('summary', {})}
关键洞察：{structured_response.get('insights', [])}
建议：{structured_response.get('recommendations', [])}
"""
        
        return f"{base_prompt}\n\n{context}"
    
    def _create_fallback_response(self, structured_response: Dict[str, Any]) -> str:
        """创建备选响应"""
        summary = structured_response.get("summary", {})
        insights = structured_response.get("insights", [])
        
        response_parts = ["根据您的查询，我找到了以下信息："]
        
        if summary:
            response_parts.append(f"数据概览：{summary}")
        
        if insights:
            response_parts.append("主要发现：")
            for insight in insights[:3]:
                response_parts.append(f"• {insight}")
        
        return "\n\n".join(response_parts)
    
    def _enhance_response(self,
                         natural_response: str,
                         structured_response: Dict[str, Any],
                         intent_result: IntentAnalysisResult) -> Dict[str, Any]:
        """增强响应，添加元数据和建议"""
        return {
            "content": natural_response,
            "metadata": {
                "intent_type": intent_result.primary_intent.type.value,
                "confidence": intent_result.primary_intent.confidence,
                "strategy": structured_response.get("strategy"),
                "data_sources": list(structured_response.get("data", {}).keys())
            },
            "structured_data": structured_response.get("summary", {}),
            "insights": structured_response.get("insights", []),
            "recommendations": structured_response.get("recommendations", []),
            "follow_up_suggestions": self._generate_follow_up_suggestions(intent_result)
        }
    
    def _generate_follow_up_suggestions(self, intent_result: IntentAnalysisResult) -> List[str]:
        """生成后续建议"""
        suggestions = []
        intent_type = intent_result.primary_intent.type
        
        if intent_type == IntentType.SEARCH_PAPERS:
            suggestions = [
                "查看具体论文的详细信息",
                "分析作者的其他工作",
                "探索相关的研究趋势"
            ]
        elif intent_type == IntentType.SEARCH_AUTHORS:
            suggestions = [
                "查看作者的详细资料",
                "分析作者的合作网络",
                "了解作者的研究轨迹"
            ]
        elif intent_type == IntentType.TREND_ANALYSIS:
            suggestions = [
                "深入分析特定研究方向",
                "比较不同时间段的趋势",
                "探索跨领域的研究机会"
            ]
        
        return suggestions
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "content": f"抱歉，处理您的请求时遇到了问题：{error_message}。请稍后重试或重新表述您的问题。",
            "metadata": {
                "error": True,
                "error_message": error_message
            },
            "recommendations": [
                "请检查您的查询是否清晰明确",
                "尝试使用不同的关键词",
                "如果问题持续，请联系技术支持"
            ]
        }
    
    # 辅助方法
    def _extract_top_authors(self, papers: List[Dict]) -> List[str]:
        """提取热门作者"""
        author_counts = {}
        for paper in papers:
            for author in paper.get("authors", []):
                author_counts[author] = author_counts.get(author, 0) + 1
        
        return sorted(author_counts.keys(), key=lambda x: author_counts[x], reverse=True)
    
    def _extract_publication_years(self, papers: List[Dict]) -> List[int]:
        """提取发表年份"""
        years = []
        for paper in papers:
            if "year" in paper:
                years.append(paper["year"])
        return sorted(set(years), reverse=True)
    
    def _get_year_distribution(self, papers: List[Dict]) -> str:
        """获取年份分布描述"""
        years = self._extract_publication_years(papers)
        if not years:
            return "年份信息不可用"
        
        if len(years) == 1:
            return f"{years[0]}年"
        else:
            return f"{years[-1]}-{years[0]}年"
    
    def _extract_top_institutions(self, authors: List[Dict]) -> List[str]:
        """提取热门机构"""
        institutions = []
        for author in authors:
            if "affiliation" in author:
                institutions.append(author["affiliation"])
        
        return list(set(institutions))[:5]  # 返回前5个机构
    
    def _extract_research_areas(self, authors: List[Dict]) -> List[str]:
        """提取研究领域"""
        areas = []
        for author in authors:
            if "research_areas" in author:
                areas.extend(author["research_areas"])
        
        return list(set(areas))[:5]  # 返回前5个领域
    
    def _get_area_distribution(self, authors: List[Dict]) -> str:
        """获取研究领域分布描述"""
        areas = self._extract_research_areas(authors)
        if not areas:
            return "领域信息不可用"
        
        return f"{', '.join(areas[:3])}" + ("等" if len(areas) > 3 else "")
    
    def _identify_key_nodes(self, network_data: Dict[str, Any]) -> List[str]:
        """识别网络中的关键节点"""
        nodes = network_data.get("nodes", [])
        if not nodes:
            return []
        
        # 简单按度数排序（如果有度数信息）
        if isinstance(nodes[0], dict) and "degree" in nodes[0]:
            sorted_nodes = sorted(nodes, key=lambda x: x.get("degree", 0), reverse=True)
            return [node.get("id", node.get("name", "")) for node in sorted_nodes[:5]]
        
        # 否则返回前几个节点
        return [node.get("id", node.get("name", "")) for node in nodes[:5]]

