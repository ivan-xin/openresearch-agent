"""
ID生成工具 - MVP版本
"""
import uuid

def generate_conversation_id() -> str:
    """生成会话ID"""
    return f"conv_{uuid.uuid4().hex[:12]}"

def generate_message_id() -> str:
    """生成消息ID"""
    return f"msg_{uuid.uuid4().hex[:12]}"

def generate_task_id() -> str:
    """生成任务ID"""
    return f"task_{uuid.uuid4().hex[:12]}"
