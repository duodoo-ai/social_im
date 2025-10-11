from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class AIProviderBalance(models.Model):
    _name = 'oudu.bot.provider.balance'
    _description = 'AI Provider Balance Monitoring'
    _order = 'check_date desc'

    # Basic Information
    provider_id = fields.Many2one(
        'oudu.bot.provider',
        string='AI Provider',
        required=True,
        ondelete='cascade'
    )
    provider_name = fields.Char(
        string='Provider Name',
        related='provider_id.name',
        store=True
    )
    provider_code = fields.Char(
        string='Provider Code',
        related='provider_id.code',
        store=True
    )

    # Balance Information
    balance = fields.Float(
        string='Balance',
        help='Current balance in the provider account'
    )
    currency = fields.Char(
        string='Currency',
        default='CNY',
        help='Currency code (CNY, USD, etc.)'
    )
    balance_status = fields.Selection([
        ('sufficient', 'Sufficient'),
        ('low', 'Low Balance'),
        ('insufficient', 'Insufficient'),
        ('unknown', 'Unknown')
    ], string='Balance Status', default='unknown')

    # Monitoring Information
    check_date = fields.Datetime(
        string='Check Date',
        default=fields.Datetime.now,
        required=True
    )
    is_success = fields.Boolean(
        string='Check Successful',
        help='Whether the balance check was successful'
    )
    error_message = fields.Text(
        string='Error Message',
        help='Error message if balance check failed'
    )

    # Threshold Settings
    low_balance_threshold = fields.Float(
        string='Low Balance Threshold',
        default=10.0,
        help='Threshold for low balance warning'
    )
    critical_balance_threshold = fields.Float(
        string='Critical Balance Threshold',
        default=1.0,
        help='Threshold for critical balance warning'
    )

    _sql_constraints = [
        ('balance_positive', 'CHECK(balance >= 0)', 'Balance must be positive or zero'),
    ]

    @api.model
    def check_provider_balance(self, provider):
        """Check balance for a specific provider."""
        try:
            if provider.provider_type == 'deepseek':
                return self._check_deepseek_balance(provider)
            elif provider.provider_type == 'openai':
                return self._check_openai_balance(provider)
            else:
                # For other providers, we don't have balance API
                return self._create_unknown_balance_record(provider)
        except Exception as e:
            _logger.error(f"Balance check failed for {provider.name}: {str(e)}")
            return self._create_error_balance_record(provider, str(e))

    def _check_deepseek_balance(self, provider):
        """Check DeepSeek provider balance according to actual API response format."""
        try:
            # 根据官方文档，正确的接口URL
            url = "https://api.deepseek.com/user/balance"
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {provider.api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            _logger.info(f"DeepSeek API response: {data}")

            # 根据实际API响应格式解析
            # 实际响应格式:
            # {
            #   "is_available": true,
            #   "balance_infos": [
            #     {
            #       "currency": "CNY",
            #       "total_balance": "110.00",
            #       "granted_balance": "10.00",
            #       "topped_up_balance": "100.00"
            #     }
            #   ]
            # }

            if not data.get('is_available', False):
                error_msg = "Balance service is not available"
                _logger.error(f"DeepSeek balance service not available: {data}")
                return self._create_error_balance_record(provider, error_msg)

            balance_infos = data.get('balance_infos', [])
            if not balance_infos:
                error_msg = "No balance information found in response"
                _logger.error(f"No balance info in response: {data}")
                return self._create_error_balance_record(provider, error_msg)

            # 获取第一个余额信息（通常只有一个）
            balance_info = balance_infos[0]
            total_balance_str = balance_info.get('total_balance', '0')
            currency = balance_info.get('currency', 'CNY')
            granted_balance_str = balance_info.get('granted_balance', '0')
            topped_up_balance_str = balance_info.get('topped_up_balance', '0')

            # 详细的调试信息
            _logger.info(f"Raw total_balance from API: {total_balance_str}, type: {type(total_balance_str)}")
            _logger.info(
                f"Provider low threshold: {provider.low_balance_threshold}, type: {type(provider.low_balance_threshold)}")
            _logger.info(
                f"Provider critical threshold: {provider.critical_balance_threshold}, type: {type(provider.critical_balance_threshold)}")

            # 确保余额是浮点数类型
            try:
                total_balance = float(total_balance_str)
                granted_balance = float(granted_balance_str)
                topped_up_balance = float(topped_up_balance_str)
            except (TypeError, ValueError) as e:
                _logger.error(
                    f"Failed to convert balance values to float: total={total_balance_str}, granted={granted_balance_str}, topped_up={topped_up_balance_str}, error: {str(e)}")
                total_balance = 0.0
                granted_balance = 0.0
                topped_up_balance = 0.0

            # 确保阈值也是浮点数类型
            try:
                low_threshold = float(provider.low_balance_threshold)
                critical_threshold = float(provider.critical_balance_threshold)
            except (TypeError, ValueError) as e:
                _logger.error(f"Failed to convert thresholds to float: {e}")
                low_threshold = 10.0
                critical_threshold = 1.0

            _logger.info(
                f"After conversion - total_balance: {total_balance} (type: {type(total_balance)}), low_threshold: {low_threshold} (type: {type(low_threshold)}), critical_threshold: {critical_threshold} (type: {type(critical_threshold)})")

            # Determine balance status using provider's thresholds
            if total_balance >= low_threshold:
                status = 'sufficient'
            elif total_balance >= critical_threshold:
                status = 'low'
            else:
                status = 'insufficient'

            # Create balance record
            balance_record = self.create({
                'provider_id': provider.id,
                'balance': total_balance,
                'currency': currency,
                'balance_status': status,
                'is_success': True,
                'check_date': fields.Datetime.now(),
                'low_balance_threshold': low_threshold,
                'critical_balance_threshold': critical_threshold,
                'error_message': f"Granted: {granted_balance} {currency}, Topped up: {topped_up_balance} {currency}"
                # 存储额外信息
            })

            # Update provider status if balance is low
            if status in ['low', 'insufficient'] and provider.auto_deactivate_low_balance:
                provider.write({'is_active': False})
                _logger.warning(f"Provider {provider.name} deactivated due to low balance: {total_balance} {currency}")

            _logger.info(f"DeepSeek balance check successful: {total_balance} {currency}")
            return balance_record

        except requests.exceptions.HTTPError as e:
            # 处理HTTP错误
            status_code = e.response.status_code if e.response else 'Unknown'
            if status_code == 401:
                error_msg = "Authentication failed: Invalid API key"
            elif status_code == 403:
                error_msg = "Permission denied: API key does not have balance access"
            elif status_code == 429:
                error_msg = "Rate limit exceeded: Too many requests"
            elif status_code >= 500:
                error_msg = f"Server error: DeepSeek API server issue (Status: {status_code})"
            else:
                error_msg = f"HTTP error: {str(e)}"

            _logger.error(f"DeepSeek balance check HTTP error: {error_msg}")
            return self._create_error_balance_record(provider, error_msg)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: Cannot connect to DeepSeek API"
            _logger.error(f"DeepSeek balance check connection error: {str(e)}")
            return self._create_error_balance_record(provider, error_msg)

        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout error: DeepSeek API request timed out"
            _logger.error(f"DeepSeek balance check timeout: {str(e)}")
            return self._create_error_balance_record(provider, error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            _logger.error(f"DeepSeek balance check request exception: {str(e)}")
            return self._create_error_balance_record(provider, error_msg)

        except ValueError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            _logger.error(f"DeepSeek balance check JSON parse error: {str(e)}")
            return self._create_error_balance_record(provider, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            _logger.error(f"DeepSeek balance check unexpected error: {str(e)}")
            return self._create_error_balance_record(provider, error_msg)

    # 添加 XML 视图中使用的方法
    def action_check_provider_balance(self):
        """Check balance for the provider associated with this record."""
        self.ensure_one()
        return self.provider_id.check_balance_now()

    def action_view_provider(self):
        """View the provider associated with this balance record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Provider',
            'res_model': 'oudu.bot.provider',
            'res_id': self.provider_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _check_openai_balance(self, provider):
        """Check OpenAI provider balance (placeholder - OpenAI doesn't have direct balance API)."""
        # OpenAI doesn't provide a direct balance API, so we'll create an unknown record
        return self._create_unknown_balance_record(provider, "OpenAI balance check not implemented")

    def _create_unknown_balance_record(self, provider, message="Balance API not available"):
        """Create a balance record for providers without balance API."""
        return self.create({
            'provider_id': provider.id,
            'balance': 0,
            'currency': 'Unknown',
            'balance_status': 'unknown',
            'is_success': True,
            'error_message': message,
            'check_date': fields.Datetime.now(),
            'low_balance_threshold': provider.low_balance_threshold,
            'critical_balance_threshold': provider.critical_balance_threshold
        })

    def _create_error_balance_record(self, provider, error_message):
        """Create a balance record for failed checks."""
        return self.create({
            'provider_id': provider.id,
            'balance': 0,
            'currency': 'Unknown',
            'balance_status': 'unknown',
            'is_success': False,
            'error_message': error_message,
            'check_date': fields.Datetime.now(),
            'low_balance_threshold': provider.low_balance_threshold,
            'critical_balance_threshold': provider.critical_balance_threshold
        })

    @api.model
    def check_all_providers_balance(self):
        """Check balance for all active providers."""
        active_providers = self.env['oudu.bot.provider'].search([
            ('is_active', '=', True)
        ])

        results = []
        for provider in active_providers:
            result = self.check_provider_balance(provider)
            results.append(result)

        # Send notifications for low balances
        self._send_balance_notifications()

        return results

    def _send_balance_notifications(self):
        """Send notifications for low balance providers."""
        # Get recent balance records with low or insufficient status
        recent_low_balances = self.search([
            ('balance_status', 'in', ['low', 'insufficient']),
            ('check_date', '>=', fields.Datetime.now().replace(hour=0, minute=0, second=0))
        ])

        if recent_low_balances:
            # Group by provider
            providers_warning = set()
            for balance in recent_low_balances:
                providers_warning.add(balance.provider_id)

            # TODO: Implement actual notification system
            # This could be email notifications, Odoo messages, etc.
            for provider in providers_warning:
                _logger.warning(f"Low balance alert for provider: {provider.name}")

    def get_latest_balance(self, provider_id):
        """Get the latest balance record for a provider."""
        return self.search([
            ('provider_id', '=', provider_id),
            ('is_success', '=', True)
        ], order='check_date desc', limit=1)

    @api.model
    def cron_check_balances(self):
        """Scheduled task to check balances regularly."""
        _logger.info("Starting scheduled balance check for all AI providers")
        return self.check_all_providers_balance()
