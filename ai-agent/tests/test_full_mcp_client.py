#!/usr/bin/env python3
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mcp_client_stdio import mcp_client_stdio
from configs.mcp_config import mcp_config

async def test_fixed_client():
    print("=== 测试修复后的MCP客户端 ===")
    
    # 清空日志文件
    with open(mcp_config.debug_log_path, 'w') as f:
        f.write("")
    print(f"已清空日志文件: {mcp_config.debug_log_path}")
    
    try:
        async with mcp_client_stdio:
            print("✅ MCP客户端初始化成功")
            
            # 获取可用工具
            tools = mcp_client_stdio.get_available_tools()
            print(f"可用工具数量: {len(tools)}")
            for tool in tools:
                print(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")
            
            # 测试健康检查
            print("\n测试健康检查...")
            health = await mcp_client_stdio.health_check()
            print(f"健康状态: {health}")
            
            # 测试搜索作者
            print("\n测试搜索作者...")
            try:
                result = await mcp_client_stdio.search_authors("Jiajing Wu", limit=1)
                print(f"搜索结果类型: {type(result)}")
                print(f"搜索结果: {result}")
            except Exception as e:
                print(f"搜索作者失败: {e}")
            
            print("✅ 所有测试完成")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 等待一下让日志写入
    await asyncio.sleep(1)
    
    # 检查日志文件
    print(f"\n=== 检查日志文件 ===")
    try:
        with open(mcp_config.debug_log_path, 'r') as f:
            log_content = f.read()
        
        print(f"日志文件大小: {len(log_content)} 字符")
        if log_content:
            # 检查是否有错误
            if "error" in log_content.lower() or "traceback" in log_content.lower():
                print("⚠️  发现错误日志:")
                error_lines = [line for line in log_content.split('\n') if 'error' in line.lower() or 'traceback' in line.lower()]
                for line in error_lines[-5:]:  # 显示最后5个错误
                    print(f"  {line}")
            else:
                print("✅ 没有发现错误")
            
            print("\n最新日志内容（最后300字符）:")
            print("-" * 50)
            print(log_content[-300:])
            print("-" * 50)
        else:
            print("❌ 日志文件为空")
    except Exception as e:
        print(f"读取日志文件失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_fixed_client())
