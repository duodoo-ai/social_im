import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Odoo配置
ODOO_URL = "http://127.0.0.1:8069"
ODOO_API_KEY = "2f79657a-8582-47b1-a3e6-29553841984b"

# 创建服务器参数
server_params = StdioServerParameters(
    command=os.path.join(os.environ.get("VIRTUAL_ENV", "/home/jason/app/odoo18/venv"), "bin", "mcp-odoo-server"),
    args=[],
    env={
        "ODOO_URL": ODOO_URL,
        "ODOO_API_KEY": ODOO_API_KEY,
        "PYTHONPATH": os.getcwd()
    }
)

async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    """处理采样消息的回调函数"""
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello from Odoo MCP server",
        ),
        model="odoo-18.0",
        stopReason="endTurn",
    )

async def main():
    """测试MCP客户端与服务器的连接"""
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=handle_sampling_message) as session:
                # 初始化连接
                print("正在初始化连接...")
                await session.initialize()
                
                # 获取可用工具列表
                print("\n获取可用工具列表...")
                tools_result = await session.list_tools()
                print(f"发现工具列表:")
                for tool in tools_result.tools:
                    print(f"\n工具名称: {tool.name}")
                    print(f"描述: {tool.description}")
                    print("输入模式:")
                    print(json.dumps(tool.inputSchema, indent=2, ensure_ascii=False))
                    if hasattr(tool, 'outputSchema'):
                        print("输出模式:")
                        print(json.dumps(tool.outputSchema, indent=2, ensure_ascii=False))
                
                # 测试 mcp_odoo_get_allowed_models 工具
                print("\n测试 mcp_odoo_get_allowed_models 工具...")
                result = await session.call_tool(
                    "mcp_odoo_get_allowed_models",
                    {
                        "odoo_url": ODOO_URL,
                        "api_key": ODOO_API_KEY
                    }
                )
                print('result:', result)
                
                # 处理返回结果
                if hasattr(result, 'content'):
                    for content in result.content:
                        try:
                            if isinstance(content, types.TextContent):
                                # 尝试解析JSON字符串
                                try:
                                    models = json.loads(content.text)
                                    print("\n可访问的模型列表:")
                                    for model in models:
                                        print(f"- {model}")
                                except json.JSONDecodeError:
                                    print(content.text)
                            elif isinstance(content, types.JSONContent):
                                print(json.dumps(content.json, indent=2, ensure_ascii=False))
                            else:
                                print(f"未知的内容类型: {type(content)}")
                        except Exception as e:
                            print(f"处理内容时出错: {str(e)}")
                            print(f"内容: {content}")
                else:
                    print(f"未知的结果类型: {type(result)}")
                    
                # 测试知识库检索功能
                print("\n测试知识库检索功能...")
                knowledge_result = await session.call_tool(
                    "mcp_odoo_search_knowledge",
                    {
                        "odoo_url": ODOO_URL,
                        "api_key": ODOO_API_KEY,
                        "keywords": ["智能制造", "生产计划"]
                    }
                )
                print('知识库检索结果:', knowledge_result)
                
                # 处理知识库检索结果
                if hasattr(knowledge_result, 'content'):
                    for content in knowledge_result.content:
                        try:
                            if isinstance(content, types.TextContent):
                                try:
                                    articles = json.loads(content.text)
                                    print("\n知识库文章列表:")
                                    for article in articles:
                                        print(f"- 标题: {article.get('name', 'N/A')}")
                                        print(f"  内容预览: {article.get('content', 'N/A')[:100]}...")
                                except json.JSONDecodeError:
                                    print(content.text)
                            elif isinstance(content, types.JSONContent):
                                print(json.dumps(content.json, indent=2, ensure_ascii=False))
                            else:
                                print(f"未知的内容类型: {type(content)}")
                        except Exception as e:
                            print(f"处理知识库检索内容时出错: {str(e)}")
                            print(f"内容: {content}")
                else:
                    print(f"未知的知识库检索结果类型: {type(knowledge_result)}")
    
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())