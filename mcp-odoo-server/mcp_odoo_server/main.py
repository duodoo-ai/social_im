import asyncio
import json
import logging
from typing import List, Dict, Any, Iterable
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from . import tools

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    logger.info("启动 MCP Odoo 服务器...")
    
    # 创建MCP服务器实例
    server = Server(name="mcp-odoo-server")
    logger.debug("创建服务器实例成功")
    
    # 定义工具列表处理函数
    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        logger.debug("处理工具列表请求")
        tools_list = [
            types.Tool(
                name="mcp_odoo_get_allowed_models",
                description="获取当前用户可以访问的Odoo业务对象列表",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        }
                    }
                },
                outputSchema={
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            ),
            types.Tool(
                name="mcp_odoo_get_model_metadata",
                description="获取指定Odoo模型的元数据信息，包括字段定义和访问权限",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "要获取元数据的模型名称"
                        }
                    },
                    "required": ["model_name"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "fields": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object"
                            }
                        },
                        "access_rights": {
                            "type": "object",
                            "properties": {
                                "read": {"type": "boolean"},
                                "write": {"type": "boolean"},
                                "create": {"type": "boolean"},
                                "unlink": {"type": "boolean"}
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="mcp_odoo_search_read",
                description="在指定的Odoo模型中搜索并读取记录",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "要搜索的模型名称"
                        },
                        "domain": {
                            "type": "array",
                            "description": "搜索条件域",
                            "items": {
                                "type": "array"
                            }
                        },
                        "fields": {
                            "type": "array",
                            "description": "要返回的字段列表",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["model_name", "domain"]
                },
                outputSchema={
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                }
            ),
            types.Tool(
                name="mcp_odoo_search_knowledge",
                description="在Odoo知识库中进行全文搜索",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        },
                        "keywords": {
                            "type": "array",
                            "description": "搜索关键词列表",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["keywords"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "name": {"type": "string"},
                                    "content": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="mcp_odoo_create_record",
                description="创建新的业务对象记录",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        },
                        "model": {
                            "type": "string",
                            "description": "要创建记录的模型名称"
                        },
                        "values": {
                            "type": "object",
                            "description": "要创建的记录数据"
                        }
                    },
                    "required": ["model", "values"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"},
                                "url": {"type": "string"}
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="mcp_odoo_update_record",
                description="更新现有业务对象记录",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        },
                        "model": {
                            "type": "string",
                            "description": "要更新记录的模型名称"
                        },
                        "id": {
                            "type": "integer",
                            "description": "要更新的记录ID"
                        },
                        "values": {
                            "type": "object",
                            "description": "要更新的字段值"
                        }
                    },
                    "required": ["model", "id", "values"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"},
                                "url": {"type": "string"}
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="mcp_odoo_get_business_license",
                description="查询企业营业执照信息,实时查询企业工商照面信息，返回企业名称、企业类型、注册资本、统一社会信用代码、经营范围、营业期限、上市状态等信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "odoo_url": {
                            "type": "string",
                            "description": "Odoo服务器URL（可选，默认使用配置文件中的值）"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Odoo API密钥（可选，默认使用配置文件中的值）"
                        },
                        "company_name": {
                            "type": "string",
                            "description": "要查询的企业名称"
                        }
                    },
                    "required": ["company_name"]
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "company_name": {"type": "string"},
                                "company_type": {"type": "string"},
                                "registered_capital": {"type": "string"},
                                "social_credit_code": {"type": "string"},
                                "business_scope": {"type": "string"},
                                "business_term": {"type": "string"},
                                "business_status": {"type": "string"},
                                "business_address": {"type": "string"},
                                "business_phone": {"type": "string"},
                                "business_email": {"type": "string"}
                            }
                        }
                    }
                }
            )
        ]
        logger.debug(f"返回工具列表: {[tool.name for tool in tools_list]}")
        return tools_list
    
    # 定义工具调用处理函数
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        logger.info(f"调用工具: {name}")
        logger.debug(f"工具参数: {json.dumps(arguments, ensure_ascii=False)}")
        
        try:
            result = None
            if name == "mcp_odoo_get_allowed_models":
                result = await tools.get_allowed_models(arguments)
                logger.debug(f"获取允许的模型列表结果: {result}")
            elif name == "mcp_odoo_get_model_metadata":
                result = await tools.get_model_metadata(arguments)
                logger.debug(f"获取模型元数据结果: {result}")
            elif name == "mcp_odoo_search_read":
                result = await tools.search_read(arguments)
                logger.debug(f"搜索读取结果: {result}")
            elif name == "mcp_odoo_search_knowledge":
                result = await tools.search_knowledge(arguments)
                logger.debug(f"搜索知识库结果: {result}")
            elif name == "mcp_odoo_create_record":
                result = await tools.create_record(arguments)
                logger.debug(f"创建记录结果: {result}")
            elif name == "mcp_odoo_update_record":
                result = await tools.update_record(arguments)
                logger.debug(f"更新记录结果: {result}")
            elif name == "mcp_odoo_get_business_license":
                result = await tools.get_business_license(arguments)
                logger.debug(f"查询企业营业执照信息结果: {result}")
            else:
                logger.error(f"未知的工具: {name}")
                result = {
                    "status": "error",
                    "message": f"未知的工具: {name}"
                }
            
            # 如果结果为None，返回错误信息
            if result is None:
                result = {
                    "status": "error",
                    "message": "工具调用返回空结果"
                }
                
            # 创建响应内容
            response = [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
            logger.debug(f"响应内容: {response}")
            return response
            
        except Exception as e:
            logger.error(f"工具调用出错: {str(e)}", exc_info=True)
            error_result = {
                "status": "error",
                "message": f"工具调用出错: {str(e)}"
            }
            return [types.TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False))]
    
    # 启动服务器
    async def run_server():
        logger.info("启动服务器...")
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.debug("stdio 服务器已启动")
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"服务器运行出错: {str(e)}", exc_info=True)
            raise
    
    await run_server()

if __name__ == "__main__":
    main() 