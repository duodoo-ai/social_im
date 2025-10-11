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
        """Check DeepSeek provider balance."""
        try:
            url = "https://api.deepseek.com/user/balance"
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {provider.api_key}'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            balance = data.get('balance', 0)
            currency = data.get('currency', 'CNY')

            # Determine balance status
            if balance >= provider.low_balance_threshold:
                status = 'sufficient'
            elif balance >= provider.critical_balance_threshold:
                status = 'low'
            else:
                status = 'insufficient'

            # Create balance record
            balance_record = self.create({
                'provider_id': provider.id,
                'balance': balance,
                'currency': currency,
                'balance_status': status,
                'is_success': True,
                'check_date': fields.Datetime.now()
            })

            # Update provider status if balance is low
            if status in ['low', 'insufficient']:
                provider.write({'is_active': False})
                _logger.warning(f"Provider {provider.name} deactivated due to low balance: {balance} {currency}")

            _logger.info(f"DeepSeek balance check successful: {balance} {currency}")
            return balance_record

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            return self._create_error_balance_record(provider, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            return self._create_error_balance_record(provider, error_msg)

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
            'check_date': fields.Datetime.now()
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
            'check_date': fields.Datetime.now()
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
