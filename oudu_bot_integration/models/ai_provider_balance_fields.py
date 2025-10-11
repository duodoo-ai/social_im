from odoo import models, fields, api
from odoo.tools import date_utils
from datetime import datetime, timedelta


class AIProviderBalanceFields(models.Model):
    _inherit = 'oudu.bot.provider'

    # Balance monitoring settings
    low_balance_threshold = fields.Float(
        string='Low Balance Threshold',
        default=10.0,
        help='Balance threshold for low balance warning'
    )
    critical_balance_threshold = fields.Float(
        string='Critical Balance Threshold',
        default=1.0,
        help='Balance threshold for critical balance warning'
    )
    auto_deactivate_low_balance = fields.Boolean(
        string='Auto Deactivate on Low Balance',
        default=True,
        help='Automatically deactivate provider when balance is too low'
    )
    balance_check_frequency = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Balance Check Frequency', default='daily')

    # Status tracking fields
    last_balance_check = fields.Datetime(
        string='Last Balance Check',
        readonly=True
    )
    last_balance_check_result = fields.Char(
        string='Last Check Result',
        readonly=True
    )

    # Related balance records
    balance_history = fields.One2many(
        'oudu.bot.provider.balance',
        'provider_id',
        string='Balance History'
    )
    current_balance = fields.Float(
        string='Current Balance',
        compute='_compute_current_balance',
        store=True
    )
    currency = fields.Char(
        string='Currency',
        compute='_compute_current_balance',
        store=True
    )
    balance_status = fields.Selection([
        ('sufficient', 'Sufficient'),
        ('low', 'Low Balance'),
        ('insufficient', 'Insufficient'),
        ('unknown', 'Unknown')
    ], string='Balance Status', compute='_compute_current_balance', store=True)

    # Computed fields for display
    balance_display = fields.Char(
        string='Balance',
        compute='_compute_balance_display'
    )
    next_check_date = fields.Datetime(
        string='Next Check',
        compute='_compute_next_check_date'
    )

    @api.depends('balance_history', 'balance_history.balance', 'balance_history.currency',
                 'balance_history.balance_status')
    def _compute_current_balance(self):
        """Compute current balance from the latest successful check."""
        BalanceModel = self.env['oudu.bot.provider.balance']
        for provider in self:
            latest_balance = BalanceModel.search([
                ('provider_id', '=', provider.id),
                ('is_success', '=', True)
            ], order='check_date desc', limit=1)

            if latest_balance:
                provider.current_balance = latest_balance.balance
                provider.currency = latest_balance.currency
                provider.balance_status = latest_balance.balance_status
            else:
                provider.current_balance = 0.0
                provider.currency = 'Unknown'
                provider.balance_status = 'unknown'

    @api.depends('current_balance', 'currency', 'balance_status')
    def _compute_balance_display(self):
        """Compute display string for balance."""
        for provider in self:
            if provider.currency and provider.currency != 'Unknown':
                status_map = {
                    'sufficient': '✅',
                    'low': '⚠️',
                    'insufficient': '❌',
                    'unknown': '❓'
                }
                emoji = status_map.get(provider.balance_status, '❓')
                provider.balance_display = f"{emoji} {provider.current_balance} {provider.currency}"
            else:
                provider.balance_display = "❓ Not checked"

    @api.depends('last_balance_check', 'balance_check_frequency')
    def _compute_next_check_date(self):
        """Compute next scheduled balance check date."""
        for provider in self:
            if not provider.last_balance_check:
                provider.next_check_date = False
                continue

            last_check = fields.Datetime.from_string(provider.last_balance_check)
            frequency_map = {
                'hourly': timedelta(hours=1),
                'daily': timedelta(days=1),
                'weekly': timedelta(weeks=1),
                'monthly': timedelta(days=30)
            }

            delta = frequency_map.get(provider.balance_check_frequency, timedelta(days=1))
            provider.next_check_date = last_check + delta

    def check_balance_now(self):
        """Manual balance check for this provider."""
        self.ensure_one()
        balance_record = self.env['oudu.bot.provider.balance'].check_provider_balance(self)

        # Update provider status
        self.write({
            'last_balance_check': fields.Datetime.now(),
            'last_balance_check_result': 'Success' if balance_record.is_success else 'Failed'
        })

        # Return notification
        if balance_record.is_success:
            if balance_record.balance_status == 'unknown':
                message = f'Balance check completed. {balance_record.error_message}'
                message_type = 'warning'
            else:
                status_display = {
                    'sufficient': 'Sufficient',
                    'low': 'Low',
                    'insufficient': 'Insufficient'
                }.get(balance_record.balance_status, 'Unknown')

                message = f'Current balance: {balance_record.balance} {balance_record.currency} ({status_display})'
                message_type = 'info'
        else:
            message = balance_record.error_message
            message_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Balance Check',
                'message': message,
                'type': message_type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }

    def action_view_balance_history(self):
        """View balance history for this provider."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Balance History - {self.name}',
            'res_model': 'oudu.bot.provider.balance',
            'view_mode': 'list,form',
            'domain': [('provider_id', '=', self.id)],
            'context': {
                'default_provider_id': self.id,
                'search_default_group_by_provider': 1
            },
            'target': 'current'
        }

    def action_check_all_balances(self):
        """Check balances for all providers."""
        providers = self.search([('is_active', '=', True)])
        results = []

        for provider in providers:
            result = provider.check_balance_now()
            results.append(result)

        # Show summary notification
        success_count = len([r for r in results if r['params']['type'] in ['info', 'warning']])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Balance Check Summary',
                'message': f'Checked {len(providers)} providers. {success_count} successful.',
                'type': 'info' if success_count == len(providers) else 'warning',
                'sticky': True,
            }
        }

    @api.model
    def cron_check_balances_by_frequency(self):
        """Scheduled task to check balances based on frequency settings."""
        now = fields.Datetime.now()

        # Check hourly providers
        if now.hour == 0:  # Only check hourly providers once per day at midnight
            hourly_providers = self.search([
                ('is_active', '=', True),
                ('balance_check_frequency', '=', 'hourly')
            ])
            for provider in hourly_providers:
                provider.check_balance_now()

        # Check daily providers
        daily_providers = self.search([
            ('is_active', '=', True),
            ('balance_check_frequency', '=', 'daily'),
            '|', ('last_balance_check', '=', False),
            ('last_balance_check', '<', fields.Datetime.to_string(now - timedelta(days=1)))
        ])
        for provider in daily_providers:
            provider.check_balance_now()

        # Check weekly providers (on Mondays)
        if now.weekday() == 0:  # Monday
            weekly_providers = self.search([
                ('is_active', '=', True),
                ('balance_check_frequency', '=', 'weekly'),
                '|', ('last_balance_check', '=', False),
                ('last_balance_check', '<', fields.Datetime.to_string(now - timedelta(weeks=1)))
            ])
            for provider in weekly_providers:
                provider.check_balance_now()

        # Check monthly providers (on 1st of month)
        if now.day == 1:
            monthly_providers = self.search([
                ('is_active', '=', True),
                ('balance_check_frequency', '=', 'monthly'),
                '|', ('last_balance_check', '=', False),
                ('last_balance_check', '<', fields.Datetime.to_string(now - timedelta(days=30)))
            ])
            for provider in monthly_providers:
                provider.check_balance_now()

    def write(self, vals):
        """Override write to handle balance threshold changes."""
        result = super().write(vals)

        # If thresholds changed, re-evaluate balance status for active providers
        if any(field in vals for field in ['low_balance_threshold', 'critical_balance_threshold']):
            BalanceModel = self.env['oudu.bot.provider.balance']
            for provider in self.filtered(lambda p: p.is_active):
                latest_balance = BalanceModel.search([
                    ('provider_id', '=', provider.id),
                    ('is_success', '=', True)
                ], order='check_date desc', limit=1)

                if latest_balance:
                    # 确保使用正确的数据类型进行比较
                    balance = float(latest_balance.balance)
                    low_threshold = float(provider.low_balance_threshold)
                    critical_threshold = float(provider.critical_balance_threshold)

                    # Re-evaluate balance status with new thresholds
                    if balance >= low_threshold:
                        new_status = 'sufficient'
                    elif balance >= critical_threshold:
                        new_status = 'low'
                    else:
                        new_status = 'insufficient'

                    # Update the latest balance record
                    latest_balance.write({'balance_status': new_status})

        return result