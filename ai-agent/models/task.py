"""
任务执行相关模型 - 简化版（方案1）
"""
from enum import Enum
from typing import Dict, Any, Optional, List, Set
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
    """单个任务 - 包含依赖和并行信息"""
    id: str
    type: TaskType
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    timeout: int = 30  # 超时时间（秒）
    
    # 新增：依赖和并行控制
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID列表
    can_parallel: bool = True  # 是否可以并行执行
    
    # 时间戳
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
            "dependencies": self.dependencies,
            "can_parallel": self.can_parallel,
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
    
    def is_ready(self, completed_task_ids: Set[str]) -> bool:
        """检查任务是否可以执行（依赖已满足）"""
        if self.status != TaskStatus.PENDING:
            return False
        return all(dep_id in completed_task_ids for dep_id in self.dependencies)
    
    def mark_started(self):
        """标记任务开始执行"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def mark_completed(self):
        """标记任务完成"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def mark_failed(self, error_message: str):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message

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

class TaskPlan:
    """简化的任务计划 - 只包含任务列表"""
    
    def __init__(self, tasks: List[Task]):
        self.tasks = tasks
        self.created_at = datetime.now()
    
    def get_ready_tasks(self, completed_task_ids: Set[str]) -> List[Task]:
        """获取可以执行的任务（依赖已满足）"""
        ready_tasks = []
        for task in self.tasks:
            if task.is_ready(completed_task_ids):
                ready_tasks.append(task)
        return ready_tasks
    
    def get_parallel_tasks(self, ready_tasks: List[Task]) -> List[Task]:
        """从就绪任务中筛选可并行执行的任务"""
        return [task for task in ready_tasks if task.can_parallel]
    
    def get_serial_tasks(self, ready_tasks: List[Task]) -> List[Task]:
        """从就绪任务中筛选必须串行执行的任务"""
        return [task for task in ready_tasks if not task.can_parallel]
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_pending_tasks(self) -> List[Task]:
        """获取所有待执行的任务"""
        return [task for task in self.tasks if task.status == TaskStatus.PENDING]
    
    def get_completed_tasks(self) -> List[Task]:
        """获取所有已完成的任务"""
        return [task for task in self.tasks if task.status == TaskStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[Task]:
        """获取所有失败的任务"""
        return [task for task in self.tasks if task.status == TaskStatus.FAILED]
    
    def is_completed(self) -> bool:
        """检查所有任务是否都已完成（成功或失败）"""
        return all(task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] for task in self.tasks)
    
    def get_completion_stats(self) -> Dict[str, int]:
        """获取完成统计信息"""
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0
        }
        
        for task in self.tasks:
            stats[task.status.value] += 1
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "created_at": self.created_at.isoformat(),
            "task_count": len(self.tasks),
            "tasks": [task.to_dict() for task in self.tasks],
            "completion_stats": self.get_completion_stats()
        }

# 任务构建器类 - 更新以支持依赖和并行控制
class TaskBuilder:
    """任务构建器"""
    
    @staticmethod
    def mcp_tool_call(tool_name: str, arguments: Dict[str, Any], 
                     task_id: str = None, dependencies: List[str] = None,
                     can_parallel: bool = True) -> Task:
        """创建MCP工具调用任务"""
        return Task(
            id=task_id or f"mcp_{tool_name}_{datetime.now().strftime('%H%M%S')}",
            type=TaskType.MCP_TOOL_CALL,
            name=f"Call MCP tool: {tool_name}",
            parameters={
                "tool_name": tool_name,
                "arguments": arguments
            },
            dependencies=dependencies or [],
            can_parallel=can_parallel
        )
    
    @staticmethod
    def llm_generation(prompt: str, model_params: Dict[str, Any] = None,
                      task_id: str = None, dependencies: List[str] = None,
                      can_parallel: bool = True) -> Task:
        """创建LLM生成任务"""
        return Task(
            id=task_id or f"llm_gen_{datetime.now().strftime('%H%M%S')}",
            type=TaskType.LLM_GENERATION,
            name="LLM text generation",
            parameters={
                "prompt": prompt,
                "model_params": model_params or {}
            },
            dependencies=dependencies or [],
            can_parallel=can_parallel
        )
    
    @staticmethod
    def response_generation(content: str, format_type: str = "text",
                           task_id: str = None, dependencies: List[str] = None,
                           can_parallel: bool = False) -> Task:
        """创建响应生成任务"""
        return Task(
            id=task_id or f"resp_gen_{datetime.now().strftime('%H%M%S')}",
            type=TaskType.RESPONSE_GENERATION,
            name="Generate response",
            parameters={
                "content": content,
                "format_type": format_type
            },
            dependencies=dependencies or [],
            can_parallel=can_parallel  # 响应生成通常需要等待所有数据收集完成
        )
    
    @staticmethod
    def create_dependent_chain(tasks_config: List[Dict[str, Any]]) -> List[Task]:
        """创建依赖链任务"""
        tasks = []
        previous_task_id = None
        
        for i, config in enumerate(tasks_config):
            dependencies = [previous_task_id] if previous_task_id else []
            
            task = Task(
                id=config.get("id", f"task_{i}_{datetime.now().strftime('%H%M%S')}"),
                type=TaskType(config["type"]),
                name=config["name"],
                parameters=config.get("parameters", {}),
                dependencies=dependencies,
                can_parallel=config.get("can_parallel", False)  # 链式任务默认不能并行
            )
            
            tasks.append(task)
            previous_task_id = task.id
        
        return tasks
    
    @staticmethod
    def create_parallel_group(tasks_config: List[Dict[str, Any]], 
                             shared_dependencies: List[str] = None) -> List[Task]:
        """创建并行任务组"""
        tasks = []
        
        for i, config in enumerate(tasks_config):
            task = Task(
                id=config.get("id", f"parallel_{i}_{datetime.now().strftime('%H%M%S')}"),
                type=TaskType(config["type"]),
                name=config["name"],
                parameters=config.get("parameters", {}),
                dependencies=shared_dependencies or [],
                can_parallel=True  # 并行组中的任务都可以并行
            )
            
            tasks.append(task)
        
        return tasks
