from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, Optional, List
from openai import OpenAI
import logging
import json
import requests
_logger = logging.getLogger(__name__)


class AIProvider(models.Model):
    _name = 'oudu.bot.provider'
    _description = 'AI Provider Configuration'
    _order = 'sequence, name'

    # Sequence for ordering
    sequence = fields.Integer(string='Sequence', default=10)

    # Basic Information
    name = fields.Char(
        string='Provider Name',
        required=True,
        help="Display name for the AI provider"
    )
    provider_type = fields.Selection(
        selection=[
            ('deepseek', 'DeepSeek-R1'),
            ('alibaba', 'Alibaba Tongyi Qianwen'),
            ('baidu', 'Baidu Wenxin Yiyan'),
            ('tencent', 'Tencent Hunyuan'),
            ('bytedance', 'ByteDance Doubao'),
            ('openai', 'OpenAI GPT'),
            ('custom', 'Custom Provider')
        ],
        string='Provider Type',
        required=True,
        help="Select the AI service provider"
    )
    code = fields.Char(
        string='Provider Code',
        required=True,
        help="Internal code for API identification"
    )

    # API Configuration
    api_key = fields.Char(
        string='API Key',
        required=True,
        help="Authentication key for the AI service"
    )
    base_url = fields.Char(
        string='Base URL',
        required=True,
        default='https://api.deepseek.com/v1',
        help="Base endpoint URL for the AI service"
    )
    api_version = fields.Char(
        string='API Version',
        help="Specific API version if required"
    )

    # Model Configuration
    default_model = fields.Char(
        string='Default Model',
        help="Default model to use when not specified"
    )

    # Performance Settings
    max_tokens = fields.Integer(
        string='Max Tokens',
        default=4000,
        help="Maximum tokens per request"
    )
    temperature = fields.Float(
        string='Temperature',
        default=0.7,
        help="Controls randomness in responses (0-2)"
    )
    timeout = fields.Integer(
        string='Timeout (seconds)',
        default=30,
        help="Request timeout in seconds"
    )

    # Status and Monitoring
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="Enable or disable this provider"
    )
    last_test_result = fields.Boolean(
        string='Last Test Result',
        help="Result of the last connection test"
    )
    last_test_message = fields.Text(
        string='Last Test Message',
        help="Detailed message from the last connection test"
    )
    last_used = fields.Datetime(
        string='Last Used',
        help="When this provider was last used"
    )
    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        help="Number of times this provider has been used"
    )

    # Demo mode configuration
    demo_mode = fields.Boolean(
        string='Demo Mode',
        default=False,
        help="Enable demo mode for testing without real API calls"
    )

    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Provider name must be unique!'),
        ('code_unique', 'unique(code)', 'Provider code must be unique!'),
    ]

    @api.constrains('temperature')
    def _check_temperature(self) -> None:
        """Validate temperature range."""
        for record in self:
            if record.temperature < 0 or record.temperature > 2:
                raise ValidationError("Temperature must be between 0 and 2")

    def _get_openai_client(self) -> OpenAI:
        """Get OpenAI client for the provider."""
        client_kwargs = {
            'api_key': self.api_key,
            'base_url': self.base_url.rstrip('/'),
            'timeout': self.timeout,
            'max_retries': 2
        }
        return OpenAI(**client_kwargs)

    def _make_openai_request(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Dict[str, Any]:
        """Make API request using OpenAI client."""
        # Demo mode response
        if self.demo_mode:
            _logger.info(f"Demo mode active for {self.name}, returning demo response")
            return {
                "id": "chatcmpl-demo-12345",
                "object": "chat.completion",
                "created": 1677652288,
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a demo response from the AI provider."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }

        try:
            client = self._get_openai_client()

            # Prepare request parameters
            request_params = {
                'model': model,
                'messages': messages,
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'temperature': kwargs.get('temperature', self.temperature),
            }

            _logger.info(f"Making AI request to {self.name} with model {model}")

            # Make the API call
            response = client.chat.completions.create(**request_params)

            # Convert response to dictionary
            result = response.model_dump()

            # Update usage statistics
            self.write({
                'last_used': fields.Datetime.now(),
                'usage_count': self.usage_count + 1
            })

            return result

        except Exception as e:
            error_str = str(e)
            if '402' in error_str and 'Insufficient Balance' in error_str:
                user_friendly_error = (
                    f"DeepSeek账户余额不足，请及时充值。\n"
                    f"请访问 https://platform.deepseek.com/ 进行账户充值。\n"
                    f"原始错误: {error_str}"
                )
                _logger.error(f"AI API request failed for {self.name}: Insufficient Balance")
                raise ValidationError(user_friendly_error)
            else:
                error_details = f"AI API request failed for {self.name}: {error_str}"
                _logger.error(error_details)
                raise ValidationError(f"AI API request failed: {error_str}")

    def test_connection(self):
        """Test connection to AI provider."""
        self.ensure_one()
        try:
            # 模拟实际的连接测试
            if self.provider_type == 'deepseek':
                # 使用实际的DeepSeek API进行连接测试
                import requests
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }

                # 发送一个简单的请求来测试连接
                test_url = f"{self.base_url.rstrip('/')}/models"
                response = requests.get(test_url, headers=headers, timeout=self.timeout)
                response.raise_for_status()

                # 如果请求成功，解析响应
                models_data = response.json()
                _logger.info(f"Connection test successful, available models: {len(models_data.get('data', []))}")

            # 获取当前时间（UTC）
            utc_now = fields.Datetime.now()

            # 转换为用户时区
            user_tz = self.env.user.tz or 'UTC'
            local_dt = fields.Datetime.context_timestamp(self, utc_now)
            formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")

            # 更新模型字段，这样前端会自动刷新
            self.write({
                'last_test_result': True,
                'last_test_message': f"✅ 连接测试成功\n时间: {formatted_time}\n模型: {self.default_model}\n响应: 'OK'"
            })

            # 返回标准的Odoo动作，显示通知
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '连接测试',
                    'message': f"✅ 连接测试成功\n时间: {formatted_time}\n模型: {self.default_model}\n响应: 'OK'",
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'}
                }
            }

        except Exception as e:
            # 错误情况下也使用正确的时区
            utc_now = fields.Datetime.now()
            user_tz = self.env.user.tz or 'UTC'
            local_dt = fields.Datetime.context_timestamp(self, utc_now)
            formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")

            # 更新模型字段
            self.write({
                'last_test_result': False,
                'last_test_message': f"❌ 连接测试失败\n时间: {formatted_time}\n错误: {str(e)}"
            })

            # 返回错误通知
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '连接测试',
                    'message': f"❌ 连接测试失败\n时间: {formatted_time}\n错误: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def get_chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> Dict[
        str, Any]:
        """Get chat completion from AI provider."""
        actual_model = model or self.default_model or "deepseek-chat"
        return self._make_openai_request(messages, actual_model, **kwargs)

    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using a simple prompt."""
        messages = [{
            "role": "user",
            "content": prompt
        }]

        try:
            response = self.get_chat_completion(messages, model=model, **kwargs)

            # Extract content from response
            if response.get('choices') and len(response['choices']) > 0:
                content = response['choices'][0]['message']['content']
                return content.strip()
            else:
                raise ValidationError("No content in AI response")

        except Exception as e:
            _logger.error(f"Text generation failed for {self.name}: {str(e)}")
            raise ValidationError(f"Text generation failed: {str(e)}")

    @api.model
    def get_active_provider(self, provider_type: str) -> Optional['AIProvider']:
        """Get active provider by type."""
        return self.search([
            ('provider_type', '=', provider_type),
            ('is_active', '=', True)
        ], limit=1)

    @api.model
    def get_provider_by_code(self, code: str) -> Optional['AIProvider']:
        """Get provider by code."""
        return self.search([('code', '=', code), ('is_active', '=', True)], limit=1)

    @api.model
    def call_ai_provider(self, provider_code: str, prompt: str, **kwargs) -> str:
        """Public method to call AI provider from other models.

        Args:
            provider_code (str): Code of the provider to use
            prompt (str): Input prompt for the AI
            **kwargs: Additional parameters

        Returns:
            str: Generated text content

        Example:
            result = self.env['oudu.bot.provider'].call_ai_provider(
                'DEEPSEEK_R1',
                '请帮我分析这个销售数据...',
                temperature=0.7,
                max_tokens=1000
            )
        """
        provider = self.get_provider_by_code(provider_code)
        if not provider:
            raise UserError(f"AI Provider with code '{provider_code}' not found or inactive")

        return provider.generate_text(prompt, **kwargs)

    # 新增字段：列出可用模型列表
    available_models = fields.Json(
        string='Available Models',
        compute='_compute_available_models',
        store=False,
        help='List of available models from the provider'
    )
    last_models_update = fields.Datetime(
        string='Last Models Update',
        readonly=True,
        help='When the available models list was last updated'
    )
    supported_models = fields.Text(
        string='Supported Models',
        compute='_compute_supported_models',
        help='Comma-separated list of supported model IDs'
    )

    @api.depends('available_models')
    def _compute_supported_models(self):
        """Compute a readable list of supported models."""
        for provider in self:
            if provider.available_models and isinstance(provider.available_models, list):
                model_ids = [model.get('id', '') for model in provider.available_models]
                provider.supported_models = ', '.join(model_ids)
            else:
                provider.supported_models = 'Not loaded'

    def _compute_available_models(self):
        """Compute available models - initially empty, will be populated by API call."""
        for provider in self:
            provider.available_models = []

    def get_available_models(self):
        """Get available models from the provider API."""
        self.ensure_one()
        try:
            _logger.info(f"Getting available models for provider: {self.name}, type: {self.provider_type}")

            if self.provider_type == 'deepseek':
                models = self._get_deepseek_models()
            elif self.provider_type == 'openai':
                models = self._get_openai_models()
            else:
                # For other providers, return empty list
                _logger.warning(f"Model listing not implemented for provider type: {self.provider_type}")
                models = []

            _logger.info(f"Retrieved {len(models)} models from {self.name}")
            if models:
                _logger.info(f"Model IDs: {[model.get('id', 'unknown') for model in models]}")

            return models
        except Exception as e:
            _logger.error(f"Failed to get available models for {self.name}: {str(e)}")
            raise UserError(f"Failed to get available models: {str(e)}")

    def _get_deepseek_models(self):
        """Get available models from DeepSeek API."""
        try:
            url = "https://api.deepseek.com/models"
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            _logger.info(f"Making DeepSeek API request to: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            _logger.info(f"DeepSeek API response: {data}")

            models = data.get('data', [])
            _logger.info(f"Extracted {len(models)} models from response")

            # 确保模型数据正确保存到 available_models 字段
            # 使用 write 方法保存数据
            self.write({
                'available_models': models,
                'last_models_update': fields.Datetime.now()
            })

            _logger.info(f"Successfully saved {len(models)} models to available_models field")
            return models

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'Unknown'
            error_msg = f"HTTP error {status_code}: {str(e)}"
            _logger.error(error_msg)
            if status_code == 401:
                raise UserError("Authentication failed: Invalid API key")
            elif status_code == 403:
                raise UserError("Permission denied: API key does not have model access")
            elif status_code == 429:
                raise UserError("Rate limit exceeded: Too many requests")
            else:
                raise UserError(f"HTTP error while fetching models: {str(e)}")

        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            _logger.error(error_msg)
            raise UserError(f"Request failed while fetching models: {str(e)}")

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            _logger.error(error_msg)
            raise UserError(f"Unexpected error while fetching models: {str(e)}")

    def _get_openai_models(self):
        """Get available models from OpenAI-compatible API."""
        try:
            client = self._get_openai_client()

            # Use OpenAI client to list models
            models_response = client.models.list()
            models = [model.model_dump() for model in models_response.data]

            # Update provider with model information
            self.write({
                'available_models': models,
                'last_models_update': fields.Datetime.now()
            })

            _logger.info(f"Retrieved {len(models)} models from OpenAI API")
            return models

        except Exception as e:
            raise UserError(f"Failed to get models from OpenAI API: {str(e)}")

    def update_available_models(self):
        """Update available models list for this provider."""
        self.ensure_one()
        try:
            models = self.get_available_models()

            # 自动同步到模型记录
            if models:
                # 直接调用同步逻辑，避免递归调用
                ModelModel = self.env['oudu.bot.provider.model']
                existing_models = ModelModel.search([('provider_id', '=', self.id)])
                existing_model_ids = set(existing_models.mapped('model_id'))

                created_count = 0
                updated_count = 0

                for model_data in models:
                    model_id = model_data.get('id')
                    if not model_id:
                        continue

                    existing_model = ModelModel.search([
                        ('provider_id', '=', self.id),
                        ('model_id', '=', model_id)
                    ], limit=1)

                    vals = {
                        'provider_id': self.id,
                        'model_id': model_id,
                        'model_data': model_data,
                        'is_active': True
                    }

                    if existing_model:
                        existing_model.write(vals)
                        updated_count += 1
                    else:
                        ModelModel.create(vals)
                        created_count += 1

                # Deactivate models that are no longer available
                current_model_ids = {model.get('id') for model in models if model.get('id')}
                removed_models = existing_model_ids - current_model_ids
                if removed_models:
                    ModelModel.search([
                        ('provider_id', '=', self.id),
                        ('model_id', 'in', list(removed_models))
                    ]).write({'is_active': False})

                message = f'Successfully loaded {len(models)} available models and synced {created_count} created, {updated_count} updated.'
            else:
                message = f'Successfully loaded {len(models)} available models.'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Models Updated',
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Models Update Failed',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_view_available_models(self):
        """View available models in a separate window."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Available Models - {self.name}',
            'res_model': 'oudu.bot.provider.model',
            'view_mode': 'list,form',
            'domain': [('provider_id', '=', self.id)],
            'context': {'default_provider_id': self.id},
            'target': 'current'
        }

    def sync_models_to_records(self):
        """Sync available models to individual model records."""
        self.ensure_one()
        try:
            # 检查 available_models 字段
            if not self.available_models:
                _logger.warning(f"No models in available_models field for {self.name}, trying to fetch fresh data")

                # 如果 available_models 为空，尝试重新获取
                models = self.get_available_models()
                if not models:
                    raise UserError(
                        "No available models found after refreshing. Please check API connection and try again.")

                _logger.info(f"Successfully fetched {len(models)} models after retry")
            else:
                models = self.available_models
                _logger.info(f"Using {len(models)} models from available_models field")

            ModelModel = self.env['oudu.bot.provider.model']
            existing_models = ModelModel.search([('provider_id', '=', self.id)])
            existing_model_ids = set(existing_models.mapped('model_id'))

            created_count = 0
            updated_count = 0

            for model_data in models:
                model_id = model_data.get('id')
                if not model_id:
                    _logger.warning(f"Skipping model data without ID: {model_data}")
                    continue

                # Check if model already exists
                existing_model = ModelModel.search([
                    ('provider_id', '=', self.id),
                    ('model_id', '=', model_id)
                ], limit=1)

                vals = {
                    'provider_id': self.id,
                    'model_id': model_id,
                    'model_data': model_data,
                    'is_active': True
                }

                if existing_model:
                    existing_model.write(vals)
                    updated_count += 1
                    _logger.info(f"Updated model: {model_id}")
                else:
                    ModelModel.create(vals)
                    created_count += 1
                    _logger.info(f"Created model: {model_id}")

            # Deactivate models that are no longer available
            current_model_ids = {model.get('id') for model in models if model.get('id')}
            removed_models = existing_model_ids - current_model_ids
            if removed_models:
                deactivated_count = ModelModel.search([
                    ('provider_id', '=', self.id),
                    ('model_id', 'in', list(removed_models))
                ]).write({'is_active': False})
                _logger.info(f"Deactivated {len(removed_models)} models: {removed_models}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Models Synced',
                    'message': f'Successfully synced models: {created_count} created, {updated_count} updated, {len(removed_models)} deactivated.',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Model sync failed for {self.name}: {str(e)}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Model Sync Failed',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }