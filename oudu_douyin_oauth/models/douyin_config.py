# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class DouyinConfig(models.Model):
    """抖音开放平台配置模型 """
    _name = 'oudu.douyin.config'
    _description = '抖音开放平台配置'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char(string='配置名称', required=True)
    sequence = fields.Integer(string='序列', default=10)
    active = fields.Boolean(string='激活', default=True)

    # 应用配置
    company_id = fields.Many2one('res.company', string='公司', required=True, default=lambda self: self.env.company)
    client_key = fields.Char(string='Client Key', required=True, help='抖音开放平台应用的Client Key')
    client_secret = fields.Char(string='Client Secret', required=True, help='抖音开放平台应用的Client Secret')
    redirect_uri = fields.Char(string='回调地址', compute='_compute_redirect_uri', help='OAuth2.0回调地址')

    # 权限范围
    scope = fields.Selection([
        ('user_info', '用户信息授权(user_info)'),
        ('mobile', '手机号授权(mobile)'),
        ('*', '所有权限(*)')],
        string='授权范围', default='user_info',
        required=True)
    access_token = fields.Char(string='Access Token', help='抖音开放平台应用的Access Token')

    # 状态信息
    state = fields.Selection([
        ('draft', '草稿'),
        ('tested', '已测试'),
        ('production', '生产')
    ], string='状态', default='draft')

    # 关联记录
    auth_ids = fields.One2many('oudu.douyin.auth', 'config_id', string='授权记录')

    _sql_constraints = [
        ('client_key_unique', 'unique(client_key)', 'Client Key必须唯一!'),
    ]

    @api.model
    def get_default_config(self):
        """获取默认配置"""
        return self.search([('active', '=', True)], limit=1)

    @api.constrains('redirect_uri')
    def _check_redirect_uri(self):
        """验证回调地址格式"""
        for record in self:
            if record.redirect_uri and not record.redirect_uri.startswith(('http://', 'https://')):
                raise ValidationError(_('回调地址必须以http://或https://开头'))

    @api.depends('company_id')
    def _compute_redirect_uri(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for config in self:
            config.redirect_uri = f"{base_url}/douyin/auth/callback"

    def get_auth_url(self, state=None):
        """生成抖音授权URL"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f"{base_url}/douyin/auth/callback"
        redirect_uri_encoded = quote(redirect_uri, safe='')

        # 更新授权URL和scope
        auth_url = (
            "https://open.douyin.com/platform/oauth/connect"
            f"?client_key={self.client_key}"
            f"&response_type=code"
            f"&scope=trial.whitelist"  # 修改为测试白名单权限
            f"&redirect_uri={redirect_uri_encoded}"
        )

        if state:
            auth_url += f"&state={state}"

        return auth_url

    def action_test_connection(self):
        """测试连接配置"""
        self.ensure_one()
        try:
            # 获取Client Token测试连接
            client_token = self._get_client_token()
            if client_token:
                self.write({'state': 'tested'})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('连接测试成功'),
                        'message': _('抖音开放平台连接配置测试成功！'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            _logger.error('抖音连接测试失败: %s', str(e))
            raise UserError(_('连接测试失败: %s') % str(e))

    def _get_client_token(self):
        """获取Client Token"""
        self.ensure_one()
        try:
            DouyinAPI = self.env['oudu.douyin.api']
            result = DouyinAPI.get_client_token(self)

            if result.get('data', {}).get('access_token'):
                token_data = result['data']

                self.write({
                    'access_token': token_data['access_token'],
                })
                return token_data['access_token']
        except Exception as e:
            _logger.error('获取Client Token失败: %s', str(e))
            raise