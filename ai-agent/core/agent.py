"""
核心Agent类 - 简化版（移除缓存）
"""
import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from data.models.conversation import Conversation
from models.intent import IntentAnalysisResult
from models.task import TaskPlan
from services.llm_service import LLMService
from services.mcp_client import MCPClient
from data.context_manager import ContextManager
from core.intent_analyzer import IntentAnalyzer
from core.task_orchestrator import TaskOrchestrator
from core.response_integrator import ResponseIntegrator
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
                if message.role == "assistant" and message.metadata.get("intent_type"):
                    recent_intents.append(message.metadata["intent_type"])
            
            context["recent_intents"] = recent_intents
        
        return context
    
    async def _extract_context_for_response(self, conversation: Conversation) -> Dict[str, Any]:
        """提取用于响应生成的上下文"""
        context = {}
        
        if hasattr(conversation, 'messages') and conversation.messages:
            context["conversation_length"] = len(conversation.messages)
            context["recent_topics"] = []  # 可以添加主题提取逻辑
        
        return context
    
    async def _execute_task_plan(self, task_plan: TaskPlan, query_id: str) -> Dict[str, Any]:
        """执行任务计划"""
        results = {}
        
        try:
            for task in task_plan.tasks:
                logger.info("Executing task", task_id=task.id, task_type=task.type.value)
                
                # 根据任务类型执行
                if task.type.value == "mcp_tool_call":
                    result = await self.mcp_client.call_tool(
                        task.name, 
                        task.parameters
                    )
                    results[task.id] = result
                else:
                    logger.warning("Unknown task type", task_type=task.type.value)
                    results[task.id] = {"error": f"Unknown task type: {task.type.value}"}
            
            return results
            
        except Exception as e:
            logger.error("Task execution failed", query_id=query_id, error=str(e))
            return {"error": str(e)}
    
    def _create_clarification_response(self, intent_result: IntentAnalysisResult) -> Dict[str, Any]:
        """创建澄清响应"""
        return {
            "content": intent_result.clarification_questions[0] if intent_result.clarification_questions else "请提供更多信息",
            "needs_clarification": True,
            "metadata": {
                "intent_type": intent_result.primary_intent.type.value,
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
                    "response": "正在处理您的上一个请求，请稍候...",
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
    
    async def _execute_processing_pipeline(self,
                                         query: str,
                                         conversation_id: Optional[str],
                                         user_id: str,
                                         query_id: str) -> Dict[str, Any]:
        """执行完整的处理流水线"""
        
        # 1. 获取或创建对话上下文
        conversation = await self._get_or_create_conversation(
            conversation_id, user_id
        )
        
        # 2. 添加用户消息到对话
        conversation.add_message("user", query, {"query_id": query_id})
        
        # 3. 意图分析
        logger.info("Starting intent analysis", query_id=query_id)
        intent_result = await self.intent_analyzer.analyze(
            query, 
            self._extract_context_for_intent(conversation)
        )
        
        # 4. 检查是否需要澄清
        if intent_result.needs_clarification:
            clarification_response = self._create_clarification_response(intent_result)
            conversation.add_message("assistant", clarification_response["content"])
            await self.context_manager.update_conversation(conversation)
            return clarification_response
        
        # 5. 任务编排
        logger.info("Creating task plan", query_id=query_id)
        task_plan = await self.task_orchestrator.create_plan(intent_result)
        
        # 6. 执行任务计划
        logger.info("Executing task plan", 
                   query_id=query_id,
                   task_count=len(task_plan.tasks))
        execution_results = await self._execute_task_plan(task_plan, query_id)
        
        # 7. 整合响应
        logger.info("Integrating response", query_id=query_id)
        final_response = await self.response_integrator.integrate(
            query,
            intent_result,
            execution_results,
            self._extract_context_for_response(conversation)
        )
        
        # 8. 更新对话上下文
        conversation.add_message("assistant", final_response["content"], {
            "query_id": query_id,
            "intent_type": intent_result.primary_intent.type.value,
            "confidence": intent_result.primary_intent.confidence
        })
        
        # 9. 保存对话
        await self.context_manager.update_conversation(conversation)
        
        # 10. 添加查询元数据
        final_response["query_id"] = query_id
        final_response["conversation_id"] = conversation.id
        final_response["processing_time"] = (
            datetime.now() - conversation.messages[-2].created_at
        ).total_seconds()
        
        logger.info("Query processing completed successfully", 
                   query_id=query_id,
                   processing_time=final_response["processing_time"])
        
        return final_response
    
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
    
    # ... 其他方法保持不变，但移除所有缓存相关的代码
    
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
                "message_count": len(conversation.messages),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat(),
                        "metadata": msg.metadata
                    }
                    for msg in conversation.messages
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
                    "message_count": len(conv.messages),
                    "last_message": conv.messages[-1].content if conv.messages else None
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
