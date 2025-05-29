"""
数据库连接和管理
"""
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool
from configs.database_config import database_config
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self._initialized = False
    
    async def initialize(self):
        """初始化数据库连接池"""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing database connection pool")
            
            self.pool = await asyncpg.create_pool(
                host=database_config.host,
                port=database_config.port,
                database=database_config.database,
                user=database_config.username,
                password=database_config.password,
                min_size=database_config.min_connections,
                max_size=database_config.max_connections,
                command_timeout=database_config.connection_timeout
            )
            
            # 测试连接
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            self._initialized = True
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database connection pool", error=str(e))
            raise
    
    async def close(self):
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not self._initialized:
            await self.initialize()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_script(self, script: str):
        """执行SQL脚本"""
        async with self.get_connection() as conn:
            await conn.execute(script)
    
    async def create_tables(self):
        """创建数据表"""
        create_tables_sql = """
        -- 创建会话表
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            title VARCHAR(500),
            context JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        );
        
        -- 创建消息表
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_messages_conversation_id (conversation_id),
            INDEX idx_messages_created_at (created_at)
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);
        CREATE INDEX IF NOT EXISTS idx_conversations_active ON conversations(is_active);
        
        -- 创建更新时间触发器
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
        CREATE TRIGGER update_conversations_updated_at
            BEFORE UPDATE ON conversations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        await self.execute_script(create_tables_sql)
        logger.info("Database tables created successfully")

# 全局数据库管理器实例
db_manager = DatabaseManager()
