"""
详细的MCP客户端测试
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mcp_client_oneshot import mcp_client_oneshot
from utils.logger import get_logger

logger = get_logger(__name__)

async def test_mcp_detailed():
    """详细测试MCP客户端"""
    
    print("=== 详细测试 MCP 一次性调用 ===")
    
    try:
        # 1. 初始化
        print("1. 初始化客户端...")
        await mcp_client_oneshot.initialize()
        print("✅ 初始化成功")
        
        # 2. 检查工具列表
        tools = mcp_client_oneshot.get_available_tools()
        print(f"✅ 可用工具数量: {len(tools)}")
        for tool in tools:
            print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # 3. 测试搜索论文
        print("\n2. 测试搜索论文...")
        try:
            result = await mcp_client_oneshot.search_papers("machine learning", limit=2)
            print("✅ 搜索论文成功")
            print(f"   结果类型: {type(result)}")
            print(f"   结果内容: {result}")
            
            # 检查结果结构
            if isinstance(result, dict):
                if "papers" in result:
                    papers = result["papers"]
                    print(f"   找到论文数量: {len(papers) if isinstance(papers, list) else 'N/A'}")
                elif "content" in result:
                    print(f"   内容长度: {len(str(result['content']))}")
                else:
                    print(f"   结果键: {list(result.keys())}")
            
        except Exception as e:
            print(f"❌ 搜索论文失败: {e}")
        
        # 4. 测试搜索作者
        print("\n3. 测试搜索作者...")
        try:
            result = await mcp_client_oneshot.search_authors("Geoffrey Hinton", limit=1)
            print("✅ 搜索作者成功")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"❌ 搜索作者失败: {e}")
        
        # 5. 测试获取热门论文
        print("\n4. 测试获取热门论文...")
        try:
            result = await mcp_client_oneshot.call_tool("get_trending_papers", {"limit": 2})
            print("✅ 获取热门论文成功")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"❌ 获取热门论文失败: {e}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await mcp_client_oneshot.cleanup()

if __name__ == "__main__":
    asyncio.run(test_mcp_detailed())
