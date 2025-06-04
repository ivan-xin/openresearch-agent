"""
数据访问层包 - 统一数据访问接口
"""

# 数据库管理
from .database import db_manager

# 数据模型
from .models import Conversation, Message

# 数据访问层
from .repositories.conversation_repository import conversation_repo
from .repositories.message_repository import message_repo

# 上下文管理器
from .context_manager import ContextManager

# 创建全局上下文管理器实例
context_manager = ContextManager()

__all__ = [
    # 数据库管理
    "db_manager",
    
    # 数据模型
    "Conversation",
    "Message",
    
    # 数据访问层
    "conversation_repo",
    "message_repo",
    
    # 上下文管理
    "ContextManager",
    "context_manager",
]

# 版本信息
__version__ = "1.0.0-mvp"

# 数据层初始化函数
async def initialize_data_layer():
    """初始化数据访问层"""
    try:
        # 初始化数据库连接
        await db_manager.initialize()
        
        # 创建数据表
        await db_manager.create_tables()
        
        # 初始化上下文管理器
        await context_manager.initialize()
        
        return True
        
    except Exception as e:
        print(f"Failed to initialize data layer: {e}")
        return False

async def cleanup_data_layer():
    """清理数据访问层资源"""
    try:
        # 清理上下文管理器
        await context_manager.cleanup()
        
        # 关闭数据库连接
        await db_manager.close()
        
        return True
        
    except Exception as e:
        print(f"Failed to cleanup data layer: {e}")
        return False

# 便捷函数
async def get_conversation_with_messages(conversation_id: str):
    """获取包含消息的完整会话 - 便捷函数"""
    return await context_manager.get_conversation(conversation_id)

async def create_new_conversation(user_id: str, conversation_id: str = None):
    """创建新会话 - 便捷函数"""
    return await context_manager.create_conversation(user_id, conversation_id)

async def add_message_to_conversation(conversation_id: str, role: str, content: str, metadata: dict = None):
    """添加消息到会话 - 便捷函数"""
    return await context_manager.add_message(conversation_id, role, content, metadata)

# 数据层状态检查
async def check_data_layer_health():
    """检查数据层健康状态"""
    health_status = {
        "database": "unknown",
        "context_manager": "unknown",
        "repositories": "unknown"
    }
    
    try:
        # 检查数据库连接
        if db_manager._initialized:
            async with db_manager.get_connection() as conn:
                await conn.execute("SELECT 1")
            health_status["database"] = "healthy"
        else:
            health_status["database"] = "not_initialized"
            
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
    
    try:
        # 检查上下文管理器
        stats = await context_manager.get_conversation_stats("health_check")
        health_status["context_manager"] = "healthy"
        
    except Exception as e:
        health_status["context_manager"] = f"unhealthy: {str(e)}"
    
    try:
        # 检查仓储层
        # 简单测试：获取用户会话（空结果也是正常的）
        await conversation_repo.get_by_user_id("health_check", limit=1)
        health_status["repositories"] = "healthy"
        
    except Exception as e:
        health_status["repositories"] = f"unhealthy: {str(e)}"
    
    # 计算总体状态
    all_healthy = all(status == "healthy" for status in health_status.values())
    health_status["overall"] = "healthy" if all_healthy else "degraded"
    
    return health_status
