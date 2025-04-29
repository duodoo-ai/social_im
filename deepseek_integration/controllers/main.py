from odoo import http
from odoo.http import request

class DeepseekController(http.Controller):
    @http.route('/deepseek/status', type='json', auth='user')
    def check_status(self):
        config = request.env['deepseek.config'].get_active_config()
        return {
            'active': bool(config),
            'model': config.model if config else None
        }

    @http.route('/deepseek/history', type='json', auth='user')
    def get_history(self, limit=10):
        return request.env['deepseek.history'].search_read(
            [('status', '=', 'success')],
            ['prompt', 'response', 'create_date'],
            limit=limit
        )
