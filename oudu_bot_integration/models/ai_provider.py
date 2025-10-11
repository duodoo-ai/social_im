from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, Optional, List
from openai import OpenAI
import logging
import json

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

    def test_connection(self) -> bool:
        """Test connection to AI provider."""
        test_time = fields.Datetime.now()

        try:
            test_messages = [{
                "role": "user",
                "content": "Connection test - reply with 'OK'"
            }]

            model = self.default_model or "deepseek-chat"
            result = self.get_chat_completion(test_messages, model=model, max_tokens=5)

            # Check if we got a valid response
            if result.get('choices') and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                success_message = f"✅ 连接测试成功\n时间: {test_time}\n模型: {model}\n响应: '{content.strip()}'"
                _logger.info(f"Connection test successful for {self.name}. Response: {content}")

                self.write({
                    'last_test_result': True,
                    'last_test_message': success_message,
                    'last_used': test_time
                })
                return True
            else:
                error_message = f"❌ 连接测试失败\n时间: {test_time}\n原因: API响应中没有有效数据"
                _logger.error(f"Connection test failed for {self.name}: No choices in response")

                self.write({
                    'last_test_result': False,
                    'last_test_message': error_message
                })
                return False

        except Exception as e:
            error_message = f"❌ 连接测试失败\n时间: {test_time}\n原因: {str(e)}"
            _logger.error(f"Connection test failed for {self.name}: {str(e)}")

            self.write({
                'last_test_result': False,
                'last_test_message': error_message
            })
            return False

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