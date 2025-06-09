#!/usr/bin/env python3
import subprocess
import sys
import os

def cleanup_mcp_processes():
    print("=== 清理MCP进程 ===")
    
    try:
        # 查找MCP相关进程
        result = subprocess.run([
            'pgrep', '-f', 'openresearch-mcp-server'
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"找到MCP进程: {pids}")
            
            for pid in pids:
                try:
                    print(f"终止进程 {pid}")
                    subprocess.run(['kill', '-9', pid], check=True)
                    print(f"✅ 进程 {pid} 已终止")
                except Exception as e:
                    print(f"❌ 无法终止进程 {pid}: {e}")
        else:
            print("没有找到MCP进程")
            
    except Exception as e:
        print(f"清理过程出错: {e}")
    
    # 清空日志文件
    log_path = "/Users/zhouxin/Workspace/ai-space/openresearch/openresearch-mcp-server/logs/mcp_debug.log"
    try:
        with open(log_path, 'w') as f:
            f.write("")
        print(f"✅ 已清空日志文件: {log_path}")
    except Exception as e:
        print(f"❌ 清空日志文件失败: {e}")

if __name__ == "__main__":
    cleanup_mcp_processes()
