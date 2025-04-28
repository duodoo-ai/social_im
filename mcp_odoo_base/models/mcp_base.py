from odoo import models, fields, api
from typing import Dict, Any, List
import requests
import json
import time
import hashlib
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class MCPBase(models.AbstractModel):
    _name = 'mcp.base'
    _description = 'MCP Base Model'

    @api.model
    def get_resource_schema(self) -> Dict[str, Any]:
        """获取资源schema"""
        fields_info = self.fields_get()
        properties = {}
        
        for field_name, field_info in fields_info.items():
            field_type = field_info.get('type')
            if field_type in ['char', 'text']:
                properties[field_name] = {"type": "string"}
            elif field_type in ['integer', 'float', 'monetary']:
                properties[field_name] = {"type": "number"}
            elif field_type == 'boolean':
                properties[field_name] = {"type": "boolean"}
            elif field_type == 'date':
                properties[field_name] = {"type": "string", "format": "date"}
            elif field_type == 'datetime':
                properties[field_name] = {"type": "string", "format": "date-time"}
            elif field_type in ['many2one', 'one2many', 'many2many']:
                properties[field_name] = {
                    "type": "array" if field_type in ['one2many', 'many2many'] else "object",
                    "relation": field_info.get('relation')
                }

        return {
            "type": "object",
            "properties": properties
        }

    @api.model
    def mcp_search_read(self, domain: List, fields: List[str], limit: int = 80) -> Dict[str, Any]:
        """MCP标准搜索读取方法"""
        try:
            records = self.search_read(domain=domain, fields=fields, limit=limit)
            return {
                "status": "success",
                "data": records
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    @api.model
    def mcp_create(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """MCP标准创建方法"""
        try:
            record = self.create(values)
            return {
                "status": "success",
                "data": {"id": record.id}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_agent_url = fields.Char(
        string='AI代理服务器URL',
        config_parameter='ai.agent_url',
        help='设置AI代理服务器的URL地址'
    )

    qcc_app_key = fields.Char(
        string='企查查AppKey',
        config_parameter='qcc.app_key',
        help='企查查API的AppKey'
    )

    qcc_secret_key = fields.Char(
        string='企查查SecretKey',
        config_parameter='qcc.secret_key',
        help='企查查API的SecretKey'
    )

class QccBusinessLicense(models.Model):
    _name = 'qcc.business.license'
    _description = '企查查营业执照信息'
    _rec_name = 'company_name'

    company_name = fields.Char('企业名称', required=True, index=True)
    credit_code = fields.Char('统一社会信用代码')
    registration_number = fields.Char('注册号')
    company_type = fields.Char('企业类型')
    legal_representative = fields.Char('法定代表人')
    registered_capital = fields.Char('注册资本')
    paid_in_capital = fields.Char('实缴资本')
    establishment_date = fields.Date('成立日期')
    business_term = fields.Char('营业期限')
    registration_authority = fields.Char('登记机关')
    approval_date = fields.Date('核准日期')
    business_status = fields.Char('登记状态')
    address = fields.Text('注册地址')
    business_scope = fields.Text('经营范围')
    is_listed = fields.Boolean('是否上市')
    stock_number = fields.Char('股票代码')
    stock_type = fields.Char('上市类型')
    
    last_query_time = fields.Datetime('最后查询时间', required=True)
    active = fields.Boolean('有效', default=True)

    _sql_constraints = [
        ('company_name_uniq', 'unique(company_name)', '企业名称必须唯一!')
    ]

class MCPQcc(models.AbstractModel):
    _name = 'mcp.qcc'
    _description = '企查查'

    def _generate_qcc_token(self, app_key, timespan, secret_key):
        """生成企查查API的Token"""
        src = f"{app_key}{timespan}{secret_key}"
        return hashlib.md5(src.encode()).hexdigest().upper()

    def query_business_license(self, company_name):
        """查询企业营业执照信息"""
        try:
            # 先查询本地数据库
            QccLicense = self.env['qcc.business.license']
            license = QccLicense.search([('company_name', '=', company_name)], limit=1)
            
            # 如果存在记录且未超过6个月，直接返回
            if license and license.last_query_time > datetime.now() - timedelta(days=180):
                _logger.info(f"查询企业营业执照信息: {license.company_name} 从缓存中获取")
                return {
                    "status": 'success',
                    "data": {
                        "name": license.company_name,
                        "credit_code": license.credit_code,
                        "registration_number": license.registration_number,
                        "company_type": license.company_type,
                        "legal_representative": license.legal_representative,
                        "registered_capital": license.registered_capital,
                        "paid_in_capital": license.paid_in_capital,
                        "establishment_date": license.establishment_date,
                        "business_term": license.business_term,
                        "registration_authority": license.registration_authority,
                        "approval_date": license.approval_date,
                        "business_status": license.business_status,
                        "address": license.address,
                        "business_scope": license.business_scope,
                        "is_listed": license.is_listed,
                        "stock_number": license.stock_number,
                        "stock_type": license.stock_type
                    },
                    "from_cache": True,
                    "message": "查询成功"
                }

            # 获取企查查API配置
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            app_key = IrConfigParameter.get_param('qcc.app_key')
            secret_key = IrConfigParameter.get_param('qcc.secret_key')
            
            if not app_key or not secret_key:
                return {
                    "status": 'error',
                    "message": "未配置企查查API密钥，请在系统参数中配置 qcc.app_key 和 qcc.secret_key"
                }
            
            # 准备请求参数
            timespan = str(int(time.time()))
            token = self._generate_qcc_token(app_key, timespan, secret_key)
            
            # 调用企查查API
            headers = {
                'Token': token,
                'Timespan': timespan
            }
            
            params = {
                'key': app_key,
                'keyword': company_name
            }
            
            response = requests.get(
                'https://api.qichacha.com/ECIV4/GetBasicDetailsByName',
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                _logger.error(f"企查查API请求失败: HTTP {response.status_code}")
                return {
                    "status": 'error',
                    "message": f"企查查API请求失败: HTTP {response.status_code}"
                }
            
            result = response.json()
            if result.get('Status') != '200':
                return {
                    "status": 'error',
                    "message": f"企查查API返回错误: {result.get('Message')}"
                }
                
            _logger.info(f"企查查API返回数据: {result}")
            # 处理返回数据
            data = result.get('Result', {})
            
            # 更新或创建记录
            license_data = {
                'company_name': data.get('Name'),
                'credit_code': data.get('CreditCode'),
                'registration_number': data.get('No'),
                'company_type': data.get('EconKind'),
                'legal_representative': data.get('OperName'),
                'registered_capital': data.get('RegistCapi'),
                'paid_in_capital': data.get('RecCap'),
                'establishment_date': data.get('StartDate'),
                'business_term': f"{data.get('TermStart')} 至 {data.get('TermEnd')}",
                'registration_authority': data.get('BelongOrg'),
                'approval_date': data.get('CheckDate'),
                'business_status': data.get('Status'),
                'address': data.get('Address'),
                'business_scope': data.get('Scope'),
                'is_listed': data.get('IsOnStock') == '1',
                'stock_number': data.get('StockNumber'),
                'stock_type': data.get('StockType'),
                'last_query_time': fields.Datetime.now()
            }

            if license:
                license.write(license_data)
            else:
                QccLicense.create(license_data)

            return {
                "status": 'success',
                "data": license_data,
                "from_cache": False,
                "message": "查询成功"
            }
        except Exception as e:
            return {
                "status": 'error',
                "message": str(e),
                "from_cache": False
            } 