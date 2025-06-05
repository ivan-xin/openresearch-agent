#!/usr/bin/env python3
"""
测试 MCP 连接
"""
import asyncio
import subprocess
import json
import os

async def test_mcp_connection():
    """测试 MCP 连接"""
    
    # 测试1：检查 MCP 服务器是否能启动
    print("=== 测试1：启动 MCP 服务器进程 ===")
    
    # 尝试不同的启动方式
    commands = [
        ["python", "../openresearch-mcp-server/src/main.py"],
        ["bash", "-c", "cd ../openresearch-mcp-server && python src/main.py"],
        ["python", "/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server/src/main.py"]
    ]
    
    for i, cmd in enumerate(commands):
        print(f"\n尝试命令 {i+1}: {cmd}")
        
        try:
            # 启动进程
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # 等待一下
            await asyncio.sleep(2)
            
            # 检查进程状态
            if process.poll() is not None:
                stderr_output = process.stderr.read() if process.stderr else "No error output"
                print(f"❌ 进程启动失败: {stderr_output}")
                continue
            
            print("✅ 进程启动成功")
            
            # 测试2：发送初始化请求
            print("\n=== 测试2：发送初始化请求 ===")
            
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            # 发送请求
            request_line = json.dumps(init_request) + "\n"
            print(f"发送请求: {request_line.strip()}")
            
            process.stdin.write(request_line)
            process.stdin.flush()
            
            # 读取响应
            try:
                response_line = await asyncio.wait_for(
                    asyncio.to_thread(process.stdout.readline),
                    timeout=10
                )
                
                if response_line:
                    print(f"✅ 收到响应: {response_line.strip()}")
                    
                    # 解析响应
                    try:
                        response = json.loads(response_line.strip())
                        if "error" in response:
                            print(f"❌ 服务器返回错误: {response['error']}")
                        else:
                            print("✅ 初始化成功")
                            
                            # 测试3：获取工具列表
                            print("\n=== 测试3：获取工具列表 ===")
                            
                            tools_request = {
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "tools/list",
                                "params": {}
                            }
                            
                            tools_line = json.dumps(tools_request) + "\n"
                            process.stdin.write(tools_line)
                            process.stdin.flush()
                            
                            tools_response = await asyncio.wait_for(
                                asyncio.to_thread(process.stdout.readline),
                                timeout=10
                            )
                            
                            if tools_response:
                                print(f"✅ 工具列表响应: {tools_response.strip()}")
                            else:
                                print("❌ 没有收到工具列表响应")
                                
                    except json.JSONDecodeError as e:
                        print(f"❌ 响应不是有效的 JSON: {e}")
                        
                else:
                    print("❌ 没有收到响应")
                    
            except asyncio.TimeoutError:
                print("❌ 响应超时")
            
            # 清理进程
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            print(f"\n✅ 命令 {i+1} 测试完成")
            return  # 找到可用的命令就退出
            
        except Exception as e:
            print(f"❌ 命令 {i+1} 测试失败: {e}")
            continue
    
    print("\n❌ 所有命令都失败了")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
