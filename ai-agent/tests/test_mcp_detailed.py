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
        
        # 3. 测试搜索论文 - 添加更多调试信息
        print("\n2. 测试搜索论文...")
        try:
            # 使用更简单的参数进行测试
            result = await mcp_client_oneshot.call_tool("search_papers", {
                "query": "machine learning",
                "limit": 2
            })
            print("✅ 搜索论文成功")
            print(f"   结果类型: {type(result)}")
            
            # 详细分析结果
            if isinstance(result, dict):
                print(f"   结果键: {list(result.keys())}")
                
                # 检查是否是工具调用结果
                if "content" in result:
                    content = result["content"]
                    print(f"   内容类型: {type(content)}")
                    if isinstance(content, list):
                        print(f"   内容项数: {len(content)}")
                        for i, item in enumerate(content[:2]):
                            print(f"   项 {i}: {type(item)} - {str(item)[:100]}")
                    else:
                        print(f"   内容: {str(content)[:200]}")
                
                # 检查是否包含论文数据
                elif "papers" in result:
                    papers = result["papers"]
                    print(f"   找到论文数量: {len(papers) if isinstance(papers, list) else 'N/A'}")
                
                # 检查是否是初始化响应（错误情况）
                elif "protocolVersion" in result:
                    print("   ❌ 返回的是初始化响应，不是工具调用结果")
                    print(f"   服务器信息: {result.get('serverInfo', {})}")
                
                else:
                    print(f"   未知结果格式: {result}")
            else:
                print(f"   结果内容: {result}")
            
        except Exception as e:
            print(f"❌ 搜索论文失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. 直接测试工具调用（跳过便捷方法）
        print("\n3. 直接测试工具调用...")
        try:
            result = await mcp_client_oneshot.call_tool("search_papers", {
                "query": "test",
                "limit": 1
            })
            print("✅ 直接工具调用成功")
            print(f"   结果: {result}")
        except Exception as e:
            print(f"❌ 直接工具调用失败: {e}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await mcp_client_oneshot.cleanup()


if __name__ == "__main__":
    asyncio.run(test_mcp_detailed())
