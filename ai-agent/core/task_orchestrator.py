"""
任务编排器 - 简化版（方案1）
"""
import uuid
from typing import List, Dict, Any
from models.intent import IntentAnalysisResult, IntentType
from models.task import Task, TaskPlan, TaskType, TaskStatus
from utils.logger import get_logger

logger = get_logger(__name__)

class TaskOrchestrator:
    """任务编排器类 - 简化版"""
    
    def __init__(self):
        self.intent_to_tools = self._build_intent_tool_mapping()
    
    async def create_plan(self, intent_result: IntentAnalysisResult) -> TaskPlan:
        """根据意图分析结果创建任务执行计划"""
        try:
            logger.info("Creating task plan", intent=intent_result.primary_intent.type.value)
            
            # 根据主要意图创建任务
            primary_tasks = self._create_tasks_for_intent(intent_result.primary_intent)
            
            # 处理次要意图（如果有）
            secondary_tasks = []
            for secondary_intent in intent_result.secondary_intents:
                secondary_tasks.extend(self._create_tasks_for_intent(secondary_intent))
            
            all_tasks = primary_tasks + secondary_tasks
            
            # 创建简化的任务计划
            task_plan = TaskPlan(tasks=all_tasks)
            
            logger.info("Task plan created", 
                       task_count=len(all_tasks),
                       stats=task_plan.get_completion_stats())
            
            return task_plan
            
        except Exception as e:
            logger.error("Failed to create task plan", error=str(e))
            raise
    
    def _build_intent_tool_mapping(self) -> Dict[IntentType, List[str]]:
        """构建意图到工具的映射关系"""
        return {
            IntentType.SEARCH_PAPERS: ["search_papers"],
            IntentType.GET_PAPER_DETAILS: ["get_paper_details"],
            IntentType.SEARCH_AUTHORS: ["search_authors"],
            IntentType.GET_AUTHOR_DETAILS: ["get_author_details"],
            IntentType.CITATION_NETWORK: ["get_citation_network"],  # 修改这里
            IntentType.COLLABORATION_NETWORK: ["get_collaboration_network"],  # 修改这里
            IntentType.RESEARCH_TRENDS: ["get_research_trends"],  # 修改这里
            IntentType.RESEARCH_LANDSCAPE: ["analyze_research_landscape"],
        }
    
    def _create_tasks_for_intent(self, intent) -> List[Task]:
        """为特定意图创建任务列表"""
        tasks = []
        
        # 特殊处理复合意图
        # if intent.type == IntentType.PAPER_REVIEW:
        #     tasks = self._create_paper_review_tasks(intent)
        # elif intent.type == IntentType.PAPER_GENERATION:
        #     tasks = self._create_paper_generation_tasks(intent)
        # else:
            # 简单意图：直接映射到工具
        tools = self.intent_to_tools.get(intent.type, [])
        for tool_name in tools:
            task = Task(
                id=str(uuid.uuid4()),
                type=TaskType.MCP_TOOL_CALL,
                name=f"Call {tool_name}",
                parameters=self._prepare_tool_parameters(tool_name, intent.parameters),
                dependencies=[],  # 简单任务无依赖
                can_parallel=True  # 简单任务可并行
            )
            tasks.append(task)
        
        return tasks
    
    def _create_paper_review_tasks(self, intent) -> List[Task]:
        """创建论文审核任务序列 - 有依赖关系"""
        tasks = []
        
        # 1. 搜索相关论文
        search_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_TOOL_CALL,
            name="Search papers for review",
            parameters=self._prepare_tool_parameters("search_papers", intent.parameters),
            dependencies=[],  # 无依赖
            can_parallel=True
        )
        tasks.append(search_task)
        
        # 2. 获取论文详情（依赖搜索结果）
        details_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_TOOL_CALL,
            name="Get paper details for review",
            parameters={
                "tool_name": "get_paper_details",
                "arguments": {}  # 参数将在运行时从搜索结果中获取
            },
            dependencies=[search_task.id],  # 依赖搜索任务
            can_parallel=False  # 有依赖，不能并行
        )
        tasks.append(details_task)
        
        return tasks
    
    def _create_paper_generation_tasks(self, intent) -> List[Task]:
        """创建论文生成任务序列 - 可并行"""
        tasks = []
        
        # 1. 分析研究趋势
        trend_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_TOOL_CALL,
            name="Analyze research trends",
            parameters=self._prepare_tool_parameters("get_research_trends", intent.parameters),
            dependencies=[],
            can_parallel=True  # 可以与搜索任务并行
        )
        tasks.append(trend_task)
        
        # 2. 搜索相关论文
        search_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_TOOL_CALL,
            name="Search papers for generation",
            parameters=self._prepare_tool_parameters("search_papers", intent.parameters),
            dependencies=[],
            can_parallel=True  # 可以与趋势分析并行
        )
        tasks.append(search_task)
        
        return tasks
    
    def _prepare_tool_parameters(self, tool_name: str, intent_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """为工具调用准备参数"""
        # 返回标准化的参数格式，包含工具名和参数
        tool_arguments = {}
        
        if tool_name == "search_papers":
            tool_arguments = {
                "query": intent_parameters.get("query", ""),
                "limit": intent_parameters.get("limit", 10),
                "fields": intent_parameters.get("fields", ["title", "abstract", "authors"])
            }
        elif tool_name == "get_paper_details":
            tool_arguments = {
                "paper_id": intent_parameters.get("paper_id", ""),
                "include_citations": intent_parameters.get("include_citations", True)
            }
        elif tool_name == "search_authors":
            tool_arguments = {
                "author_name": intent_parameters.get("author_name", ""),
                "limit": intent_parameters.get("limit", 10)
            }
        elif tool_name == "get_author_details":
            tool_arguments = {
                "author_id": intent_parameters.get("author_id", ""),
                "include_papers": intent_parameters.get("include_papers", True)
            }
        elif tool_name == "get_citation_network":
            tool_arguments = {
                "paper_id": intent_parameters.get("paper_id", ""),
                "depth": intent_parameters.get("depth", 2)
            }
        elif tool_name == "get_collaboration_network":
            tool_arguments = {
                "author_id": intent_parameters.get("author_id", ""),
                "depth": intent_parameters.get("depth", 2)
            }
        elif tool_name == "get_research_trends":
            tool_arguments = {
                "field": intent_parameters.get("field", ""),
                "time_range": intent_parameters.get("time_range", "5years")
            }
        elif tool_name == "analyze_research_landscape":
            tool_arguments = {
                "domain": intent_parameters.get("domain", ""),
                "analysis_type": intent_parameters.get("analysis_type", "overview")
            }
        
        # 返回标准化格式
        return {
            "tool_name": tool_name,
            "arguments": tool_arguments
        }
