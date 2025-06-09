#!/usr/bin/env python3
"""
测试MCP服务器的search_authors工具
"""
import asyncio
import json
import sys
import os
from datetime import datetime
import subprocess

# MCP服务器配置
MCP_SERVER_PATH = "/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server"
MCP_PYTHON = os.path.join(MCP_SERVER_PATH, "venv/bin/python")
MCP_COMMAND = os.path.join(MCP_SERVER_PATH, "src/main.py")

class MCPTester:
    def __init__(self):
        self.process = None
        self.request_id = 0
    
    def get_next_id(self):
        self.request_id += 1
        return self.request_id
    
    async def start_server(self):
        """启动MCP服务器"""
        print(f"🚀 启动MCP服务器...")
        print(f"   Python: {MCP_PYTHON}")
        print(f"   Command: {MCP_COMMAND}")
        print(f"   CWD: {MCP_SERVER_PATH}")
        
        # 检查文件是否存在
        if not os.path.exists(MCP_PYTHON):
            raise Exception(f"Python解释器不存在: {MCP_PYTHON}")
        if not os.path.exists(MCP_COMMAND):
            raise Exception(f"MCP命令不存在: {MCP_COMMAND}")
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env.pop('DEBUGPY_LAUNCHER_PORT', None)
        env.pop('PYDEVD_LOAD_VALUES_ASYNC', None)
        
        # 启动进程
        self.process = await asyncio.create_subprocess_exec(
            MCP_PYTHON, MCP_COMMAND,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=MCP_SERVER_PATH,
            env=env
        )
        
        print(f"✅ 进程已启动，PID: {self.process.pid}")
        
        # 等待服务器启动
        await asyncio.sleep(2)
        
        # 检查进程状态
        if self.process.returncode is not None:
            stderr_output = ""
            if self.process.stderr:
                try:
                    stderr_data = await asyncio.wait_for(
                        self.process.stderr.read(1024), timeout=1.0
                    )
                    stderr_output = stderr_data.decode()
                except:
                    pass
            raise Exception(f"进程启动失败: {stderr_output}")
    
    async def send_request(self, method: str, params: dict = None) -> dict:
        """发送JSON-RPC请求"""
        if not self.process or not self.process.stdin:
            raise Exception("进程未启动")
        
        request_id = self.get_next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        print(f"📤 发送请求: {method}")
        print(f"   ID: {request_id}")
        print(f"   参数: {json.dumps(params, indent=2, ensure_ascii=False)}")
        
        # 发送请求
        request_line = json.dumps(request, ensure_ascii=False) + "\n"
        self.process.stdin.write(request_line.encode('utf-8'))
        await self.process.stdin.drain()
        
        # 读取响应
        response = await self.read_response()
        
        if "error" in response:
            print(f"❌ 错误响应: {response['error']}")
            raise Exception(f"MCP错误: {response['error']}")
        
        print(f"✅ 成功响应")
        return response.get("result", {})
    
    async def send_notification(self, method: str, params: dict = None):
        """发送通知（无响应）"""
        if not self.process or not self.process.stdin:
            raise Exception("进程未启动")
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        print(f"📢 发送通知: {method}")
        
        notification_line = json.dumps(notification, ensure_ascii=False) + "\n"
        self.process.stdin.write(notification_line.encode('utf-8'))
        await self.process.stdin.drain()
    
    async def read_response(self, timeout: float = 30.0) -> dict:
        """读取JSON响应"""
        if not self.process or not self.process.stdout:
            raise Exception("进程不可用")
        
        max_attempts = 50
        attempt = 0
        collected_lines = []
        
        while attempt < max_attempts:
            try:
                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=timeout if attempt == 0 else 5.0
                )
                
                if not line:
                    raise Exception("服务器连接断开")
                
                line_str = line.decode('utf-8').strip()
                collected_lines.append(line_str)
                
                print(f"📥 收到数据: {line_str[:100]}{'...' if len(line_str) > 100 else ''}")
                
                if not line_str:
                    attempt += 1
                    continue
                
                try:
                    data = json.loads(line_str)
                    if isinstance(data, dict) and data.get("jsonrpc") == "2.0":
                        return data
                except json.JSONDecodeError:
                    print(f"   ⚠️  非JSON数据，继续读取...")
                
                attempt += 1
                
            except asyncio.TimeoutError:
                print(f"   ⏰ 读取超时，尝试 {attempt + 1}/{max_attempts}")
                attempt += 1
                continue
        
        print(f"❌ 未找到有效响应，收集到的行:")
        for i, line in enumerate(collected_lines[-10:]):
            print(f"   {i}: {line}")
        
        raise Exception("未找到有效的JSON-RPC响应")
    
    async def initialize(self):
        """初始化MCP连接"""
        print("\n🔧 初始化MCP连接...")
        
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "mcp-tester",
                "version": "1.0.0"
            }
        }
        
        result = await self.send_request("initialize", params)
        print(f"   服务器能力: {json.dumps(result.get('capabilities', {}), indent=2, ensure_ascii=False)}")
        
        # 发送初始化完成通知
        await self.send_notification("notifications/initialized")
        print("✅ 初始化完成")
    
    async def list_tools(self):
        """获取工具列表"""
        print("\n🔍 获取工具列表...")
        
        result = await self.send_request("tools/list")
        tools = result.get("tools", [])
        
        print(f"   找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description', 'N/A')}")
        
        return tools
    
    async def test_search_authors(self, query: str = "Jiajing Wu", limit: int = 10):
        """测试search_authors工具"""
        print(f"\n🔎 测试search_authors工具...")
        print(f"   查询: {query}")
        print(f"   限制: {limit}")
        
        params = {
            "name": "search_authors",
            "arguments": {
                "query": query,
                "limit": limit
            }
        }
        
        result = await self.send_request("tools/call", params)
        
        print(f"📊 搜索结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 解析结果
        if "content" in result:
            for content_item in result["content"]:
                if content_item.get("type") == "text":
                    try:
                        data = json.loads(content_item["text"])
                        if "authors" in data:
                            authors = data["authors"]
                            print(f"\n   找到 {len(authors)} 位作者:")
                            for i, author in enumerate(authors[:5], 1):  # 只显示前5个
                                print(f"   {i}. {author.get('name', 'N/A')}")
                                print(f"      ID: {author.get('authorId', 'N/A')}")
                                print(f"      论文数: {author.get('paperCount', 'N/A')}")
                                print(f"      引用数: {author.get('citationCount', 'N/A')}")
                                if author.get('affiliations'):
                                    print(f"      机构: {author['affiliations'][0] if author['affiliations'] else 'N/A'}")
                                print()
                    except json.JSONDecodeError:
                        print(f"   文本内容: {content_item['text'][:200]}...")
        
        return result
    
    async def cleanup(self):
        """清理资源"""
        print("\n🧹 清理资源...")
        
        if self.process:
            try:
                # 尝试优雅关闭
                if self.process.returncode is None:
                    await self.send_notification("notifications/shutdown")
                    
                    if self.process.stdin:
                        self.process.stdin.close()
                        await self.process.stdin.wait_closed()
                    
                    # 等待进程结束
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        print("   ⚠️  进程未正常结束，强制终止")
                        self.process.kill()
                        await self.process.wait()
                
                print("✅ 清理完成")
            except Exception as e:
                print(f"⚠️  清理时出错: {e}")

async def main():
    """主测试函数"""
    print("🧪 MCP search_authors 工具测试")
    print("=" * 50)
    
    tester = MCPTester()
    
    try:
        # 启动服务器
        await tester.start_server()
        
        # 初始化连接
        await tester.initialize()
        
        # 获取工具列表
        tools = await tester.list_tools()
        
        # 检查search_authors工具是否存在
        search_authors_tool = None
        for tool in tools:
            if tool.get("name") == "search_authors":
                search_authors_tool = tool
                break
        
        if not search_authors_tool:
            print("❌ 未找到search_authors工具")
            return
        
        print(f"✅ 找到search_authors工具:")
        print(f"   描述: {search_authors_tool.get('description', 'N/A')}")
        print(f"   参数: {json.dumps(search_authors_tool.get('inputSchema', {}), indent=2, ensure_ascii=False)}")
        
        # 测试不同的查询
        test_queries = [
            ("Jiajing Wu", 10),
            ("Andrew Ng", 5),
            ("Geoffrey Hinton", 3)
        ]
        
        for query, limit in test_queries:
            try:
                await tester.test_search_authors(query, limit)
                print(f"✅ 查询 '{query}' 成功")
            except Exception as e:
                print(f"❌ 查询 '{query}' 失败: {e}")
            
            print("-" * 30)
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    # 运行测试
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  用户中断测试")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)
