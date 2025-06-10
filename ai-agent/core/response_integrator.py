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
        """处理和清理执行结果 - 保留 MCP 结构信息"""
        processed = {}
        
        for task_id, result in execution_results.items():
            if isinstance(result, dict) and not result.get("error"):
                if "content" in result:
                    content = result["content"]
                    
                    if isinstance(content, list) and content:
                        first_item = content[0]
                        if isinstance(first_item, dict) and first_item.get("type") == "text":
                            # 保留 MCP 结构，同时提供便捷访问
                            processed[task_id] = {
                                "mcp_format": True,
                                "content_type": "text",
                                "text_content": first_item.get("text", ""),
                                "raw_mcp_content": content,
                                "full_result": result
                            }
                        else:
                            # 其他类型的 MCP 内容
                            processed[task_id] = {
                                "mcp_format": True,
                                "content_type": first_item.get("type", "unknown"),
                                "content_data": first_item,
                                "raw_mcp_content": content,
                                "full_result": result
                            }
                    else:
                        # content 不是列表或为空
                        processed[task_id] = {
                            "mcp_format": True,
                            "content_type": "invalid",
                            "content_data": content,
                            "full_result": result
                        }
                else:
                    # 没有 content 字段
                    processed[task_id] = {
                        "mcp_format": False,
                        "content_data": result
                    }
            else:
                logger.warning("Task result contains error", 
                            task_id=task_id, 
                            error=result.get("error") if isinstance(result, dict) else "Invalid result format")
        
        return processed
    
    def _select_response_strategy(self, intent_type: IntentType) -> str:
        """根据意图类型选择响应策略"""
        strategy_mapping = {
        # 论文相关
            IntentType.SEARCH_PAPERS: "paper_list",
            IntentType.GET_PAPER_DETAILS: "paper_detail",
            IntentType.GET_PAPER_CITATIONS: "citation_analysis",
            
            IntentType.SEARCH_AUTHORS: "author_list",
            IntentType.GET_AUTHOR_DETAILS: "author_detail",  # 虽然值是"search_authors"，但策略可以不同
            IntentType.GET_AUTHOR_PAPERS: "author_papers",

            # 趋势分析
            IntentType.GET_TRENDING_PAPERS: "trending_papers",
            IntentType.GET_TOP_KEYWORDS: "keyword_analysis",

            # IntentType.PAPER_REVIEW: "review_report",
            # IntentType.PAPER_GENERATION: "generation_guide",
            
            # 通用对话
            IntentType.GENERAL_CHAT: "general_chat",
            
            # 未知意图
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
        elif strategy == "trending_papers":
            structured_response.update(self._structure_trend_report_response(processed_data))
        elif strategy == "keyword_analysis":
            structured_response.update(self._structure_keyword_analysis_response(processed_data))
        elif strategy == "landscape_overview":
            structured_response.update(self._structure_landscape_response(processed_data))
        elif strategy == "review_report":
            structured_response.update(self._structure_review_response(processed_data))
        elif strategy == "generation_guide":
            structured_response.update(self._structure_generation_response(processed_data))
        
        return structured_response
    
    def _structure_paper_list_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化论文列表响应 - 处理 MCP 格式和 JSON 字符串数据"""
        papers = []
        total_count = 0
        text_content = ""
        paper_count = 0
        
        for task_result in data.values():
            if isinstance(task_result, dict):
                if task_result.get("mcp_format") and task_result.get("content_type") == "text":
                    # 从 text_content 中获取 JSON 字符串
                    text_content = task_result.get("text_content", "")
                    
                    if text_content:
                        try:
                            # 尝试解析 JSON 字符串
                            import json
                            json_data = json.loads(text_content)
                            
                            if isinstance(json_data, dict):
                                # 提取论文数据
                                papers.extend(json_data.get("papers", []))
                                total_count = json_data.get("count", len(papers))
                                paper_count = len(papers)
                                
                                logger.info("Successfully parsed JSON from text_content", 
                                        papers_count=len(papers), 
                                        total_count=total_count)
                            else:
                                logger.warning("JSON data is not a dictionary", data_type=type(json_data).__name__)
                                
                        except json.JSONDecodeError as e:
                            logger.warning("Failed to parse JSON from text_content", error=str(e))
                            # 回退到文本解析
                            parsed_papers = self._parse_paper_text_result(text_content)
                            if parsed_papers.get("papers"):
                                papers = parsed_papers["papers"]
                                total_count = parsed_papers.get("total_count", 0)
                                paper_count = len(papers)
                    
                elif "papers" in task_result:
                    # 标准的结构化论文数据
                    papers.extend(task_result["papers"])
                    total_count = task_result.get("total", len(papers))
                    paper_count = len(papers)
                    
            elif isinstance(task_result, str):
                # 向后兼容：直接是字符串
                text_content = task_result
                try:
                    # 尝试解析为 JSON
                    import json
                    json_data = json.loads(task_result)
                    
                    if isinstance(json_data, dict):
                        papers.extend(json_data.get("papers", []))
                        total_count = json_data.get("count", len(papers))
                        paper_count = len(papers)
                    else:
                        # 不是字典，回退到文本解析
                        raise json.JSONDecodeError("Not a dictionary", task_result, 0)
                        
                except json.JSONDecodeError:
                    # 不是 JSON，按文本解析
                    import re
                    
                    # 提取总数
                    total_match = re.search(r'\*\*总数\*\*:\s*(\d+)', task_result)
                    if total_match:
                        total_count = int(total_match.group(1))
                    
                    # 计算论文数量
                    paper_sections = re.findall(r'###\s*\d+\.', task_result)
                    paper_count = len(paper_sections)
        
        # 提取更详细的统计信息
        if papers:
            top_authors = self._extract_top_authors(papers)
            publication_years = self._extract_publication_years(papers)
            avg_citations = sum(paper.get("citations", 0) for paper in papers) / len(papers) if papers else 0
            top_venues = self._extract_top_venues(papers)
        else:
            top_authors = []
            publication_years = []
            avg_citations = 0
            top_venues = []
        
        return {
            "summary": {
                "total_papers": total_count,
                "returned_papers": paper_count,
                "data_format": "json" if papers else ("text" if text_content else "unknown"),
                "has_structured_papers": len(papers) > 0,
                "has_text_content": bool(text_content),
                "top_authors": top_authors[:5],
                "publication_years": publication_years[:5],
                "average_citations": round(avg_citations, 1),
                "top_venues": top_venues[:3]
            },
            "insights": [
                f"找到 {total_count} 篇相关论文，成功获取了 {len(papers)} 篇的详细信息",
                f"平均引用次数：{round(avg_citations, 1)} 次" if papers else "获取了论文搜索结果",
                f"主要作者包括：{', '.join(top_authors[:3])}" if top_authors else "包含多位研究者的工作",
                f"发表年份范围：{min(publication_years)}-{max(publication_years)}" if len(publication_years) > 1 else f"主要发表于 {publication_years[0]} 年" if publication_years else "年份信息完整",
                f"主要发表期刊/会议：{', '.join(top_venues[:2])}" if top_venues else "涵盖多个学术期刊和会议"
            ],
            "recommendations": [
                "建议查看引用次数最高的论文以了解核心研究",
                "可以进一步分析作者合作网络和研究团队",
                "建议关注最新发表的论文以跟踪前沿进展",
                "可以按发表期刊筛选高质量论文"
            ]
        }
 
    def _structure_paper_detail_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化论文详情响应 - 处理实际的MCP数据格式"""
        paper_details = {}
        papers_found = []
        
        for task_result in data.values():
            if isinstance(task_result, dict):
                # 处理MCP格式的响应
                if task_result.get("mcp_format") and task_result.get("content_type") == "text":
                    text_content = task_result.get("text_content", "")
                    try:
                        import json
                        json_data = json.loads(text_content)
                        
                        # 处理新的数据结构：paper_searches
                        if isinstance(json_data, dict) and "paper_searches" in json_data:
                            paper_searches = json_data["paper_searches"]
                            
                            # 提取所有候选论文
                            for search in paper_searches:
                                if "candidates" in search:
                                    papers_found.extend(search["candidates"])
                            
                            # 如果找到论文，使用第一篇作为详情
                            if papers_found:
                                paper_details = papers_found[0]
                                break
                                
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse paper details JSON")
                        continue
                        
                # 处理直接的论文数据格式
                elif "paper" in task_result:
                    paper_details = task_result["paper"]
                    break
                elif "papers" in task_result and task_result["papers"]:
                    # 如果是论文列表，取第一个
                    paper_details = task_result["papers"][0]
                    break
                elif "candidates" in task_result and task_result["candidates"]:
                    # 直接是候选列表
                    paper_details = task_result["candidates"][0]
                    break
        
        # 如果没有找到论文详情，返回空结构
        if not paper_details:
            return {
                "summary": {
                    "title": "",
                    "authors": [],
                    "publication_year": "",
                    "citation_count": 0,
                    "venue": "",
                    "doi": "",
                    "abstract": "",
                    "keywords": [],
                    "url": ""
                },
                "insights": ["未找到论文详细信息"],
                "recommendations": [
                    "请检查论文ID或标题是否正确",
                    "尝试使用不同的搜索关键词",
                    "确认论文是否存在于数据库中"
                ]
            }
        
        # 提取论文信息 - 适配新的数据结构
        title = paper_details.get("title", "")
        
        # 处理作者信息 - 新格式是对象数组
        authors = []
        authors_data = paper_details.get("authors", [])
        for author in authors_data:
            if isinstance(author, dict):
                author_name = author.get("name", "")
                if author_name:
                    authors.append(author_name)
            elif isinstance(author, str):
                authors.append(author)
        
        # 处理发表时间 - 新格式是时间戳
        publication_year = ""
        if "published_at" in paper_details:
            try:
                import datetime
                timestamp = paper_details["published_at"]
                publication_year = datetime.datetime.fromtimestamp(timestamp).year
            except:
                publication_year = "未知"
        elif "year" in paper_details:
            publication_year = paper_details["year"]
        
        citation_count = paper_details.get("citations", 0)
        venue = paper_details.get("venue_name", paper_details.get("venue", ""))
        doi = paper_details.get("doi", "")
        abstract = paper_details.get("abstract", "")
        keywords = paper_details.get("keywords", [])
        url = paper_details.get("url", "")
        references_count = paper_details.get("references_count", 0)
        likes_count = paper_details.get("likes_count", 0)
        
        # 分析论文影响力
        impact_level = "较低"
        if citation_count >= 100:
            impact_level = "很高"
        elif citation_count >= 50:
            impact_level = "高"
        elif citation_count >= 10:
            impact_level = "中等"
        elif citation_count >= 1:
            impact_level = "较低"
        else:
            impact_level = "新发表"
        
        # 分析研究领域
        research_fields = []
        for keyword in keywords:
            if isinstance(keyword, str):
                # 处理常见的学科分类
                if keyword.startswith("cs."):
                    field_mapping = {
                        "cs.CR": "密码学与安全",
                        "cs.AI": "人工智能",
                        "cs.LG": "机器学习",
                        "cs.CV": "计算机视觉",
                        "cs.CL": "计算语言学",
                        "cs.DB": "数据库",
                        "cs.DC": "分布式计算",
                        "cs.SE": "软件工程"
                    }
                    research_fields.append(field_mapping.get(keyword, keyword))
                else:
                    research_fields.append(keyword)
        
        return {
            "summary": {
                "title": title,
                "authors": authors,
                "publication_year": publication_year,
                "citation_count": citation_count,
                "venue": venue,
                "doi": doi,
                "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,  # 摘要截断
                "keywords": keywords,
                "url": url,
                "references_count": references_count,
                "likes_count": likes_count,
                "research_fields": research_fields,
                "impact_level": impact_level
            },
            "insights": [
                f"论文《{title}》发表于 {publication_year} 年" if title and publication_year else "论文信息获取成功",
                f"被引用 {citation_count} 次，学术影响力{impact_level}" if citation_count > 0 else "暂无引用数据",
                f"作者包括：{', '.join(authors[:3])}" + ("等" if len(authors) > 3 else "") if authors else "作者信息完整",
                f"发表在 {venue}" if venue else "期刊信息可用",
                f"研究领域：{', '.join(research_fields[:3])}" if research_fields else "关键词信息完整",
                f"论文摘要长度：{len(abstract)} 字符" if abstract else "摘要信息可用",
                f"参考文献 {references_count} 篇" if references_count > 0 else "参考文献信息可用",
                f"获得 {likes_count} 个赞" if likes_count > 0 else "社交互动数据可用"
            ],
            "recommendations": [
                "查看论文的完整摘要和内容" if url else "获取论文的访问链接",
                "分析该论文的引用网络和影响力" if citation_count > 0 else "关注该论文的后续引用情况",
                f"了解作者 {authors[0]} 的其他研究工作" if authors else "探索相关作者的研究",
                f"探索 {research_fields[0]} 领域的相关研究" if research_fields else "深入了解相关研究领域",
                "查看该论文的参考文献列表" if references_count > 0 else "分析论文的理论基础",
                f"关注 {venue} 期刊的最新研究" if venue else "了解发表期刊的影响因子",
                "下载并阅读论文全文" if url else "获取论文的详细信息"
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
    
    def _structure_author_detail_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化作者详情响应"""
        author_details = {}
        
        for task_result in data.values():
            if isinstance(task_result, dict):
                # 处理MCP格式的响应
                if task_result.get("mcp_format") and task_result.get("content_type") == "text":
                    text_content = task_result.get("text_content", "")
                    try:
                        import json
                        json_data = json.loads(text_content)
                        if isinstance(json_data, dict) and "authors" in json_data:
                            authors = json_data["authors"]
                            if authors and len(authors) > 0:
                                author_details = authors[0]  # 取第一个作者的详细信息
                                break
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse author details JSON")
                        continue
                # 处理直接的作者数据
                elif "authors" in task_result:
                    authors = task_result["authors"]
                    if authors and len(authors) > 0:
                        author_details = authors[0]
                        break
                # 处理单个作者对象
                elif "name" in task_result or "id" in task_result:
                    author_details = task_result
                    break
        
        if not author_details:
            return {
                "summary": {},
                "insights": ["未找到作者详细信息"],
                "recommendations": ["请检查作者姓名是否正确", "尝试使用不同的搜索关键词"]
            }
        
        # 提取作者基本信息
        author_name = author_details.get("name", "未知作者")
        affiliation = author_details.get("affiliation", "")
        email = author_details.get("email", "")
        h_index = author_details.get("h_index", 0)
        paper_count = author_details.get("paper_count", 0)
        citation_count = author_details.get("citation_count", 0)
        research_interests = author_details.get("research_interests", [])
        
        # 处理合作者信息
        coauthors = author_details.get("coauthors", [])
        coauthor_count = len(coauthors)
        
        # 分析合作者的机构分布
        coauthor_institutions = []
        collaboration_strength = {}
        
        for coauthor in coauthors:
            if isinstance(coauthor, dict):
                # 收集合作者机构
                coauthor_affiliation = coauthor.get("affiliation", "")
                if coauthor_affiliation and coauthor_affiliation not in coauthor_institutions:
                    coauthor_institutions.append(coauthor_affiliation)
                
                # 分析合作强度
                coauthor_name = coauthor.get("name", "")
                collaboration_count = coauthor.get("collaboration_count", 0)
                if coauthor_name and collaboration_count > 0:
                    collaboration_strength[coauthor_name] = collaboration_count
        
        # 找出最频繁的合作者
        top_collaborators = sorted(collaboration_strength.items(), 
                                key=lambda x: x[1], reverse=True)[:5]
        
        # 分析研究活跃度
        activity_level = "低"
        if paper_count >= 20:
            activity_level = "高"
        elif paper_count >= 10:
            activity_level = "中"
        elif paper_count >= 5:
            activity_level = "中低"
        
        # 分析影响力
        impact_level = "较低"
        if h_index >= 20:
            impact_level = "很高"
        elif h_index >= 10:
            impact_level = "高"
        elif h_index >= 5:
            impact_level = "中等"
        elif h_index >= 2:
            impact_level = "较高"
        
        return {
            "summary": {
                "author_name": author_name,
                "affiliation": affiliation,
                "email": email,
                "h_index": h_index,
                "paper_count": paper_count,
                "citation_count": citation_count,
                "coauthor_count": coauthor_count,
                "research_interests": research_interests if research_interests else [],
                "top_collaborators": [collab[0] for collab in top_collaborators],
                "collaboration_institutions": coauthor_institutions[:5],  # 前5个机构
                "activity_level": activity_level,
                "impact_level": impact_level
            },
            "insights": [
                f"作者 {author_name} 共发表 {paper_count} 篇论文",
                f"H指数为 {h_index}，学术影响力{impact_level}",
                f"总引用次数：{citation_count} 次" if citation_count > 0 else "引用信息暂无",
                f"与 {coauthor_count} 位学者有合作关系" if coauthor_count > 0 else "暂无合作者信息",
                f"主要合作机构：{', '.join(coauthor_institutions[:3])}" if coauthor_institutions else "机构信息不完整",
                f"最频繁合作者：{', '.join([collab[0] for collab in top_collaborators[:3]])}" if top_collaborators else "合作关系信息不可用",
                f"研究活跃度：{activity_level}"
            ],
            "recommendations": [
                "查看该作者的论文列表" if paper_count > 0 else "搜索该作者的相关论文",
                "分析该作者的合作网络" if coauthor_count > 0 else "探索该作者的潜在合作关系",
                "了解该作者的研究轨迹和发展趋势",
                "查看该作者在特定研究领域的贡献",
                "分析该作者与其他知名学者的关系" if top_collaborators else "探索该作者的学术影响力",
                f"关注该作者所在机构 {affiliation} 的其他研究者" if affiliation else "了解该作者的学术背景"
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
        """结构化趋势报告响应 - 简化版"""
        trending_papers = []
        total_count = 0
        time_window = ""
        
        # 提取数据
        for task_result in data.values():
            if isinstance(task_result, dict):
                if task_result.get("mcp_format") and task_result.get("content_type") == "text":
                    text_content = task_result.get("text_content", "")
                    try:
                        import json
                        json_data = json.loads(text_content)
                        
                        if isinstance(json_data, dict):
                            trending_papers = json_data.get("trending_papers", [])
                            total_count = json_data.get("count", len(trending_papers))
                            time_window = json_data.get("time_window", "")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
                elif "trending_papers" in task_result:
                    trending_papers = task_result["trending_papers"]
                    total_count = task_result.get("count", len(trending_papers))
                    time_window = task_result.get("time_window", "")
                    break
        
        if not trending_papers:
            return {
                "summary": {
                    "total_papers": 0,
                    "time_window": time_window or "未知"
                },
                "insights": ["未找到热门论文数据"],
                "recommendations": ["尝试调整搜索条件"]
            }
        
        # 简单统计
        total_citations = sum(paper.get("citations", 0) for paper in trending_papers)
        avg_citations = round(total_citations / len(trending_papers), 1) if trending_papers else 0
        
        # 提取作者（取前3个论文的第一作者）
        top_authors = []
        for paper in trending_papers[:3]:
            authors = paper.get("authors", [])
            if authors:
                first_author = authors[0] if isinstance(authors[0], str) else authors[0].get("name", "")
                if first_author:
                    top_authors.append(first_author)
        
        # 提取关键词
        keywords = []
        for paper in trending_papers:
            paper_keywords = paper.get("keywords", [])
            keywords.extend(paper_keywords)
        
        # 去重并取前3个
        unique_keywords = list(dict.fromkeys(keywords))[:3]
        
        # 最热门的论文
        hottest_paper = ""
        if trending_papers:
            # 按popularity_score排序，如果没有则按citations排序
            sorted_papers = sorted(trending_papers, 
                                key=lambda x: x.get("popularity_score", x.get("citations", 0)), 
                                reverse=True)
            hottest_paper = sorted_papers[0].get("title", "")
        
        return {
            "summary": {
                "total_papers": total_count,
                "time_window": time_window,
                "average_citations": avg_citations,
                "top_authors": top_authors,
                "keywords": unique_keywords,
                "hottest_paper": hottest_paper
            },
            "insights": [
                f"找到 {total_count} 篇热门论文" + (f"（时间窗口：{time_window}）" if time_window else ""),
                f"平均引用次数：{avg_citations} 次" if avg_citations > 0 else "包含最新发表的论文",
                f"主要作者：{', '.join(top_authors)}" if top_authors else "涵盖多位研究者",
                f"热门关键词：{', '.join(unique_keywords)}" if unique_keywords else "涵盖多个研究领域",
                f"最热门论文：《{hottest_paper[:50]}...》" if len(hottest_paper) > 50 else f"最热门论文：《{hottest_paper}》" if hottest_paper else "热度排名完整"
            ],
            "recommendations": [
                "查看引用次数最高的论文了解研究热点",
                "关注活跃作者的最新研究动态",
                "深入了解热门关键词相关的研究领域",
                "分析热门论文的研究方法和创新点"
            ]
        }
    
    def _structure_keyword_analysis_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化关键词分析响应 - 处理 MCP 格式数据"""
        keywords = []
        total_count = 0
        text_content = ""
        
        for task_result in data.values():
            if isinstance(task_result, dict):
                if task_result.get("mcp_format") and task_result.get("content_type") == "text":
                    # 从 text_content 中获取 JSON 字符串
                    text_content = task_result.get("text_content", "")
                    
                    if text_content:
                        try:
                            import json
                            json_data = json.loads(text_content)
                            
                            if isinstance(json_data, dict):
                                keywords = json_data.get("keywords", [])
                                total_count = json_data.get("count", len(keywords))
                                
                                logger.info("Successfully parsed keywords from text_content", 
                                        keywords_count=len(keywords), 
                                        total_count=total_count)
                            else:
                                logger.warning("JSON data is not a dictionary", data_type=type(json_data).__name__)
                                
                        except json.JSONDecodeError as e:
                            logger.warning("Failed to parse JSON from text_content", error=str(e))
                
                elif "keywords" in task_result:
                    # 标准的结构化关键词数据
                    keywords = task_result["keywords"]
                    total_count = task_result.get("count", len(keywords))
        
        # 如果没有找到关键词数据
        if not keywords:
            return {
                "summary": {
                    "total_keywords": 0,
                    "data_format": "empty"
                },
                "insights": ["未找到热门关键词数据"],
                "recommendations": ["尝试指定具体的研究领域", "检查搜索条件是否正确"]
            }
        
        # 提取统计信息
        total_papers = sum(kw.get("paper_count", 0) for kw in keywords)
        avg_papers_per_keyword = round(total_papers / len(keywords), 1) if keywords else 0
        
        # 找出最热门的关键词
        top_keyword = max(keywords, key=lambda x: x.get("paper_count", 0)) if keywords else {}
        top_keyword_name = top_keyword.get("keyword", "")
        top_keyword_count = top_keyword.get("paper_count", 0)
        
        # 分类关键词（简单的领域分类）
        cs_keywords = [kw for kw in keywords if kw.get("keyword", "").startswith("cs.")]
        physics_keywords = [kw for kw in keywords if kw.get("keyword", "").startswith("physics.")]
        other_keywords = [kw for kw in keywords if not kw.get("keyword", "").startswith(("cs.", "physics."))]
        
        # 提取前5个热门关键词
        sorted_keywords = sorted(keywords, key=lambda x: x.get("paper_count", 0), reverse=True)
        top_5_keywords = [(kw.get("keyword", ""), kw.get("paper_count", 0)) for kw in sorted_keywords[:5]]
        
        return {
            "summary": {
                "total_keywords": total_count,
                "returned_keywords": len(keywords),
                "total_papers": total_papers,
                "avg_papers_per_keyword": avg_papers_per_keyword,
                "top_keyword": top_keyword_name,
                "top_keyword_count": top_keyword_count,
                "cs_keywords_count": len(cs_keywords),
                "physics_keywords_count": len(physics_keywords),
                "other_keywords_count": len(other_keywords),
                "top_5_keywords": top_5_keywords
            },
            "insights": [
                f"找到 {total_count} 个热门关键词，涵盖 {total_papers} 篇论文",
                f"最热门关键词：{top_keyword_name}（{top_keyword_count} 篇论文）" if top_keyword_name else "关键词热度分布均匀",
                f"平均每个关键词对应 {avg_papers_per_keyword} 篇论文",
                f"计算机科学领域：{len(cs_keywords)} 个关键词" if cs_keywords else "计算机科学领域关键词较少",
                f"物理学领域：{len(physics_keywords)} 个关键词" if physics_keywords else "物理学领域关键词较少",
                f"其他领域：{len(other_keywords)} 个关键词" if other_keywords else "主要集中在计算机和物理领域"
            ],
            "recommendations": [
                f"深入研究热门关键词 '{top_keyword_name}' 相关的论文" if top_keyword_name else "关注论文数量较多的关键词",
                "比较不同领域关键词的发展趋势",
                "分析跨领域关键词的研究机会",
                "关注新兴关键词的发展潜力"
            ]
        }

    async def _generate_natural_response(self,
                                    query: str,
                                    structured_response: Dict[str, Any],
                                    intent_result: IntentAnalysisResult) -> str:
        """生成自然语言响应"""
        try:
            # 准备研究数据
            research_data = {
                "strategy": structured_response.get("strategy"),
                "summary": structured_response.get("summary", {}),
                "insights": structured_response.get("insights", []),
                "recommendations": structured_response.get("recommendations", []),
                "intent_type": intent_result.primary_intent.type.value,
                "confidence": intent_result.primary_intent.confidence
            }
            
            # 调用 LLM 服务生成学术响应
            try:
                natural_response = await self.llm_service.generate_academic_response(
                    user_query=query,
                    research_data=research_data,
                    conversation_history=None
                )
                
                if isinstance(natural_response, str) and natural_response.strip():
                    logger.info("LLM generated academic response successfully")
                    return natural_response.strip()
                else:
                    logger.warning("LLM generated empty response")
                    
            except Exception as llm_error:
                logger.warning("LLM academic response generation failed", error=str(llm_error))

            # 备选方案：使用基础的 generate_response 方法
            try:
                messages = [
                    {
                        "role": "system",
                        "content": "你是一个专业的学术研究助手。请根据用户查询和研究数据生成友好、专业的回复。"
                    },
                    {
                        "role": "user",
                        "content": f"用户查询：{query}\n\n研究数据：{research_data}\n\n请生成自然的中文回复："
                    }
                ]
                
                natural_response = await self.llm_service.generate_response(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                if isinstance(natural_response, str) and natural_response.strip():
                    logger.info("LLM basic response generation successful")
                    return natural_response.strip()
                    
            except Exception as basic_error:
                logger.warning("LLM basic response generation failed", error=str(basic_error))

            # 最后使用备选响应
            logger.info("Using fallback response generation")
            return self._create_fallback_response(structured_response)
            
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
        
        # 确保 natural_response 是字符串
        if not isinstance(natural_response, str):
            natural_response = str(natural_response)
        
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
        elif intent_type == IntentType.RESEARCH_TRENDS:
            suggestions = [
                "深入分析特定研究方向",
                "比较不同时间段的趋势", 
                "探索跨领域的研究机会"
            ]
        elif intent_type == IntentType.GENERAL_CHAT:
            suggestions = [
                "您可以询问学术研究相关的问题",
                "尝试搜索特定主题的论文",
                "查找感兴趣的研究作者"
            ]
        else:
            suggestions = [
                "请提供更具体的查询",
                "尝试使用不同的关键词", 
                "描述您想了解的研究领域"
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
    def _extract_top_venues(self, papers: List[Dict]) -> List[str]:
        """提取热门期刊/会议"""
        venue_counts = {}
        for paper in papers:
            venue = paper.get("venue_name", "")
            if venue:
                venue_counts[venue] = venue_counts.get(venue, 0) + 1
    
        return sorted(venue_counts.keys(), key=lambda x: venue_counts[x], reverse=True)





    def _extract_top_authors(self, papers: List[Dict]) -> List[str]:
        """提取热门作者 - 处理新的作者数据结构"""
        author_counts = {}
        for paper in papers:
            authors = paper.get("authors", [])
            for author in authors:
                if isinstance(author, dict):
                    # 新格式：{"id": "...", "name": "..."}
                    author_name = author.get("name", "")
                elif isinstance(author, str):
                    # 旧格式：直接是字符串
                    author_name = author
                else:
                    continue
                    
                if author_name:
                    author_counts[author_name] = author_counts.get(author_name, 0) + 1
    
        return sorted(author_counts.keys(), key=lambda x: author_counts[x], reverse=True)    
    

    def _extract_publication_years(self, papers: List[Dict]) -> List[int]:
        """提取发表年份 - 处理时间戳格式"""
        years = []
        for paper in papers:
            if "published_at" in paper:
                # 时间戳格式
                timestamp = paper["published_at"]
                try:
                    import datetime
                    year = datetime.datetime.fromtimestamp(timestamp).year
                    years.append(year)
                except:
                    continue
            elif "year" in paper:
                # 直接年份格式
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

