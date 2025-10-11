from odoo import models, fields, api


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
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Balance Check Frequency', default='daily')

    # Related balance records
    balance_history = fields.One2many(
        'oudu.bot.provider.balance',
        'provider_id',
        string='Balance History'
    )
    current_balance = fields.Float(
        string='Current Balance',
        compute='_compute_current_balance'
    )
    currency = fields.Char(
        string='Currency',
        compute='_compute_current_balance'
    )
    balance_status = fields.Selection([
        ('sufficient', 'Sufficient'),
        ('low', 'Low Balance'),
        ('insufficient', 'Insufficient'),
        ('unknown', 'Unknown')
    ], string='Balance Status', compute='_compute_current_balance')

    @api.depends('balance_history')
    def _compute_current_balance(self):
        """Compute current balance from the latest successful check."""
        for provider in self:
            latest_balance = self.env['oudu.bot.provider.balance'].get_latest_balance(provider.id)
            if latest_balance:
                provider.current_balance = latest_balance.balance
                provider.currency = latest_balance.currency
                provider.balance_status = latest_balance.balance_status
            else:
                provider.current_balance = 0
                provider.currency = 'Unknown'
                provider.balance_status = 'unknown'

    def check_balance_now(self):
        """Manual balance check for this provider."""
        self.ensure_one()
        balance_record = self.env['oudu.bot.provider.balance'].check_provider_balance(self)

        # Return notification
        if balance_record.is_success:
            if balance_record.balance_status == 'unknown':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Balance Check',
                        'message': f'Balance check completed. {balance_record.error_message}',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Balance Check',
                        'message': f'Current balance: {balance_record.balance} {balance_record.currency}',
                        'type': 'info',
                        'sticky': False,
                    }
                }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Balance Check Failed',
                    'message': balance_record.error_message,
                    'type': 'danger',
                    'sticky': False,
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
            'context': {'default_provider_id': self.id}
        }
