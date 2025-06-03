"""
验证工具
"""

class ValidationError(Exception):
    """验证错误"""
    pass

def validate_not_empty(value: str, field_name: str = "字段"):
    """验证非空"""
    if not value or not value.strip():
        raise ValidationError(f"{field_name}不能为空")

def validate_max_length(value: str, max_length: int, field_name: str = "字段"):
    """验证最大长度"""
    if len(value) > max_length:
        raise ValidationError(f"{field_name}长度不能超过{max_length}个字符")

def validate_chat_message(message: str):
    """验证聊天消息"""
    validate_not_empty(message, "消息内容")
    validate_max_length(message, 5000, "消息内容")

def validate_conversation_id(conversation_id: str):
    """验证会话ID"""
    validate_not_empty(conversation_id, "会话ID")
    if not conversation_id.startswith("conv_"):
        raise ValidationError("会话ID格式不正确")
