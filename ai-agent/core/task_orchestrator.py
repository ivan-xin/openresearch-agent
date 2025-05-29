"""
任务编排器 - 根据意图创建执行计划
"""
import uuid
from typing import List, Dict, Any
from models.intent import IntentAnalysisResult, IntentType
from models.task import Task, TaskPlan, TaskType, TaskStatus
from utils.logger import get_logger

logger = get_logger(__name__)

class TaskOrchestrator:
    """任务编排器类"""
    
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
            
            # 确定执行顺序
            execution_order = self._determine_execution_order(all_tasks)
            
            # 识别可并行执行的任务
            parallel_groups = self._identify_parallel_groups(all_tasks)
            
            task_plan = TaskPlan(
                tasks=all_tasks,
                execution_order=execution_order,
                parallel_groups=parallel_groups
            )
            
            logger.info("Task plan created", 
                       task_count=len(all_tasks),
                       parallel_groups_count=len(parallel_groups))
            
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
            IntentType.CITATION_ANALYSIS: ["get_citation_network"],
            IntentType.COLLABORATION_ANALYSIS: ["get_collaboration_network"],
            IntentType.TREND_ANALYSIS: ["get_research_trends"],
            IntentType.RESEARCH_LANDSCAPE: ["analyze_research_landscape"],
            IntentType.PAPER_REVIEW: ["search_papers", "get_paper_details"],
            IntentType.PAPER_GENERATION: ["get_research_trends", "search_papers"]
        }
    
    def _create_tasks_for_intent(self, intent) -> List[Task]:
        """为特定意图创建任务列表"""
        tasks = []
        tools = self.intent_to_tools.get(intent.type, [])
        
        for tool_name in tools:
            task = Task(
                id=str(uuid.uuid4()),
                type=TaskType.MCP_CALL,
                tool_name=tool_name,
                parameters=self._prepare_tool_parameters(tool_name, intent.parameters),
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        # 特殊处理复合意图
        if intent.type == IntentType.PAPER_REVIEW:
            tasks = self._create_paper_review_tasks(intent)
        elif intent.type == IntentType.PAPER_GENERATION:
            tasks = self._create_paper_generation_tasks(intent)
        
        return tasks
    
    def _prepare_tool_parameters(self, tool_name: str, intent_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """为工具调用准备参数"""
        parameters = {}
        
        if tool_name == "search_papers":
            parameters = {
                "query": intent_parameters.get("query", ""),
                "limit": intent_parameters.get("limit", 10),
                "fields": intent_parameters.get("fields", ["title", "abstract", "authors"])
            }
        
        elif tool_name == "get_paper_details":
            parameters = {
                "paper_id": intent_parameters.get("paper_id", ""),
                "include_citations": intent_parameters.get("include_citations", True)
            }
        
        elif tool_name == "search_authors":
            parameters = {
                "author_name": intent_parameters.get("author_name", ""),
                "limit": intent_parameters.get("limit", 10)
            }
        
        elif tool_name == "get_author_details":
            parameters = {
                "author_id": intent_parameters.get("author_id", ""),
                "include_papers": intent_parameters.get("include_papers", True)
            }
        
        elif tool_name == "get_citation_network":
            parameters = {
                "paper_id": intent_parameters.get("paper_id", ""),
                "depth": intent_parameters.get("depth", 2)
            }
        
        elif tool_name == "get_collaboration_network":
            parameters = {
                "author_id": intent_parameters.get("author_id", ""),
                "depth": intent_parameters.get("depth", 2)
            }
        
        elif tool_name == "get_research_trends":
            parameters = {
                "field": intent_parameters.get("field", ""),
                "time_range": intent_parameters.get("time_range", "5years")
            }
        
        elif tool_name == "analyze_research_landscape":
            parameters = {
                "domain": intent_parameters.get("domain", ""),
                "analysis_type": intent_parameters.get("analysis_type", "overview")
            }
        
        return parameters
    
    def _create_paper_review_tasks(self, intent) -> List[Task]:
        """创建论文审核任务序列"""
        tasks = []
        
        # 1. 搜索相关论文
        search_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_CALL,
            tool_name="search_papers",
            parameters=self._prepare_tool_parameters("search_papers", intent.parameters)
        )
        tasks.append(search_task)
        
        # 2. 获取论文详情（依赖搜索结果）
        details_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_CALL,
            tool_name="get_paper_details",
            parameters={},  # 参数将在运行时从搜索结果中获取
            dependencies=[search_task.id]
        )
        tasks.append(details_task)
        
        return tasks
    
    def _create_paper_generation_tasks(self, intent) -> List[Task]:
        """创建论文生成任务序列"""
        tasks = []
        
        # 1. 分析研究趋势
        trend_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_CALL,
            tool_name="get_research_trends",
            parameters=self._prepare_tool_parameters("get_research_trends", intent.parameters)
        )
        tasks.append(trend_task)
        
        # 2. 搜索相关论文
        search_task = Task(
            id=str(uuid.uuid4()),
            type=TaskType.MCP_CALL,
            tool_name="search_papers",
            parameters=self._prepare_tool_parameters("search_papers", intent.parameters)
        )
        tasks.append(search_task)
        
        return tasks
    
    def _determine_execution_order(self, tasks: List[Task]) -> List[str]:
        """确定任务执行顺序"""
        ordered_tasks = []
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            # 找到没有依赖或依赖已满足的任务
            ready_tasks = []
            for task in remaining_tasks:
                if not task.dependencies or all(dep_id in ordered_tasks for dep_id in task.dependencies):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # 如果没有就绪任务，可能存在循环依赖，选择第一个任务
                ready_tasks = [remaining_tasks[0]]
            
            # 添加就绪任务到执行顺序
            for task in ready_tasks:
                ordered_tasks.append(task.id)
                remaining_tasks.remove(task)
        
        return ordered_tasks
    
    def _identify_parallel_groups(self, tasks: List[Task]) -> List[List[str]]:
        """识别可并行执行的任务组"""
        parallel_groups = []
        
        # 简单策略：没有依赖关系的同类型任务可以并行执行
        independent_tasks = [task for task in tasks if not task.dependencies]
        
        if len(independent_tasks) > 1:
            # 按工具类型分组
            tool_groups = {}
            for task in independent_tasks:
                tool_name = task.tool_name
                if tool_name not in tool_groups:
                    tool_groups[tool_name] = []
                tool_groups[tool_name].append(task.id)
            
            # 如果同一工具有多个独立任务，可以并行执行
            for tool_name, task_ids in tool_groups.items():
                if len(task_ids) > 1:
                    parallel_groups.append(task_ids)
        
        return parallel_groups
