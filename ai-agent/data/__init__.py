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

from configs.database_config import database_config
from utils.logger import get_logger

logger = get_logger(__name__)

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
        # if database_config.skip_in_dev:
        #     logger.info("开发环境跳过数据库初始化")
        #     await context_manager.initialize_memory_only()
        #     return True

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
