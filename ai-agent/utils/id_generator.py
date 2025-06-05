"""
ID生成工具 - MVP版本
"""
import uuid

def generate_conversation_id() -> str:
    """生成会话ID - 使用标准UUID格式"""
    return str(uuid.uuid4())

def generate_message_id() -> str:
    """生成消息ID - 使用标准UUID格式"""
    return str(uuid.uuid4())

def generate_task_id() -> str:
    """生成任务ID"""
    return f"task_{uuid.uuid4().hex[:12]}"
