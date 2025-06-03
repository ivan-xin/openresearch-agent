"""
大语言模型服务 - MVP版本
"""
import asyncio
import structlog
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.configs.llm_config import llm_config
from app.models.task import Task, TaskResult, TaskStatus

logger = structlog.get_logger()

class LLMService:
    """大语言模型服务"""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化LLM客户端"""
        try:
            if llm_config.provider == "openai":
                self.client = AsyncOpenAI(
                    api_key=llm_config.openai_api_key,
                    base_url=llm_config.openai_base_url,
                    timeout=llm_config.timeout
                )
                logger.info("OpenAI client initialized successfully")
            else:
                raise ValueError(f"Unsupported LLM provider: {llm_config.provider}")
                
        except Exception as e:
            logger.error("Failed to initialize LLM client", error=str(e))
            raise
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              **kwargs) -> str:
        """生成回复"""
        try:
            # 合并配置参数
            params = {
                "model": llm_config.openai_model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", llm_config.max_tokens),
                "temperature": kwargs.get("temperature", llm_config.temperature),
            }
            
            logger.debug("Generating LLM response", params=params)
            
            # 调用LLM API
            response: ChatCompletion = await self.client.chat.completions.create(**params)
            
            # 提取回复内容
            content = response.choices[0].message.content
            
            logger.info(
                "LLM response generated successfully",
                model=params["model"],
                tokens_used=response.usage.total_tokens if response.usage else None
            )
            
            return content
            
        except Exception as e:
            logger.error("Failed to generate LLM response", error=str(e))
            raise
    
    async def analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """分析用户意图"""
        try:
            # 构建意图分析提示
            system_prompt = """你是一个学术研究助手的意图分析器。请分析用户的查询意图，并返回JSON格式的结果。
                            可能的意图类型：
                            - search_papers: 搜索论文
                            - get_paper_details: 获取论文详情  
                            - search_authors: 搜索作者
                            - get_author_details: 获取作者详情
                            - citation_network: 引用网络分析
                            - collaboration_network: 合作网络分析
                            - research_trends: 研究趋势分析
                            - research_landscape: 研究全景分析
                            - general_chat: 一般对话
                            - unknown: 未知意图

                            请返回JSON格式：
                            {
                                "intent_type": "意图类型",
                                "confidence": 0.0-1.0之间的置信度,
                                "parameters": {提取的参数},
                                "needs_clarification": true/false,
                                "clarification_question": "需要澄清的问题（如果需要）"
                            }"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.generate_response(
                messages=messages,
                temperature=0.3,  # 降低温度以获得更一致的结果
                max_tokens=500
            )
            
            # 尝试解析JSON响应
            import json
            try:
                result = json.loads(response)
                logger.info("Intent analysis completed", intent=result.get("intent_type"))
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse intent analysis JSON, using fallback")
                return {
                    "intent_type": "unknown",
                    "confidence": 0.3,
                    "parameters": {},
                    "needs_clarification": True,
                    "clarification_question": "请更具体地描述您的需求"
                }
                
        except Exception as e:
            logger.error("Intent analysis failed", error=str(e))
            return {
                "intent_type": "unknown",
                "confidence": 0.0,
                "parameters": {},
                "needs_clarification": True,
                "clarification_question": "抱歉，我无法理解您的请求，请重新描述"
            }
    
    async def generate_academic_response(self, user_query: str, 
                                       research_data: Dict[str, Any],
                                       conversation_history: List[Dict[str, str]] = None) -> str:
        """生成学术研究相关的回复"""
        try:
            # 构建学术助手系统提示
            system_prompt = """你是一个专业的学术研究助手，专门帮助用户进行论文搜索、作者查询、引用分析等学术研究任务。

                                请根据提供的研究数据，生成专业、准确、有帮助的回复。回复应该：
                                1. 直接回答用户的问题
                                2. 提供具体的数据和信息
                                3. 使用专业但易懂的语言
                                4. 如果数据不完整，诚实说明
                                5. 适当提供进一步研究的建议

                                请用中文回复，保持专业和友好的语调。"""

            # 构建用户消息，包含查询和数据
            user_content = f"""用户查询：{user_query}
                            研究数据：
                            {json.dumps(research_data, ensure_ascii=False, indent=2)}
                            请基于以上数据回答用户的查询。"""

            # 构建消息列表
            messages = [{"role": "system", "content": system_prompt}]
            
            # 添加对话历史（最近几轮）
            if conversation_history:
                messages.extend(conversation_history[-6:])  # 只保留最近3轮对话
            
            messages.append({"role": "user", "content": user_content})
            
            response = await self.generate_response(
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            logger.info("Academic response generated successfully")
            return response
            
        except Exception as e:
            logger.error("Failed to generate academic response", error=str(e))
            return "抱歉，生成回复时出现错误，请稍后重试。"
    
    async def execute_task(self, task: Task) -> TaskResult:
        """执行LLM任务"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = asyncio.get_event_loop().time()
            
            logger.info("Executing LLM task", task_id=task.id, task_name=task.name)
            
            # 获取任务参数
            prompt = task.parameters.get("prompt", "")
            model_params = task.parameters.get("model_params", {})
            
            if not prompt:
                raise ValueError("Prompt is required for LLM task")
            
            # 构建消息
            messages = [{"role": "user", "content": prompt}]
            
            # 生成响应
            response = await self.generate_response(messages=messages, **model_params)
            
            # 计算执行时间
            task.completed_at = asyncio.get_event_loop().time()
            execution_time = task.completed_at - task.started_at
            
            task.status = TaskStatus.COMPLETED
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                data={"response": response},
                execution_time=execution_time
            )
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            
            logger.error("LLM task execution failed", task_id=task.id, error=str(e))
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e)
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 发送简单的测试请求
            test_messages = [{"role": "user", "content": "Hello"}]
            await self.generate_response(messages=test_messages, max_tokens=10)
            
            return {
                "status": "healthy",
                "provider": llm_config.provider,
                "model": llm_config.openai_model
            }
        except Exception as e:
            logger.error("LLM health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.client:
                await self.client.close()
                logger.info("LLM client closed successfully")
        except Exception as e:
            logger.error("Error during LLM service cleanup", error=str(e))

# 全局LLM服务实例
llm_service = LLMService()
