from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, Optional, List
from openai import OpenAI
import logging
import traceback
import json
from datetime import datetime

_logger = logging.getLogger(__name__)


class AIProvider(models.Model):
    _name = 'oudu.bot.provider'
    _description = 'AI Provider Configuration'
    _order = 'sequence, name'

    @api.model
    def init_provider_configs(self):
        """Initialize provider configurations after installation"""
        providers = self.search([])

        config_mapping = {
            'DEEPSEEK_R1': {
                'available_models': {
                    'deepseek-chat': {'name': 'DeepSeek Chat', 'context_length': 32768, 'supports_tools': True},
                    'deepseek-coder': {'name': 'DeepSeek Coder', 'context_length': 16384, 'supports_tools': True}
                },
                'headers_config': {
                    'Authorization': 'Bearer your_deepseek_api_key_here',
                    'Content-Type': 'application/json'
                },
                'model_config': {
                    'stream': False,
                    'top_p': 0.9,
                    'frequency_penalty': 0,
                    'presence_penalty': 0
                }
            },
            'DEMO_PROVIDER': {
                'available_models': {
                    'demo-model': {'name': 'Demo Model', 'context_length': 4000, 'supports_tools': True}
                },
                'headers_config': {
                    'Authorization': 'Bearer demo_api_key_12345',
                    'X-Demo-Mode': 'true'
                },
                'model_config': {
                    'demo_mode': True,
                    'echo_response': True
                }
            }
        }

        for provider in providers:
            config = config_mapping.get(provider.code, {})
            if config:
                provider.write(config)

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
    available_models = fields.Json(
        string='Available Models',
        default=lambda self: {},
        help="JSON configuration of available models and their capabilities"
    )
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
    rate_limit = fields.Integer(
        string='Rate Limit (requests/minute)',
        default=60,
        help="Maximum requests per minute"
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

    # Advanced Configuration
    model_config = fields.Json(
        string='Model Configuration',
        default=lambda self: {},
        help="Advanced model-specific configuration"
    )
    headers_config = fields.Json(
        string='Headers Configuration',
        default=lambda self: {},
        help="Custom headers for API requests"
    )
    request_config = fields.Json(
        string='Request Configuration',
        default=lambda self: {},
        help="Additional request parameters"
    )

    # Demo mode configuration
    demo_mode = fields.Boolean(
        string='Demo Mode',
        default=False,
        help="Enable demo mode for testing without real API calls"
    )
    demo_responses = fields.Json(
        string='Demo Responses',
        default=lambda self: {
            "chat_completion": {
                "id": "chatcmpl-demo-12345",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "demo-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a demo response from the AI provider. In a real implementation, this would be replaced with actual AI-generated content."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        },
        help="Predefined responses for demo mode"
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

    @api.constrains('max_tokens')
    def _check_max_tokens(self) -> None:
        """Validate max tokens value."""
        for record in self:
            if record.max_tokens < 1 or record.max_tokens > 32000:
                raise ValidationError("Max tokens must be between 1 and 32000")

    def _get_openai_client(self) -> OpenAI:
        """Get OpenAI client for the provider.

        Returns:
            OpenAI: Configured OpenAI client instance
        """
        client_kwargs = {
            'api_key': self.api_key,
            'base_url': self.base_url.rstrip('/'),
            'timeout': self.timeout,
            'max_retries': 2
        }

        return OpenAI(**client_kwargs)

    def _make_openai_request(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Dict[str, Any]:
        """Make API request using OpenAI client.

        Args:
            messages (List[Dict[str, str]]): Conversation messages
            model (str): Model to use
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: API response data

        Raises:
            ValidationError: When API request fails
        """
        # Demo mode response
        if self.demo_mode:
            _logger.info(f"Demo mode active for {self.name}, returning demo response")
            demo_response = self.demo_responses.get('chat_completion', {})
            demo_response['model'] = model
            return demo_response

        try:
            client = self._get_openai_client()

            # Prepare request parameters
            request_params = {
                'model': model,
                'messages': messages,
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'temperature': kwargs.get('temperature', self.temperature),
            }

            # Add optional parameters
            optional_params = ['top_p', 'frequency_penalty', 'presence_penalty', 'stop', 'stream']
            for param in optional_params:
                if param in kwargs:
                    request_params[param] = kwargs[param]

            # Merge with model-specific configuration
            if self.model_config:
                for key, value in self.model_config.items():
                    if key not in request_params:  # Don't override existing params
                        request_params[key] = value

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
            # 处理余额不足的特殊情况
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

    def _get_user_timezone(self):
        """获取用户时区"""
        # 从context获取时区，如果没有则使用用户配置的时区
        tz = self._context.get('tz')
        if not tz:
            # 获取当前用户的时区
            user = self.env.user
            tz = user.tz
        return tz or 'UTC'

    def _format_datetime_for_user(self, dt):
        """根据用户时区格式化时间"""
        try:
            tz = self._get_user_timezone()
            # 使用Odoo的时区处理功能
            if hasattr(fields.Datetime, 'context_timestamp'):
                # 将UTC时间转换为用户时区
                user_dt = fields.Datetime.context_timestamp(self, dt)
                return user_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                # 备用方案
                return dt.astimezone(pytz.timezone(tz)).strftime('%Y-%m-%d %H:%M:%S %Z')
        except Exception as e:
            _logger.warning(f"Failed to format datetime with timezone: {e}")
            # 如果时区处理失败，返回UTC时间
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')

    def test_connection(self) -> bool:
        """Test connection to AI provider.

        Returns:
            bool: True if connection test successful
        """
        test_time = fields.Datetime.now()

        try:
            test_messages = [{
                "role": "user",
                "content": "Connection test - reply with 'OK'"
            }]

            # Determine which model to use for testing
            if self.default_model:
                model = self.default_model
            elif self.available_models:
                model = list(self.available_models.keys())[0]
            else:
                model = "deepseek-chat"

            result = self.get_chat_completion(test_messages, model=model, max_tokens=5)

            # Check if we got a valid response
            if result.get('choices') and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                formatted_time = self._format_datetime_for_user(test_time)
                success_message = f"✅ 连接测试成功\n时间: {formatted_time}\n模型: {model}\n响应: '{content.strip()}'"
                _logger.info(f"Connection test successful for {self.name}. Response: {content}")

                self.write({
                    'last_test_result': True,
                    'last_test_message': success_message,
                    'last_used': test_time
                })
                return True
            else:
                formatted_time = self._format_datetime_for_user(test_time)
                error_message = f"❌ 连接测试失败\n时间: {formatted_time}\n原因: API响应中没有有效数据"
                _logger.error(f"Connection test failed for {self.name}: No choices in response")

                self.write({
                    'last_test_result': False,
                    'last_test_message': error_message
                })
                return False

        except ValidationError as e:
            # 专门处理余额不足的ValidationError
            error_str = str(e)
            formatted_time = self._format_datetime_for_user(test_time)
            if '余额不足' in error_str:
                error_message = f"❌ 连接测试失败\n时间: {formatted_time}\n原因: {error_str}"
            else:
                error_message = f"❌ 连接测试失败\n时间: {formatted_time}\n原因: {error_str}"

            _logger.error(f"Connection test failed for {self.name}: {error_str}")

            self.write({
                'last_test_result': False,
                'last_test_message': error_message
            })
            return False

        except Exception as e:
            # 简化错误信息，避免显示完整的堆栈跟踪
            formatted_time = self._format_datetime_for_user(test_time)
            error_message = f"❌ 连接测试失败\n时间: {formatted_time}\n原因: {str(e)}"

            _logger.error(f"Connection test failed for {self.name}: {str(e)}")

            self.write({
                'last_test_result': False,
                'last_test_message': error_message
            })
            return False

    def get_chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None, **kwargs) -> Dict[
        str, Any]:
        """Get chat completion from AI provider.

        Args:
            messages (List[Dict[str, str]]): Conversation messages
            model (Optional[str]): Specific model to use
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: Completion response
        """
        # Determine which model to use
        actual_model = model or self.default_model
        if not actual_model and self.available_models:
            actual_model = list(self.available_models.keys())[0]
        elif not actual_model:
            actual_model = "deepseek-chat"

        return self._make_openai_request(messages, actual_model, **kwargs)

    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using a simple prompt (similar to deepseek_api.py).

        Args:
            prompt (str): The input prompt
            model (Optional[str]): Specific model to use
            **kwargs: Additional parameters

        Returns:
            str: Generated text content

        Raises:
            ValidationError: When generation fails
        """
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
        """Get active provider by type.

        Args:
            provider_type (str): Type of provider to find

        Returns:
            Optional[AIProvider]: Active provider or None
        """
        return self.search([
            ('provider_type', '=', provider_type),
            ('is_active', '=', True)
        ], limit=1)

    @api.model
    def get_provider_by_code(self, code: str) -> Optional['AIProvider']:
        """Get provider by code.

        Args:
            code (str): Provider code to find

        Returns:
            Optional[AIProvider]: Provider instance or None
        """
        return self.search([('code', '=', code), ('is_active', '=', True)], limit=1)