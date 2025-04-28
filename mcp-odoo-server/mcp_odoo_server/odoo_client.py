import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

class OdooClient:
    """Odoo API客户端类"""
    
    def __init__(self, base_url: str, api_key: str):
        """初始化Odoo客户端
        
        Args:
            base_url: Odoo服务器URL
            api_key: Odoo API密钥
        """
        logger.debug(f"初始化 Odoo 客户端，base_url: {base_url}")

        logger.debug(f"os.environ: {os.environ}")

        base_url = os.environ.get('ODOO_URL') if not base_url else base_url
        api_key = os.environ.get('ODOO_API_KEY') if not api_key else api_key
        
        if not base_url:
            logger.error("base_url不能为空")
            raise ValueError("base_url不能为空")
        if not api_key:
            logger.error("api_key不能为空")
            raise ValueError("api_key不能为空")
            
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        logger.debug("Odoo 客户端初始化完成")
        
    def get_allowed_models(self) -> List[Dict[str, Any]]:
        """获取允许访问的业务对象列表"""
        url = f"{self.base_url}/api/v1/models"
        logger.info(f"获取允许访问的业务对象列表，URL: {url}")
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"获取到的模型列表: {data['data']}")
            return data['data']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"获取模型列表时发生错误: {str(e)}", exc_info=True)
            raise
        
    def get_model_metadata(self, model_name: str) -> Dict[str, Any]:
        """获取模型元数据"""
        url = f"{self.base_url}/api/v1/metadata/{model_name}"
        logger.info(f"获取模型元数据，model_name: {model_name}, URL: {url}")
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"获取到的元数据: {data['data']}")
            return data['data']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"获取模型元数据时发生错误: {str(e)}", exc_info=True)
            raise
        
    def search_read(
        self,
        model_name: str,
        domain: List[List[Any]],
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """搜索并读取记录"""
        url = f"{self.base_url}/api/v1/{model_name}/search_read"
        logger.info(f"搜索并读取记录，model_name: {model_name}, URL: {url}")
        logger.debug(f"搜索条件: {domain}")
        logger.debug(f"返回字段: {fields}")
        
        try:
            payload = {
                "params": {
                    "domain": domain,
                    "fields": fields or []
                }
            }
            logger.debug(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"搜索结果: {data['data']}")
            return data['data']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"搜索读取记录时发生错误: {str(e)}", exc_info=True)
            raise
        
    def search_knowledge(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """在知识库中搜索内容
        
        Args:
            keywords: 搜索关键词列表
            
        Returns:
            搜索结果列表，每个结果包含文章信息
        """
        url = f"{self.base_url}/api/v1/knowledge/search"
        logger.info(f"搜索知识库内容，关键词: {keywords}, URL: {url}")
        
        try:
            payload = {
                "keywords": keywords

            }
            logger.debug(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"搜索结果: {data['data']}")
            return data['data']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"搜索知识库内容时发生错误: {str(e)}", exc_info=True)
            raise

    def create_record(self, model: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的业务对象记录
        
        Args:
            model: 模型名称
            values: 要创建的记录数据
            
        Returns:
            创建的记录信息
        """
        url = f"{self.base_url}/api/v1/object/create"
        logger.info(f"创建记录，model: {model}, URL: {url}")
        logger.debug(f"记录数据: {values}")
        
        try:
            payload = {
                "model": model,
                "values": values
            }
            logger.debug(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"创建结果: {data['data']}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"创建记录时发生错误: {str(e)}", exc_info=True)
            raise
            
    def update_record(self, model: str, record_id: int, values: Dict[str, Any]) -> Dict[str, Any]:
        """更新现有业务对象记录
        
        Args:
            model: 模型名称
            record_id: 记录ID
            values: 要更新的字段值
            
        Returns:
            更新后的记录信息
        """
        url = f"{self.base_url}/api/v1/object/update"
        logger.info(f"更新记录，model: {model}, id: {record_id}, URL: {url}")
        logger.debug(f"更新数据: {values}")
        
        try:
            payload = {
                "model": model,
                "id": record_id,
                "values": values
            }
            logger.debug(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"更新结果: {data['data']}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"更新记录时发生错误: {str(e)}", exc_info=True)
            raise 

    def get_business_license(self, company_name: str) -> Dict[str, Any]:
        """查询企业营业执照信息
        
        Args:
            company_name: 企业名称
                
        Returns:
            Dict[str, Any]: 企业营业执照信息
        """
        url = f"{self.base_url}/api/v1/qcc/business_license"
        logger.info(f"查询企业营业执照信息，company_name: {company_name}, URL: {url}")
        
        try:
            payload = {
                "company_name": company_name
            }
            logger.debug(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False
            )
            logger.debug(f"API响应状态码: {response.status_code}")
            logger.debug(f"API响应内容: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            logger.debug(f"mcp-server 查询结果: {data}")
            
            if data['status'] != 'success':
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API调用失败: {error_msg}")
                raise ValueError(error_msg)
                
            logger.debug(f"查询结果: {data}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {str(e)}", exc_info=True)
            raise ValueError(f"HTTP request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"查询企业营业执照信息时发生错误: {str(e)}", exc_info=True)
            raise