import base64

import qrcode
from odoo import models, fields, api
import uuid
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'

    mcp_api_key = fields.Char('AI API密钥', copy=False, readonly=True, groups='base.group_system')
    mcp_enabled = fields.Boolean('启用AI访问', default=False)
    mcp_last_access = fields.Datetime('最后访问时间', readonly=True)
    mcp_access_count = fields.Integer('访问次数', default=0, readonly=True)

    # 增加一个二维码的图片字段, 用于生成二维码, 二维码的内容由系统参数中的agent_url和mcp_api_key组成, 简化为base64编码
    mcp_qr_code = fields.Binary('AI二维码', copy=False, readonly=True, compute='_compute_mcp_qr_code', store=True)

    @api.depends('mcp_api_key')
    def _compute_mcp_qr_code(self):
        for user in self:
            mcp_qr_code_str = f'{self.env["ir.config_parameter"].get_param("ai.agent_url")}/mcp/{user.mcp_api_key}'
            mcp_qr_code_str = base64.b64encode(mcp_qr_code_str.encode('utf-8'))

            # 生成二维码图片
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(mcp_qr_code_str)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            user.mcp_qr_code = img.tobytes()

    def action_generate_mcp_key(self):
        """生成新的API密钥"""
        for user in self:
            if not user.mcp_enabled:
                raise UserError('请先启用AI访问')
            user.mcp_api_key = str(uuid.uuid4())

    def action_disable_mcp(self):
        """禁用MCP访问"""
        for user in self:
            user.write({
                'mcp_enabled': False,
                'mcp_api_key': False
            })

    @api.model
    def verify_mcp_access(self, api_key):
        """验证API密钥"""
        user = self.sudo().search([
            ('mcp_api_key', '=', api_key),
            ('mcp_enabled', '=', True),
            ('active', '=', True)
        ], limit=1)
        
        if not user:
            return False
            
        user.write({
            'mcp_last_access': fields.Datetime.now(),
            'mcp_access_count': user.mcp_access_count + 1
        })
        return user 