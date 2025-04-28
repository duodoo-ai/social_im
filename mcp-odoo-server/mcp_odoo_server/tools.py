import logging
from typing import Dict, List, Any, Optional
import mcp.types as types
from .odoo_client import OdooClient

# 配置日志
logger = logging.getLogger(__name__)

def get_client(odoo_url: str = None, api_key: str = None) -> OdooClient:
    """获取Odoo客户端实例"""
     
    logger.debug(f"创建 Odoo 客户端实例，URL: {odoo_url}")
    return OdooClient(
        base_url=odoo_url,
        api_key=api_key
    )

async def get_allowed_models(arguments: dict = None) -> Dict[str, Any]:
    """获取允许访问的业务对象列表"""
    logger.info("获取允许访问的业务对象列表")
    logger.debug(f"参数: {arguments}")
    
    try:
        client = get_client()
        result = client.get_allowed_models()
        logger.debug(f"获取到的模型列表: {result}")
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"获取模型列表失败: {str(e)}"
        }

async def get_model_metadata(arguments: dict) -> Dict[str, Any]:
    """获取模型元数据"""
    logger.info("获取模型元数据")
    logger.debug(f"参数: {arguments}")
    
    try:
        # 使用参数中的值（如果有），否则使用配置文件中的值
        model_name = arguments["model_name"]
        client = get_client()
        logger.debug(f"获取模型 {model_name} 的元数据")
        result = client.get_model_metadata(model_name)
        logger.debug(f"获取到的元数据: {result}")
        return {
            "status": "success",
            "data": result
        }
    except KeyError as e:
        logger.error(f"缺少必需的参数: {str(e)}")
        return {
            "status": "error",
            "message": f"缺少必需的参数: {str(e)}"
        }
    except Exception as e:
        logger.error(f"获取模型元数据失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"获取模型元数据失败: {str(e)}"
        }

async def search_read(arguments: dict) -> Dict[str, Any]:
    """搜索并读取记录"""
    logger.info("搜索并读取记录")
    logger.debug(f"参数: {arguments}")
    
    try:
        # 使用参数中的值（如果有），否则使用配置文件中的值
        model_name = arguments["model_name"]
        domain = arguments["domain"]
        fields = arguments.get("fields")
        
        client = get_client()
        logger.debug(f"搜索模型: {model_name}")
        logger.debug(f"搜索条件: {domain}")
        logger.debug(f"返回字段: {fields}")
        
        result = client.search_read(model_name, domain, fields)
        logger.debug(f"搜索结果: {result}")
        return {
            "status": "success",
            "data": result
        }
    except KeyError as e:
        logger.error(f"缺少必需的参数: {str(e)}")
        return {
            "status": "error",
            "message": f"缺少必需的参数: {str(e)}"
        }
    except Exception as e:
        logger.error(f"搜索读取失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"搜索读取失败: {str(e)}"
        }

async def search_knowledge(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """在Odoo知识库中进行全文搜索
    
    Args:
        arguments: 包含搜索参数的字典
            - keywords: 关键词列表
            - odoo_url: (可选) Odoo服务器URL
            - api_key: (可选) API密钥
    
    Returns:
        Dict[str, Any]: 搜索结果
    """
    logger.info("搜索知识库内容")
    logger.debug(f"参数: {arguments}")
    
    try:
        # 使用参数中的值（如果有），否则使用配置文件中的值
        keywords = arguments["keywords"]
        
        client = get_client()
        logger.debug(f"搜索关键词: {keywords}")
        
        result = client.search_knowledge(keywords)
        logger.debug(f"搜索结果: {result}")

        # 如果结果为空,则返回空列表,并提示"未找到相关知识, 建议更换关键词"
        if not result:
            return {
                "status": "success",
                "data": [],
                "message": "未找到相关知识, 建议更换关键词"
            }
            
        return result  # 知识库搜索已经返回了带有status的结果
    except KeyError as e:
        logger.error(f"缺少必需的参数: {str(e)}")
        return {
            "status": "error",
            "message": f"缺少必需的参数: {str(e)}"
        }
    except Exception as e:
        logger.error(f"知识库搜索失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"知识库搜索失败: {str(e)}"
        }

async def create_record(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """创建新的业务对象记录
    
    Args:
        arguments: 包含创建参数的字典
            - model: 模型名称
            - values: 要创建的记录数据
            - odoo_url: (可选) Odoo服务器URL
            - api_key: (可选) API密钥
    
    Returns:
        Dict[str, Any]: 创建结果
    """
    logger.info("创建新记录")
    logger.debug(f"参数: {arguments}")
    
    try:
        # 使用参数中的值（如果有），否则使用配置文件中的值
        model = arguments["model"]
        values = arguments["values"]
        
        client = get_client()
        logger.debug(f"创建 {model} 记录")
        logger.debug(f"记录数据: {values}")
        
        result = client.create_record(model, values)
        logger.debug(f"创建结果: {result}")
        return result
        
    except KeyError as e:
        logger.error(f"缺少必需的参数: {str(e)}")
        return {
            "status": "error",
            "message": f"缺少必需的参数: {str(e)}"
        }
    except Exception as e:
        logger.error(f"创建记录失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"创建记录失败: {str(e)}"
        }

async def update_record(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """更新现有业务对象记录
    
    Args:
        arguments: 包含更新参数的字典
            - model: 模型名称
            - id: 记录ID
            - values: 要更新的字段值
            - odoo_url: (可选) Odoo服务器URL
            - api_key: (可选) API密钥
    
    Returns:
        Dict[str, Any]: 更新结果
    """
    logger.info("更新记录")
    logger.debug(f"参数: {arguments}")
    
    try:
        # 使用参数中的值（如果有），否则使用配置文件中的值
        model = arguments["model"]
        record_id = arguments["id"]
        values = arguments["values"]
        
        client = get_client()
        logger.debug(f"更新 {model} 记录 {record_id}")
        logger.debug(f"更新数据: {values}")
        
        result = client.update_record(model, record_id, values)
        logger.debug(f"更新结果: {result}")
        return result
        
    except KeyError as e:
        logger.error(f"缺少必需的参数: {str(e)}")
        return {
            "status": "error",
            "message": f"缺少必需的参数: {str(e)}"
        }
    except Exception as e:
        logger.error(f"更新记录失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"更新记录失败: {str(e)}"
        }

async def get_business_license(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """查询企业营业执照信息
    
    Args:
        arguments: 包含查询参数的字典
            - company_name: 企业名称
            - odoo_url: (可选) Odoo服务器URL
            - api_key: (可选) API密钥
    
    Returns:
        Dict[str, Any]: 查询结果
    """
    logger.info("查询企业营业执照信息")
    logger.debug(f"参数: {arguments}")
    
    try:
        # 获取参数
        company_name = arguments["company_name"]
        
        # 创建客户端并发送请求
        client = get_client()
        logger.debug(f"查询企业: {company_name}")
        
        result = client.get_business_license(company_name)
        logger.debug(f"查询结果: {result}")
        return result
        
    except KeyError as e:
        logger.error(f"缺少必需的参数: {str(e)}")
        return {
            "status": "error",
            "message": f"缺少必需的参数: {str(e)}"
        }
    except ValueError as e:
        logger.error(f"参数验证失败: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"查询企业营业执照信息失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"查询失败: {str(e)}"
        }