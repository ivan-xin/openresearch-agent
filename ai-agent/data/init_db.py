"""
数据库初始化脚本
"""
import asyncio
from data.database import db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

async def init_database():
    """初始化数据库"""
    try:
        logger.info("Starting database initialization")
        
        # 初始化连接池
        await db_manager.initialize()
        
        # 创建表
        await db_manager.create_tables()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(init_database())
