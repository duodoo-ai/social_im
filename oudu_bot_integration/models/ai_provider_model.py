from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class AIProviderModel(models.Model):
    _name = 'oudu.bot.provider.model'
    _description = 'AI Provider Model'
    _order = 'provider_id, model_id'
    _rec_name = 'model_id'  # 设置默认的显示名称字段

    # Basic Information
    provider_id = fields.Many2one(
        'oudu.bot.provider',
        string='Provider',
        required=True,
        ondelete='cascade'
    )
    model_id = fields.Char(
        string='Model ID',
        required=True,
        help='Unique identifier for the model (e.g., deepseek-chat)'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='User-friendly display name'
    )

    # Model Details
    model_data = fields.Json(
        string='Model Data',
        help='Raw model data from provider API'
    )
    object_type = fields.Char(
        string='Object Type',
        compute='_compute_model_details',
        store=True
    )
    created_timestamp = fields.Integer(
        string='Created Timestamp',
        compute='_compute_model_details',
        store=True
    )
    owned_by = fields.Char(
        string='Owned By',
        compute='_compute_model_details',
        store=True
    )

    # Status
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this model is currently available'
    )
    is_recommended = fields.Boolean(
        string='Recommended',
        default=False,
        store=True,
        help='Whether this is a recommended model for the provider'
    )

    # Usage Information
    last_used = fields.Datetime(
        string='Last Used',
        help='When this model was last used'
    )
    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        help='Number of times this model has been used'
    )

    _sql_constraints = [
        ('model_provider_unique', 'unique(model_id, provider_id)',
         'Model ID must be unique per provider!'),
    ]

    @api.depends('model_id', 'provider_id')
    def _compute_display_name(self):
        """Compute display name for the model."""
        for record in self:
            if record.model_id and record.provider_id:
                record.display_name = f"{record.provider_id.name} - {record.model_id}"
            else:
                record.display_name = record.model_id or 'Unknown Model'

    @api.depends('model_data')
    def _compute_model_details(self):
        """Extract model details from the model_data JSON."""
        for record in self:
            if record.model_data and isinstance(record.model_data, dict):
                record.object_type = record.model_data.get('object', '')
                record.created_timestamp = record.model_data.get('created', 0)
                record.owned_by = record.model_data.get('owned_by', '')
            else:
                record.object_type = ''
                record.created_timestamp = 0
                record.owned_by = ''

    @api.model
    def create(self, vals):
        """Override create to set is_recommended based on model ID."""
        record = super().create(vals)
        record._set_recommended_status()
        return record

    def write(self, vals):
        """Override write to update is_recommended if model_id changes."""
        result = super().write(vals)
        if 'model_id' in vals:
            self._set_recommended_status()
        return result

    def _set_recommended_status(self):
        """Set recommended status based on model ID patterns."""
        for record in self:
            if record.provider_id.provider_type == 'deepseek':
                # For DeepSeek, recommend chat models
                record.is_recommended = 'chat' in (record.model_id or '').lower()
            elif record.provider_id.provider_type == 'openai':
                # For OpenAI, recommend GPT-4 models
                record.is_recommended = 'gpt-4' in (record.model_id or '').lower()
            else:
                record.is_recommended = False

    def action_use_model(self):
        """Set this model as the default for the provider."""
        self.ensure_one()
        self.provider_id.write({'default_model': self.model_id})

        # Update usage information
        self.write({
            'last_used': fields.Datetime.now(),
            'usage_count': self.usage_count + 1
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Default Model Updated',
                'message': f'Default model set to: {self.model_id}',
                'type': 'success',
                'sticky': False,
            }
        }

    def get_model_info(self):
        """Get formatted model information for display."""
        self.ensure_one()
        info_lines = [
            f"Model: {self.model_id}",
            f"Type: {self.object_type or 'Unknown'}",
            f"Provider: {self.owned_by or 'Unknown'}",
        ]

        if self.created_timestamp:
            from datetime import datetime
            created_date = datetime.fromtimestamp(self.created_timestamp)
            info_lines.append(f"Created: {created_date.strftime('%Y-%m-%d')}")

        return "\n".join(info_lines)

    @api.model
    def get_recommended_models(self, provider_id):
        """Get recommended models for a provider."""
        return self.search([
            ('provider_id', '=', provider_id),
            ('is_active', '=', True),
            ('is_recommended', '=', True)
        ], order='usage_count desc')