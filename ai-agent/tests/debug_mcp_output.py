"""
调试MCP输出解析
"""
import json

# 从你的输出中提取的实际响应
sample_output = '''{"event": "Starting OpenResearch MCP Server", "logger": "__main__", "level": "info", "timestamp": "2025-06-06T03:02:09.784470Z"}
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":false}},"serverInfo":{"name":"OpenResearch MCP Server","version":"1.0.0"}}}
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"search_authors","description":"搜索学术作者","inputSchema":{"type":"object","properties":{"query":{"type":"string","description":"作者姓名查询"},"filters":{"type":"object","description":"过滤条件","properties":{"affiliation":{"type":"string","description":"机构名称"},"research_area":{"type":"string","description":"研究领域"}}},"limit":{"type":"integer","minimum":1,"maximum":100,"default":20}},"required":["query"]}},{"name":"get_author_details","description":"获取作者详细信息","inputSchema":{"type":"object","properties":{"author_ids":{"type":"array","items":{"type":"string"},"description":"作者ID列表"}},"required":["author_ids"]}},{"name":"search_papers","description":"搜索学术论文，支持关键词、作者、时间范围等过滤条件","inputSchema":{"type":"object","properties":{"query":{"type":"string","description":"搜索查询，支持论文标题关键词"},"filters":{"type":"object","description":"过滤条件","properties":{"keywords":{"type":"string","description":"关键词"},"author":{"type":"string","description":"作者名称"},"year":{"type":"integer","description":"发表年份"},"venue":{"type":"string","description":"会议或期刊名称"},"doi":{"type":"string","description":"DOI"}}},"limit":{"type":"integer","minimum":1,"maximum":100,"default":20,"description":"返回结果数量"}},"required":["query"]}}]}}'''

def parse_mcp_output(stdout: str):
    """解析MCP服务器输出"""
    responses = []
    
    for line in stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        try:
            data = json.loads(line)
            if isinstance(data, dict) and data.get("jsonrpc") == "2.0":
                responses.append(data)
                print(f"找到JSON-RPC响应: ID={data.get('id')}, 有结果={('result' in data)}")
        except json.JSONDecodeError:
            print(f"跳过非JSON行: {line[:50]}...")
    
    return responses

print("=== 调试MCP输出解析 ===")
responses = parse_mcp_output(sample_output)
print(f"\n找到 {len(responses)} 个响应")

for i, resp in enumerate(responses):
    print(f"\n响应 {i+1}:")
    print(f"  ID: {resp.get('id')}")
    print(f"  有结果: {'result' in resp}")
    if 'result' in resp:
        result = resp['result']
        if 'tools' in result:
            print(f"  工具数量: {len(result['tools'])}")
            print(f"  工具名称: {[t['name'] for t in result['tools']]}")
        else:
            print(f"  结果键: {list(result.keys())}")
