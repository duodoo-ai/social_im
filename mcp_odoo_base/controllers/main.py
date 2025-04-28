from odoo import http, fields
from odoo.http import request, Response
import json
from typing import Dict, Any, List
import logging
import urllib.parse

_logger = logging.getLogger(__name__)

class MCPController(http.Controller):

    def _verify_api_key(self):
        """验证API密钥
        
        Returns:
            res.users: 验证成功返回用户对象，失败返回None
        """
        api_key = request.httprequest.headers.get('X-API-Key')
        if not api_key:
            return None
        
        try:
            # 使用sudo()避免权限问题
            user = request.env['res.users'].sudo().search([
                ('mcp_api_key', '=', api_key),
                ('mcp_enabled', '=', True)
            ], limit=1)
            
            if user:
                # 设置用户环境
                request.update_env(user=user.id)
                return user
            
            return None
        
        except Exception as e:
            _logger.error("API密钥验证失败: %s", str(e))
            return None

    def _json_response(self, data):
        """返回JSON响应"""
        return Response(
            json.dumps(data, default=str),
            mimetype='application/json'
        )

    def _get_allowed_models(self, user) -> List[str]:
        """获取用户允许访问的业务对象列表"""
        # 使用用户环境获取系统参数
        param = request.env['ir.config_parameter'].sudo().get_param('mcp.allowed_models', '')
        if not param or len(param) == 0:
            # 如果没有限制模型,就获取所有模型
            allowed_models = request.env['ir.model'].sudo().search([])
            # 取模型的名称
            allowed_models = [model.model for model in allowed_models]
            
        else:
            allowed_models = [x.strip() for x in param.split(',') if x.strip()]

        # 过滤出用户有权限访问的模型
        result = []
        for model in allowed_models:
            try:
                # 检查用户是否有读取权限
                if request.env[model].sudo().check_access_rights('read', raise_exception=False):
                    result.append(model)
            except Exception:
                continue
        return result

    def _is_model_allowed(self, model: str, user) -> bool:
        """检查用户是否有权限访问该业务对象"""
        return model in self._get_allowed_models(user)

    def _get_field_info(self, field) -> Dict[str, Any]:
        """获取字段的详细信息"""
        info = {
            'type': field.type,
            'string': field.string,
            'required': field.required,
            'readonly': field.readonly,
            'store': field.store,
            # 'help': field.help,
            # 'compute': field.compute if hasattr(field, 'compute') else None,
            # 'inverse': field.inverse if hasattr(field, 'inverse') else None,
            # 'search': field.search if hasattr(field, 'search') else None,
            'default': field.default if hasattr(field, 'default') else None,
            # 'groups': field.groups if hasattr(field, 'groups') else None,
            # 'states': field.states if hasattr(field, 'states') else None,
            'size': field.size if hasattr(field, 'size') else None,
            # 'translate': field.translate if hasattr(field, 'translate') else None,
            # 'tracking': field.tracking if hasattr(field, 'tracking') else None,
            # 'copy': field.copy if hasattr(field, 'copy') else None,
            # 'index': field.index if hasattr(field, 'index') else None,
        }

        # 处理关系字段
        if field.type in ('many2one', 'one2many', 'many2many'):
            info['relation'] = field.comodel_name
            if field.type in ('one2many', 'many2many'):
                info['relation_field'] = field.relation_field if hasattr(field, 'relation_field') else None
                info['relation_table'] = field.relation if hasattr(field, 'relation') else None
            # if field.type == 'many2one':
            #     info['ondelete'] = field.ondelete if hasattr(field, 'ondelete') else None

        # 处理选择字段
        if field.type == 'selection':
            if callable(field.selection):
                # 如果selection是方法，则调用获取选项
                try:
                    selection = field.selection(request.env[field._model_name].sudo(), {})
                except:
                    selection = []
            else:
                selection = field.selection
            info['selection'] = selection

        # 处理数值字段
        if field.type in ('float', 'monetary'):
            if isinstance(field, fields.Float):
                info['digits'] = getattr(field, 'digits', None)
                if callable(info['digits']):
                    try:
                        info['digits'] = info['digits'](request.env)
                    except:
                        info['digits'] = None

        # 处理货币字段
        if field.type == 'monetary':
            info['currency_field'] = field.currency_field if hasattr(field, 'currency_field') else None

        # 处理二进制字段
        if field.type == 'binary':
            info['attachment'] = field.attachment if hasattr(field, 'attachment') else None

        return info

    def _get_model_fields_info(self, model_obj) -> Dict[str, Any]:
        """获取模型的所有字段信息"""
        fields_info = {}
        
        # 获取所有字段对象
        for field_name, field in model_obj._fields.items():
            try:
                fields_info[field_name] = self._get_field_info(field)
            except Exception as e:
                fields_info[field_name] = {
                    'type': field.type,
                    'string': field.string,
                    'error': str(e)
                }

        return fields_info

    @http.route('/api/v1/models', auth='none', type='http', methods=['GET'], csrf=False)
    def get_allowed_models(self, **kwargs):
        """获取允许访问的业务对象列表"""
        user = self._verify_api_key()
        if not user:
            return self._json_response({
                'status': 'error',
                'message': 'Invalid API key'
            })

        try:
            allowed_models = self._get_allowed_models(user)
            models_info = []
            
            for model_name in allowed_models:
                try:
                    # model = request.env[model_name].with_user(user)
                    model = request.env[model_name].sudo()
                    models_info.append({
                        'model': model_name,
                        'description': model._description or model_name
                    })
                except Exception as e:
                    continue
            
            return self._json_response({
                'status': 'success',
                'data': models_info
            })
        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })

    @http.route('/api/v1/metadata/<string:model>', auth='none', type='http', methods=['GET'], csrf=False)
    def get_model_metadata(self, model: str, **kwargs):
        """获取模型元数据"""
        user = self._verify_api_key()
        if not user:
            return self._json_response({
                'status': 'error',
                'message': 'Invalid API key'
            })

        if not self._is_model_allowed(model, user):
            return self._json_response({
                'status': 'error',
                'message': f'Access to model {model} is not allowed'
            })

        try:
            # model_obj = request.env[model].with_user(user)
            model_obj = request.env[model].sudo()
            
            # 获取模型的基本信息
            model_info = {
                'name': model,
                'description': model_obj._description,
                'transient': model_obj._transient,
                'rec_name': model_obj._rec_name,
                'order': model_obj._order,
                'table': model_obj._table,
                'inherit': model_obj._inherit,
                'inherits': model_obj._inherits,
                'abstract': model_obj._abstract,
                'auto': model_obj._auto,
                'log_access': model_obj._log_access,
            }

            # 获取字段信息
            fields_info = self._get_model_fields_info(model_obj)
            
            # 如果模型有自定义的资源模式，则也包含进来
            if hasattr(model_obj, 'get_resource_schema'):
                model_info['custom_schema'] = model_obj.get_resource_schema()
            
            return self._json_response({
                'status': 'success',
                'data': {
                    'model': model_info,
                    'fields': fields_info
                }
            })
        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })

    @http.route('/api/v1/<string:model>/search_read', auth='none', type='http', methods=['POST'], csrf=False)
    def search_read(self, model: str, **kwargs):
        """查询记录"""
        user = self._verify_api_key()
        if not user:
            return self._json_response({
                'status': 'error',
                'message': 'Invalid API key'
            })

        if not self._is_model_allowed(model, user):
            return self._json_response({
                'status': 'error',
                'message': f'Access to model {model} is not allowed'
            })

        try:
            try:
                body = json.loads(request.httprequest.data.decode())
                params = body.get('params', {})
            except json.JSONDecodeError:
                return self._json_response({
                    'status': 'error',
                    'message': 'Invalid JSON data'
                })
            
            domain = params.get('domain', [])
            fields = params.get('fields', ['id', 'name'])
            limit = params.get('limit', 80)

            _logger.debug(f"search_read: {model}, {domain}, {fields}, {limit}")
            
            model_obj = request.env[model].with_user(user)
            #model_obj = request.env[model].sudo()
            records = model_obj.search_read(domain=domain, fields=fields, limit=limit)
            result = {
                'status': 'success',
                'data': records
            }
            
            return self._json_response(result)
        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })

    @http.route('/api/v1/knowledge/search', auth='none', type='http', methods=['POST'], csrf=False)
    def search_knowledge(self, **kwargs):
        """知识库全文搜索接口
        
        Args:
            keywords (list): 关键词列表,例如 ["关键词1", "关键词2"]
        
        Returns:
            dict: 包含搜索结果的字典
            {
                'status': 'success',
                'data': [{
                    'id': 1, 
                    'name': '文档标题',
                    'content': '文档内容'
                }]
            }
        """
        user = self._verify_api_key()
        if not user:
            return self._json_response({
                'status': 'error',
                'message': 'Invalid API key'
            })

        try:
            # 从请求体中获取关键词列表
            try:
                body = json.loads(request.httprequest.data.decode())
                keywords = body.get('keywords', {})
                
            except json.JSONDecodeError:
                return self._json_response({
                    'status': 'error',
                    'message': '无效的JSON数据'
                })

            
            if not keywords:
                return self._json_response({
                    'status': 'error',
                    'message': '请提供搜索关键词'
                })
            
            # 如果keywords中包含空字符串,则按空字符串进行分割
            if '' in keywords:
                keywords = [k for k in keywords if k != '']
            
            # 删除关键字中含有的odoo关键字
            keywords = [k for k in keywords if not k.startswith('odoo.')]

            # 构建搜索域
            domain = ['|'] * (len(keywords) - 1)
            for keyword in keywords:
                domain.extend([
                    '|',
                    ('name', 'ilike', keyword),
                    ('content', 'ilike', keyword)
                ])

            # 执行搜索
            documents = request.env['document.page'].with_user(user).search_read(
                domain=domain,
                fields=['id', 'name', 'content'],
                limit=20
            )

            return self._json_response({
                'status': 'success',
                'data': documents
            })

        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })
        

    @http.route('/api/v1/object/create', auth='none', type='http', methods=['POST'], csrf=False)
    def create_object(self, **kwargs):
        """创建业务对象记录
        
        Args:
            model (str): 模型名称,例如 res.partner
            values (dict): 记录字段值,例如
                {
                    "name": "小海智能",
                    "email": "xiaohai@xiaohai.com", 
                    "phone": "12345678901"
                }
                
        Returns:
            dict: 包含创建结果的字典
            {
                'status': 'success',
                'data': {
                    'id': 1,
                    'name': '小海智能'
                }
            }
        """
        try:
            # 验证API密钥
            user = self._verify_api_key()
            if not user:
                return self._json_response({
                    'status': 'error',
                    'message': 'Invalid API key'
                })

            # 解析请求数据
            try:
                body = json.loads(request.httprequest.data.decode())
            except json.JSONDecodeError:
                return self._json_response({
                    'status': 'error',
                    'message': '无效的JSON数据'
                })
            
            # 获取并验证必要参数
            model = body.get('model')
            values = body.get('values', {})
            
            if not model:
                return self._json_response({
                    'status': 'error',
                    'message': '请提供模型名称'
                })
                
            if not values:
                return self._json_response({
                    'status': 'error', 
                    'message': '请提供记录值'
                })
            
            # 检查模型是否存在
            if not request.env['ir.model'].sudo().search([('model', '=', model)]):
                return self._json_response({
                    'status': 'error',
                    'message': f'模型 {model} 不存在'
                })
            
            # 创建记录
            try:
                record = request.env[model].with_user(user).create(values)
                
                # 构建URL参数
                params = {
                    'model': model,
                    'id': record.id,
                    'process_type': 'edit'
                }
                
                # 构建完整URL
                base_url = request.httprequest.host_url.rstrip('/')
                url = f"{base_url}/web/action?" + urllib.parse.urlencode(params)
                
                return self._json_response({
                    'status': 'success',
                    'data': {
                        'id': record.id,
                        'name': record.name if hasattr(record, 'name') else str(record.id),
                        'url': url
                    }
                })
            except Exception as e:
                return self._json_response({
                    'status': 'error',
                    'message': f'创建记录失败: {str(e)}'
                })
                
        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })


    @http.route('/api/v1/object/update', auth='none', type='http', methods=['POST'], csrf=False)
    def update_object(self, **kwargs):
        """更新业务对象
        
        Args:
            model (str): 模型名称，例如: 'res.partner'
            id (int): 记录ID，例如: 1
            values (dict): 需要更新的字段值，例如: {'name': '张三', 'phone': '13800138000'}
            
        Returns:
            dict: 更新结果
            {
                'status': 'success',
                'data': {
                    'id': 1,
                    'name': '更新后的名称'
                }
            }
            
        使用场景:
            当需要通过API更新业务伙伴信息时:
            {
                "model": "res.partner",
                "id": 1,
                "values": {
                    "name": "张三",
                    "phone": "13800138000",
                    "email": "zhangsan@example.com"
                }
            }
        """
        try:
            # 验证API密钥
            user = self._verify_api_key()
            if not user:
                return self._json_response({
                    'status': 'error',
                    'message': 'Invalid API key'
                })

            # 解析请求数据
            try:
                body = json.loads(request.httprequest.data.decode())
            except json.JSONDecodeError:
                return self._json_response({
                    'status': 'error',
                    'message': '无效的JSON数据'
                })
            
            # 获取并验证必要参数
            model = body.get('model')
            record_id = body.get('id')
            values = body.get('values', {})
            
            if not model:
                return self._json_response({
                    'status': 'error',
                    'message': '请提供模型名称'
                })
                
            if not record_id:
                return self._json_response({
                    'status': 'error',
                    'message': '请提供记录ID'
                })
                
            if not values:
                return self._json_response({
                    'status': 'error',
                    'message': '请提供需要更新的值'
                })
            
            # 检查模型是否存在
            if not request.env['ir.model'].sudo().search([('model', '=', model)]):
                return self._json_response({
                    'status': 'error',
                    'message': f'模型 {model} 不存在'
                })
            
            # 检查记录是否存在
            record = request.env[model].sudo().browse(record_id)
            if not record.exists():
                return self._json_response({
                    'status': 'error',
                    'message': f'ID为 {record_id} 的记录不存在或无权限访问'
                })
            
            # 更新记录
            try:
                record.write(values)
                
                # 构建URL参数
                params = {
                    'model': model,
                    'id': record.id,
                    'process_type': 'edit'
                }
                
                # 构建完整URL
                base_url = request.httprequest.host_url.rstrip('/')
                url = f"{base_url}/web/action?" + urllib.parse.urlencode(params)
                
                return self._json_response({
                    'status': 'success',
                    'data': {
                        'id': record.id,
                        'name': record.name if hasattr(record, 'name') else str(record.id),
                        'url': url
                    }
                })
            except Exception as e:
                return self._json_response({
                    'status': 'error',
                    'message': f'更新记录失败: {str(e)}'
                })
                
        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })

    @http.route('/api/v1/object/link', auth='none', type='http', methods=['POST'], csrf=False)
    def get_object_link(self, **kwargs):
        """获取对象链接
        
        Args:
            model (str): 模型名称
            id (int): 记录ID（可选，编辑时需要）
            process_type (str): 操作类型
                - 'new': 新建记录
                - 'edit': 编辑记录
            context (dict): 上下文参数
                {
                    "default_name": "小海智能",
                    "default_email": "xiaohai@xiaohai.com",
                    "default_phone": "12345678901",
                    "default_mobile": "12345678901",
                }
                
        Returns:
            dict: 包含对象链接的字典
            {
                'status': 'success',
                'data': {
                    'url': 'http://localhost:8069/web/action?model=res.partner&id=1&process_type=edit&context={...}'
                }
            }
        """
        try:
            # 验证API密钥
            user = self._verify_api_key()
            if not user:
                return self._json_response({
                    'status': 'error',
                    'message': 'Invalid API key'
                })

            # 解析请求数据
            try:
                body = json.loads(request.httprequest.data.decode())
            except json.JSONDecodeError:
                return self._json_response({
                    'status': 'error',
                    'message': '无效的JSON数据'
                })
            
            # 获取并验证必要参数
            model = body.get('model')
            process_type = body.get('process_type', 'edit')
            record_id = body.get('id')
            
            if not model:
                return self._json_response({
                    'status': 'error', 
                    'message': '缺少必填参数: model'
                })
            
            # 验证process_type
            if process_type not in ['new', 'edit']:
                return self._json_response({
                    'status': 'error',
                    'message': 'process_type必须是new或edit'
                })
                
            # 在编辑模式下验证record_id
            if process_type == 'edit' and not record_id:
                return self._json_response({
                    'status': 'error',
                    'message': '编辑模式下必须提供record_id'
                })
                
            if not self._is_model_allowed(model, user):
                return self._json_response({
                    'status': 'error',
                    'message': f'Access to model {model} is not allowed'
                })

            # 验证记录访问权限
            if record_id:
                try:
                    record = request.env[model].sudo().browse(record_id).exists()
                    if not record:
                        return self._json_response({
                            'status': 'error',
                            'message': f'Record {record_id} not found in {model}'
                        })
                except Exception as e:
                    return self._json_response({
                        'status': 'error',
                        'message': f'Error accessing record: {str(e)}'
                    })

            # 构建URL参数
            params = {
                'model': model,
                'process_type': process_type
            }
            
            # 如果是编辑模式且提供了记录ID，添加到参数中
            if record_id:
                params['id'] = record_id
            
            # 如果有上下文，添加到参数中
            # context = body.get('context', {})
            # if context:
            #     params['context'] = json.dumps(context)
            
            # 构建完整URL
            base_url = request.httprequest.host_url.rstrip('/')
            url = f"{base_url}/web/action?" + urllib.parse.urlencode(params)
            
            return self._json_response({
                'status': 'success',
                'data': {
                    'url': url
                }
            })
            
        except Exception as e:
            _logger.error("获取对象链接失败: %s", str(e))
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })

    @http.route('/web/action', auth='user', type='http', methods=['GET'], csrf=False)
    def get_object_action(self, **kwargs):
        """处理对象动作请求
        
        Args:
            model (str): 模型名称
            id (int): 记录ID（可选）
            process_type (str): 操作类型 (new/edit)
            context (str): JSON格式的上下文数据
            
        Returns:
            Response: 重定向到Odoo Web客户端
        """
        try:
            # 获取参数
            model = kwargs.get('model')
            record_id = kwargs.get('id')
            process_type = kwargs.get('process_type', 'edit')
            # context_str = kwargs.get('context')
            
            if not model:
                return request.redirect('/web#error=no_model')
            
            # 解析上下文
            # try:
            #     context = json.loads(context_str) if context_str else {}
            # except:
            #     context = {}
            
            # 查找动作
            action_domain = [
                ('res_model', '=', model),
                ('type', '=', 'ir.actions.act_window'),
            ]
            
            # 根据process_type调整查询条件
            if process_type == 'new':
                action_domain.append(('target', '=', 'new'))
            
            # 查找动作
            action = request.env['ir.actions.act_window'].sudo().search(action_domain, order='id desc', limit=1)
            
            if not action:
                # 如果没有找到特定类型的动作，尝试查找任意类型的动作
                action_domain = [
                    ('res_model', '=', model),
                    ('type', '=', 'ir.actions.act_window'),
                ]
                action = request.env['ir.actions.act_window'].sudo().search(action_domain, order='id desc', limit=1)
            
            if not action:
                # 如果仍然没有找到动作，尝试获取模型的默认动作
                try:
                    action = request.env[model].sudo().get_formview_action()
                except Exception:
                    pass
            
            if not action:
                return request.redirect('/web#error=no_action')
            
            # 构建动作URL
            url_params = []
            
            # 添加动作ID
            url_params.append(f"action={action.id}")
            
            # 如果是编辑模式且提供了记录ID，添加到参数中
            if process_type == 'edit' and record_id:
                url_params.append(f"id={record_id}")
                
            # 如果是新建模式，添加model参数
            if process_type == 'new':
                url_params.append(f"model={model}")
            
            # 如果有上下文，添加到参数中
            # if context:
            #     url_params.append(f"context={urllib.parse.quote(json.dumps(context))}")
            
            # 重定向到Web客户端
            return request.redirect('/web#' + '&'.join(url_params))
            
        except Exception as e:
            _logger.error("处理对象动作请求失败: %s", str(e))
            return request.redirect('/web#error=action_failed')
        

    @http.route('/api/v1/qcc/business_license', auth='none', type='http', methods=['POST'], csrf=False)
    def get_business_license(self, **kwargs):
        """查询企业营业执照信息
        实时查询企业工商照面信息，返回企业名称、企业类型、注册资本、统一社会信用代码、经营范围、营业期限、上市状态等信息。

        Args:
            company_name (str): 企业名称

        Returns:
            dict: 企业营业执照信息
            {
                'status': 'success',
                'data': {
                    'company_name': '小海智能',
                    'company_type': '有限责任公司',
                    'registered_capital': '1000000',
                    'social_credit_code': '123456789012345678',
                    'business_scope': '软件开发',
                    'business_term': '2020-01-01至2025-01-01',
                    'business_status': '正常',
                    'business_address': '北京市海淀区',
                    'business_phone': '12345678901',
                    'business_email': 'xiaohai@xiaohai.com',
                }
            }
        """

        _logger.info("查询企业营业执照信息")
        
        user = self._verify_api_key()

        if not user:
            return self._json_response({
                'status': 'error',
                'message': 'Invalid API key'
            })

        try:
            # 从请求体中获取关键词列表
            try:
                body = json.loads(request.httprequest.data.decode())
                
            except json.JSONDecodeError:
                return self._json_response({
                    'status': 'error',
                    'message': '无效的JSON数据'
                })

            # 获取企业名称
            company_name = body.get('company_name', '')
            
            # 验证企业名称是否为空
            if not company_name:
                return self._json_response({
                    'status': 'error',
                    'message': '企业名称不能为空'
                })

            # 查询企业营业执照信息
            data = request.env['mcp.qcc'].sudo().query_business_license(company_name)
            _logger.info(f"查询企业营业执照信息: {data}")
            if data['status'] == 'success': # 查询成功
                return self._json_response({
                    'status': 'success',
                    'data': data['data']    
                })
            else:
                return self._json_response({
                    'status': 'error',
                    'message': data['message']
                })
        except Exception as e:
            return self._json_response({
                'status': 'error',
                'message': str(e)
            })