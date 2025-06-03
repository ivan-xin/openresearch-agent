"""
任务执行相关模型 - MVP版本
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from dataclasses import dataclass, field

class TaskType(Enum):
    """任务类型枚举"""
    # MCP工具调用任务
    MCP_TOOL_CALL = "mcp_tool_call"
    
    # LLM处理任务
    LLM_GENERATION = "llm_generation"
    
    # 响应生成任务
    RESPONSE_GENERATION = "response_generation"

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    """单个任务"""
    id: str
    type: TaskType
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    timeout: int = 30  # 超时时间（秒）
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "parameters": self.parameters,
            "status": self.status.value,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }
    
    @property
    def execution_time(self) -> Optional[float]:
        """获取执行时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

class TaskResult(BaseModel):
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """判断任务是否成功"""
        return self.status == TaskStatus.COMPLETED and self.error is None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "is_success": self.is_success
        }

# 任务构建器类
class TaskBuilder:
    """任务构建器"""
    
    @staticmethod
    def mcp_tool_call(tool_name: str, arguments: Dict[str, Any], 
                     task_id: str = None) -> Task:
        """创建MCP工具调用任务"""
        return Task(
            id=task_id or f"mcp_{tool_name}_{datetime.now().strftime('%H%M%S')}",
            type=TaskType.MCP_TOOL_CALL,
            name=f"Call MCP tool: {tool_name}",
            parameters={
                "tool_name": tool_name,
                "arguments": arguments
            }
        )
    
    @staticmethod
    def llm_generation(prompt: str, model_params: Dict[str, Any] = None,
                      task_id: str = None) -> Task:
        """创建LLM生成任务"""
        return Task(
            id=task_id or f"llm_gen_{datetime.now().strftime('%H%M%S')}",
            type=TaskType.LLM_GENERATION,
            name="LLM text generation",
            parameters={
                "prompt": prompt,
                "model_params": model_params or {}
            }
        )
    
    @staticmethod
    def response_generation(content: str, format_type: str = "text",
                           task_id: str = None) -> Task:
        """创建响应生成任务"""
        return Task(
            id=task_id or f"resp_gen_{datetime.now().strftime('%H%M%S')}",
            type=TaskType.RESPONSE_GENERATION,
            name="Generate response",
            parameters={
                "content": content,
                "format_type": format_type
            }
        )
