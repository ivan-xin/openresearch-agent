"""
核心Agent类 - 简化版（移除缓存）
"""
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

import asyncio
from typing import Set

from data.models.conversation import Conversation
from models.intent import IntentAnalysisResult
from models.task import TaskPlan, Task, TaskType
from services.llm_service import LLMService
from services import MCPClient
from data.context_manager import ContextManager
from .intent_analyzer import IntentAnalyzer
from .task_orchestrator import TaskOrchestrator
from .response_integrator import ResponseIntegrator
from utils.logger import get_logger

logger = get_logger(__name__)

class AcademicAgent:
    """学术研究AI Agent核心类 - 简化版"""
    
    def __init__(self):
        # 初始化核心服务
        self.llm_service = LLMService()
        self.mcp_client = MCPClient() 
        self.context_manager = ContextManager()
        
        # 初始化核心组件
        self.intent_analyzer = IntentAnalyzer(self.llm_service)
        self.task_orchestrator = TaskOrchestrator()
        self.response_integrator = ResponseIntegrator(self.llm_service)
        
        # 状态管理
        self.active_conversations: Dict[str, Conversation] = {}
        self.processing_queries: Dict[str, bool] = {}
    
    async def initialize(self):
        """初始化Agent"""
        try:
            logger.info("Initializing Academic Agent")
            
            # 初始化上下文管理器（包含数据库初始化）
            await self.llm_service.initialize()
            await self.mcp_client.initialize()
            await self.context_manager.initialize()
            
            logger.info("Academic Agent initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Academic Agent", error=str(e))
            raise

    async def _extract_context_for_intent(self, conversation: Conversation) -> Dict[str, Any]:
        """提取用于意图分析的上下文"""
        context = {}
        
        if hasattr(conversation, 'messages') and conversation.messages:
            # 获取最近的意图类型
            recent_intents = []
            for message in conversation.messages[-5:]:  # 最近5条消息
                if hasattr(message, 'role') and message.role == "assistant" and hasattr(message, 'metadata'):
                    # 确保 metadata 是字典类型
                    metadata = message.metadata
                    if isinstance(metadata, str):
                        try:
                            import json
                            metadata = json.loads(metadata)
                        except (json.JSONDecodeError, TypeError):
                            metadata = {}
                    elif not isinstance(metadata, dict):
                        metadata = {}
                    
                    # 现在安全地使用 get 方法
                    if metadata.get("intent_type"):
                        recent_intents.append(metadata["intent_type"])
            
            context["recent_intents"] = recent_intents
            context["conversation_length"] = len(conversation.messages)
        
        return context

    
    async def _extract_context_for_response(self, conversation: Conversation) -> Dict[str, Any]:
        """提取用于响应生成的上下文"""
        context = {}
        
        if hasattr(conversation, 'messages') and conversation.messages:
            context["conversation_length"] = len(conversation.messages)
            context["recent_topics"] = []  # 可以添加主题提取逻辑
            
            # 提取最近的查询类型
            recent_queries = []
            for message in conversation.messages[-10:]:
                if hasattr(message, 'role') and message.role == "user":
                    recent_queries.append(message.content[:50])  # 前50个字符
            context["recent_queries"] = recent_queries
        
        return context

    async def _execute_task_plan(self, task_plan: TaskPlan, query_id: str) -> Dict[str, Any]:
        """执行任务计划 - 支持依赖管理和并行执行"""
        results = {}
        completed_task_ids = set()
        failed_task_ids = set()
        
        try:
            logger.info("Starting task plan execution", 
                    query_id=query_id,
                    initial_stats=task_plan.get_completion_stats())
            
            # 循环执行直到所有任务完成或失败
            max_iterations = len(task_plan.tasks) * 2  # 防止无限循环
            iteration = 0
            
            while not task_plan.is_completed() and iteration < max_iterations:
                iteration += 1
                
                # 获取可以执行的任务
                ready_tasks = task_plan.get_ready_tasks(completed_task_ids)
                
                if not ready_tasks:
                    # 没有可执行的任务，检查是否存在问题
                    pending_tasks = task_plan.get_pending_tasks()
                    if pending_tasks:
                        logger.warning("No ready tasks found but pending tasks exist", 
                                    pending_task_ids=[t.id for t in pending_tasks],
                                    completed_ids=list(completed_task_ids),
                                    failed_ids=list(failed_task_ids))
                        # 强制执行第一个待处理任务，避免死锁
                        ready_tasks = [pending_tasks[0]]
                    else:
                        break
                
                # 分离可并行和必须串行的任务
                parallel_tasks = task_plan.get_parallel_tasks(ready_tasks)
                serial_tasks = task_plan.get_serial_tasks(ready_tasks)
                
                logger.info("Executing tasks batch", 
                        iteration=iteration,
                        parallel_count=len(parallel_tasks),
                        serial_count=len(serial_tasks))
                
                # 并行执行可并行的任务
                if parallel_tasks:
                    parallel_results = await self._execute_parallel_tasks(parallel_tasks, query_id)
                    results.update(parallel_results)
                    
                    # 更新任务状态
                    for task in parallel_tasks:
                        if task.id in parallel_results:
                            result = parallel_results[task.id]
                            # 修复：确保 result 是字典类型
                            if isinstance(result, dict) and result.get("error"):
                                task.mark_failed(result["error"])
                                failed_task_ids.add(task.id)
                            elif isinstance(result, str) and "error" in result.lower():
                                # 如果结果是错误字符串
                                task.mark_failed(result)
                                failed_task_ids.add(task.id)
                            else:
                                task.mark_completed()
                                completed_task_ids.add(task.id)
                
                # 串行执行必须串行的任务
                for task in serial_tasks:
                    try:
                        logger.info("Executing serial task", 
                                task_id=task.id, 
                                task_name=task.name)
                        
                        task.mark_started()
                        
                        # 更新任务参数（可能依赖前面任务的结果）
                        updated_parameters = self._update_task_parameters(task, results)
                        
                        result = await self._execute_single_task(task, updated_parameters)
                        
                        results[task.id] = result
                        task.mark_completed()
                        completed_task_ids.add(task.id)
                        
                        logger.info("Serial task completed", 
                                task_id=task.id,
                                execution_time=task.execution_time)
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error("Serial task failed", 
                                    task_id=task.id, 
                                    error=error_msg)
                        
                        results[task.id] = {"error": error_msg}
                        task.mark_failed(error_msg)
                        failed_task_ids.add(task.id)
            
            final_stats = task_plan.get_completion_stats()
            logger.info("Task plan execution completed", 
                    query_id=query_id,
                    iterations=iteration,
                    final_stats=final_stats)
            
            return results
            
        except Exception as e:
            logger.error("Task plan execution failed", query_id=query_id, error=str(e))
            return {"error": str(e)}


    async def _execute_parallel_tasks(self, tasks: List[Task], query_id: str) -> Dict[str, Any]:
        """并行执行任务组"""
        logger.info("Executing parallel tasks", 
                query_id=query_id,
                task_count=len(tasks),
                task_ids=[t.id for t in tasks])
        
        async def execute_single_task_wrapper(task: Task) -> tuple[str, Any]:
            try:
                task.mark_started()
                result = await self._execute_single_task(task, task.parameters)
                return task.id, result
            except Exception as e:
                error_msg = str(e)
                logger.error("Parallel task failed", task_id=task.id, error=error_msg)
                return task.id, {"error": error_msg}
        
        # 使用 asyncio.gather 并行执行
        task_coroutines = [execute_single_task_wrapper(task) for task in tasks]
        task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # 整理结果
        results = {}
        for result in task_results:
            if isinstance(result, Exception):
                logger.error("Parallel task execution exception", error=str(result))
                continue
            
            task_id, task_result = result
            results[task_id] = task_result
        
        return results

    async def _execute_single_task(self, task: Task, parameters: Dict[str, Any]) -> Any:
        """执行单个任务"""
        try:
            if task.type == TaskType.MCP_TOOL_CALL:
                # 从参数中提取工具名和参数
                tool_name = parameters.get("tool_name")
                arguments = parameters.get("arguments", {})
                
                if not tool_name:
                    raise ValueError(f"Missing tool_name in task parameters: {parameters}")
                
                result = await self.mcp_client.call_tool(tool_name, arguments)
                # 确保返回字典格式
                if isinstance(result, str):
                    return {"content": result, "type": "text"}
                elif isinstance(result, dict):
                    return result
                else:
                    return {"content": str(result), "type": "unknown"}
            
            elif task.type == TaskType.LLM_GENERATION:
                # LLM生成任务
                prompt = parameters.get("prompt")
                model_params = parameters.get("model_params", {})
                
                if not prompt:
                    raise ValueError(f"Missing prompt in LLM task parameters: {parameters}")
                
                result = await self.llm_service.generate_text(prompt, **model_params)
                # 确保返回字典格式
                if isinstance(result, str):
                    return {"content": result, "type": "text"}
                elif isinstance(result, dict):
                    return result
                else:
                    return {"content": str(result), "type": "unknown"}
            
            elif task.type == TaskType.RESPONSE_GENERATION:
                # 响应生成任务
                content = parameters.get("content")
                format_type = parameters.get("format_type", "text")
                
                if not content:
                    raise ValueError(f"Missing content in response task parameters: {parameters}")
                
                # 这里可以根据format_type进行不同的格式化处理
                return {"formatted_content": content, "format": format_type}
            
            else:
                raise ValueError(f"Unknown task type: {task.type}")
                
        except Exception as e:
            logger.error("Task execution failed", task_id=task.id, error=str(e))
            return {"error": str(e)}


    def _update_task_parameters(self, task: Task, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """根据前面任务的结果更新当前任务的参数"""
        parameters = task.parameters.copy()
        
        # 特殊处理：如果是获取论文详情任务，且依赖搜索任务
        if (task.type == TaskType.MCP_TOOL_CALL and 
            parameters.get("tool_name") == "get_paper_details" and 
            task.dependencies):
            
            # 从依赖任务的结果中提取论文ID
            for dep_task_id in task.dependencies:
                if dep_task_id in previous_results:
                    dep_result = previous_results[dep_task_id]
                    
                    # 确保 dep_result 是字典类型
                    if not isinstance(dep_result, dict):
                        logger.warning("Dependency result is not a dict", 
                                    task_id=task.id, 
                                    dep_task_id=dep_task_id,
                                    result_type=type(dep_result).__name__)
                        continue
                    
                    # 假设搜索结果包含论文列表
                    if "papers" in dep_result:
                        papers = dep_result["papers"]
                        if papers and len(papers) > 0:
                            # 取第一篇论文的ID
                            first_paper = papers[0]
                            if isinstance(first_paper, dict):
                                paper_id = first_paper.get("id") or first_paper.get("paper_id")
                                if paper_id:
                                    # 更新参数
                                    if "arguments" not in parameters:
                                        parameters["arguments"] = {}
                                    parameters["arguments"]["paper_id"] = paper_id
                                    logger.info("Updated task parameters with paper_id", 
                                            task_id=task.id, 
                                            paper_id=paper_id)
                                    break
        
        return parameters


    async def _execute_processing_pipeline(self,
                                        query: str,
                                        conversation_id: Optional[str],
                                        user_id: str,
                                        query_id: str) -> Dict[str, Any]:
        """执行完整的处理流水线"""
        
        start_time = datetime.now()
        try:
            # 1. 获取或创建对话上下文
            conversation = await self._get_or_create_conversation(
                conversation_id, user_id
            )
            
            # 2. 通过 context_manager 添加用户消息
            await self.context_manager.add_message(
                conversation.id, 
                "user", 
                query, 
                {"query_id": query_id}
            )
            
            # 3. 意图分析
            logger.info("Starting intent analysis", query_id=query_id)
            intent_result = await self.intent_analyzer.analyze(
                query, 
                await self._extract_context_for_intent(conversation)
            )
            
            # 4. 检查是否需要澄清
            if intent_result.needs_clarification:
                clarification_response = self._create_clarification_response(intent_result)
                await self.context_manager.add_message(
                    conversation.id,
                    "assistant", 
                    clarification_response["content"]
                )
                await self.context_manager.update_conversation(conversation)
                return clarification_response
            
            # 5. 任务编排
            logger.info("Creating task plan", query_id=query_id)
            task_plan = await self.task_orchestrator.create_plan(intent_result)
            
            # 6. 执行任务计划
            logger.info("Executing task plan", 
                    query_id=query_id,
                    task_stats=task_plan.get_completion_stats())
            execution_results = await self._execute_task_plan(task_plan, query_id)
            
            # 7. 整合响应
            logger.info("Integrating response", query_id=query_id)
            final_response = await self.response_integrator.integrate(
                query,
                intent_result,
                execution_results,
                await self._extract_context_for_response(conversation)
            )
            
            # 8. 确保 final_response 是字典类型
            if not isinstance(final_response, dict):
                logger.warning("Response integrator returned non-dict result", 
                            result_type=type(final_response).__name__)
                final_response = {"content": str(final_response)}
            
            # 确保有 content 字段
            if "content" not in final_response:
                final_response["content"] = "抱歉，我无法生成合适的回复。"
            
            # 9. 通过 context_manager 添加助手回复
            await self.context_manager.add_message(
                conversation.id,
                "assistant", 
                final_response["content"], 
                {
                    "query_id": query_id,
                    "intent_type": intent_result.primary_intent.type.value,
                    "confidence": intent_result.primary_intent.confidence,
                    "task_stats": task_plan.get_completion_stats()
                }
            )
            
            # 10. 保存对话
            await self.context_manager.update_conversation(conversation)
            
            # 11. 计算处理时间 - 修复时区问题
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 12. 添加查询元数据
            final_response["query_id"] = query_id
            final_response["conversation_id"] = conversation.id
            final_response["task_execution_stats"] = task_plan.get_completion_stats()
            final_response["processing_time"] = processing_time
            
            logger.info("Query processing completed successfully", 
                    query_id=query_id,
                    processing_time=processing_time,
                    task_stats=final_response["task_execution_stats"])
            
            return final_response
            
        except Exception as e:
            logger.error("Processing pipeline failed", query_id=query_id, error=str(e))
            return self._create_error_response(str(e), query_id)


    def _create_clarification_response(self, intent_result: IntentAnalysisResult) -> Dict[str, Any]:
        """创建澄清响应"""
        # 根据意图类型生成不同的澄清问题
        intent_type = intent_result.primary_intent.type.value
        
        clarification_messages = {
            "search_papers": "您想搜索什么主题的论文？请提供更具体的关键词。",
            "search_authors": "您想查找哪位作者的信息？请提供作者姓名。",
            "unknown": "请提供更多信息，以便我更好地理解您的需求。"
        }
        
        content = clarification_messages.get(intent_type, clarification_messages["unknown"])
        
        return {
            "content": content,
            "needs_clarification": True,
            "metadata": {
                "intent_type": intent_type,
                "confidence": intent_result.primary_intent.confidence
            }
        }

    def _create_error_response(self, error_message: str, query_id: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "content": f"抱歉，处理您的请求时遇到了问题：{error_message}",
            "error": True,
            "query_id": query_id,
            "metadata": {
                "error_message": error_message
            }
        }

    async def process_query(self, 
                          query: str, 
                          conversation_id: Optional[str] = None,
                          user_id: str = "default_user") -> Dict[str, Any]:
        """处理用户查询的主要入口方法"""
        # 生成查询ID用于跟踪
        query_id = str(uuid.uuid4())
        
        try:
            logger.info("Starting query processing", 
                       query_id=query_id,
                       query=query,
                       conversation_id=conversation_id,
                       user_id=user_id)
            
            # 防止重复处理
            if conversation_id and conversation_id in self.processing_queries:
                return {
                    "content": "正在处理您的上一个请求，请稍候...",
                    "status": "processing"
                }
            
            if conversation_id:
                self.processing_queries[conversation_id] = True
            
            try:
                # 执行处理流程
                result = await self._execute_processing_pipeline(
                    query, conversation_id, user_id, query_id
                )
                
                return result
                
            finally:
                # 清理处理状态
                if conversation_id and conversation_id in self.processing_queries:
                    del self.processing_queries[conversation_id]
            
        except Exception as e:
            logger.error("Query processing failed", 
                        query_id=query_id,
                        error=str(e))
            return self._create_error_response(str(e), query_id)
    
    async def _get_or_create_conversation(self,
                                        conversation_id: Optional[str],
                                        user_id: str) -> Conversation:
        """获取或创建对话"""
        if conversation_id and conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]
        
        if conversation_id:
            # 尝试从数据库加载
            conversation = await self.context_manager.get_conversation(conversation_id)
            if conversation:
                self.active_conversations[conversation_id] = conversation
                return conversation
        
        # 创建新对话
        conversation = await self.context_manager.create_conversation(
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        self.active_conversations[conversation.id] = conversation
        return conversation

    async def get_task_plan_debug_info(self, query: str, user_id: str = "debug_user") -> Dict[str, Any]:
        """获取任务计划的调试信息（用于开发和测试）"""
        try:
            # 创建临时对话
            conversation = await self._get_or_create_conversation(None, user_id)
            
            # 意图分析
            intent_result = await self.intent_analyzer.analyze(
                query, 
                await self._extract_context_for_intent(conversation)
            )
            
            # 创建任务计划
            task_plan = await self.task_orchestrator.create_plan(intent_result)
            
            # 返回调试信息
            debug_info = {
                "query": query,
                "intent_analysis": {
                    "primary_intent": {
                        "type": intent_result.primary_intent.type.value,
                        "confidence": intent_result.primary_intent.confidence,
                        "parameters": intent_result.primary_intent.parameters
                    },
                    "needs_clarification": intent_result.needs_clarification,
                    "clarification_questions": getattr(intent_result, 'clarification_questions', [])
                },
                "task_plan": task_plan.to_dict(),
                "execution_flow": self._analyze_execution_flow(task_plan)
            }
            
            return debug_info
            
        except Exception as e:
            logger.error("Failed to get task plan debug info", error=str(e))
            return {"error": str(e)}

    def _analyze_execution_flow(self, task_plan: TaskPlan) -> Dict[str, Any]:
        """分析任务执行流程"""
        flow_info = {
            "total_tasks": len(task_plan.tasks),
            "parallel_tasks": [],
            "serial_tasks": [],
            "dependency_chains": [],
            "execution_phases": []
        }
        
        # 分析并行和串行任务
        for task in task_plan.tasks:
            task_info = {
                "id": task.id,
                "name": task.name,
                "type": task.type.value,
                "dependencies": task.dependencies
            }
            
            if task.can_parallel:
                flow_info["parallel_tasks"].append(task_info)
            else:
                flow_info["serial_tasks"].append(task_info)
        
        # 分析依赖链
        dependency_chains = self._find_dependency_chains(task_plan.tasks)
        flow_info["dependency_chains"] = dependency_chains
        
        # 模拟执行阶段
        execution_phases = self._simulate_execution_phases(task_plan)
        flow_info["execution_phases"] = execution_phases
        
        return flow_info

    def _find_dependency_chains(self, tasks: List[Task]) -> List[List[str]]:
        """找出依赖链"""
        chains = []
        visited = set()
        
        for task in tasks:
            if task.id not in visited and not task.dependencies:
                # 从无依赖的任务开始构建链
                chain = self._build_chain(task, tasks, visited)
                if len(chain) > 1:
                    chains.append(chain)
        
        return chains

    def _build_chain(self, start_task: Task, all_tasks: List[Task], visited: set) -> List[str]:
        """构建从指定任务开始的依赖链"""
        chain = [start_task.id]
        visited.add(start_task.id)
        
        # 找到依赖当前任务的下一个任务
        for task in all_tasks:
            if start_task.id in task.dependencies and task.id not in visited:
                chain.extend(self._build_chain(task, all_tasks, visited))
                break
        
        return chain

    def _simulate_execution_phases(self, task_plan: TaskPlan) -> List[Dict[str, Any]]:
        """模拟执行阶段"""
        phases = []
        completed_ids = set()
        phase_num = 1
        
        while len(completed_ids) < len(task_plan.tasks):
            ready_tasks = task_plan.get_ready_tasks(completed_ids)
            
            if not ready_tasks:
                break
            
            parallel_tasks = task_plan.get_parallel_tasks(ready_tasks)
            serial_tasks = task_plan.get_serial_tasks(ready_tasks)
            
            phase_info = {
                "phase": phase_num,
                "parallel_tasks": [{"id": t.id, "name": t.name} for t in parallel_tasks],
                "serial_tasks": [{"id": t.id, "name": t.name} for t in serial_tasks],
                "total_tasks_in_phase": len(ready_tasks)
            }
            
            phases.append(phase_info)
            
            # 模拟完成这些任务
            for task in ready_tasks:
                completed_ids.add(task.id)
            
            phase_num += 1
            
            # 防止无限循环
            if phase_num > 10:
                break
        
        return phases
    
    async def get_conversation_history(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话历史"""
        try:
            conversation = await self.context_manager.get_conversation(conversation_id)
            if not conversation:
                return None
            
            return {
                "conversation_id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "message_count": len(conversation.messages) if hasattr(conversation, 'messages') else 0,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat(),
                        "metadata": msg.metadata
                    }
                    for msg in (conversation.messages if hasattr(conversation, 'messages') else [])
                ]
            }
            
        except Exception as e:
            logger.error("Failed to get conversation history", 
                        conversation_id=conversation_id,
                        error=str(e))
            return None
    
    async def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的对话列表"""
        try:
            conversations = await self.context_manager.get_user_conversations(user_id)
            
            return [
                {
                    "conversation_id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "message_count": len(conv.messages) if hasattr(conv, 'messages') else 0,
                    "last_message": conv.messages[-1].content if hasattr(conv, 'messages') and conv.messages else None
                }
                for conv in conversations
            ]
            
        except Exception as e:
            logger.error("Failed to get user conversations", user_id=user_id, error=str(e))
            return []
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("Starting agent cleanup")
            
            # 保存所有活跃对话
            for conversation in self.active_conversations.values():
                await self.context_manager.update_conversation(conversation)
            
            # 清理上下文管理器
            await self.context_manager.cleanup()
            
            # 清理状态
            self.active_conversations.clear()
            self.processing_queries.clear()
            
            logger.info("Agent cleanup completed")
            
        except Exception as e:
            logger.error("Error during agent cleanup", error=str(e))
            raise
