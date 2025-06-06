"""
测试 MCP 连接
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services import mcp_client

async def test_mcp():
    try:
        print("=== 测试 MCP 一次性调用 ===")
        
        # 初始化
        await mcp_client.initialize()
        print("✅ 初始化成功")
        
        # 获取工具列表
        tools = mcp_client.get_available_tools()
        print(f"✅ 可用工具: {[t.get('name') for t in tools]}")
        
        # 测试搜索论文
        result = await mcp_client.search_papers("machine learning", limit=3)
        print(f"✅ 搜索结果: {result}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp())
