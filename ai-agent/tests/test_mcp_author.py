# 在 Python 中测试
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mcp_client_stdio import mcp_client_stdio
from utils.logger import get_logger

logger = get_logger(__name__)

async def test():
    async with mcp_client_stdio:
        # 测试搜索作者
        result = await mcp_client_stdio.search_authors("Jiajing Wu", limit=1)
        print("Search result:", result)
        
        # 调试原始响应
        debug_result = await mcp_client_stdio.debug_tool_call(
            "search_authors", 
            {"query": "Jiajing Wu", "limit": 1}
        )
        print("Debug result:", debug_result)

asyncio.run(test())
