# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/25 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class DouyinConfig(models.Model):
    """抖音开放平台配置模型"""
    _name = 'oudu.douyin.config'
    _description = '抖音开放平台配置'
    _order = 'sequence, id'

    name = fields.Char(string='配置名称', required=True)
    sequence = fields.Integer(string='序列', default=10)
    active = fields.Boolean(string='激活', default=True)

    # 应用配置
    company_id = fields.Many2one('res.company', string='公司', required=True, default=lambda self: self.env.company)
    client_key = fields.Char(string='Client Key', required=True, help='抖音开放平台应用的Client Key')
    client_secret = fields.Char(string='Client Secret', required=True, help='抖音开放平台应用的Client Secret')
    redirect_uri = fields.Char(string='回调地址', compute='_compute_redirect_uri', help='OAuth2.0回调地址')

    # API端点配置
    api_base_url = fields.Char(
        string='API基础地址',
        default='https://open.douyin.com',
        required=True
    )
    auth_url = fields.Char(
        string='授权地址',
        default='https://open.douyin.com/platform/oauth/connect/',
        required=True
    )
    token_url = fields.Char(
        string='Token地址',
        default='https://open.douyin.com/oauth/access_token/',
        required=True
    )
    refresh_token_url = fields.Char(
        string='刷新Token地址',
        default='https://open.douyin.com/oauth/refresh_token/',
        required=True
    )
    client_token_url = fields.Char(
        string='Client Token地址',
        default='https://open.douyin.com/oauth/client_token/',
        required=True
    )

    # 权限范围
    scope = fields.Char(
        string='权限范围',
        default='user_info,mobile,*',
        help='授权权限范围，多个用逗号分隔'
    )

    # Token信息
    client_token = fields.Char(string='Client Token')
    client_token_expires = fields.Datetime(string='Client Token过期时间')
    stable_client_token = fields.Char(string='Stable Client Token')

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
    def create_default_config(self):
        """创建默认配置（如果不存在）"""
        existing_config = self.search([], limit=1)
        if not existing_config:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            default_redirect_uri = f"{base_url}/douyin/auth/callback"

            default_vals = {
                'name': '默认抖音配置',
                'client_key': 'awf4xgy8cibvhzuv',
                'client_secret': '请在此处填写您的Client Secret',
                'redirect_uri': default_redirect_uri,
                'scope': 'user_info,mobile,*',
                'state': 'draft',
                'active': True,
            }
            return self.create(default_vals)
        return existing_config

    @api.model
    def get_default_config(self):
        """获取默认配置"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create_default_config()
        return config

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
                expires_in = token_data.get('expires_in', 7200)
                expires_time = datetime.now() + timedelta(seconds=expires_in)

                self.write({
                    'client_token': token_data['access_token'],
                    'client_token_expires': expires_time,
                })
                return token_data['access_token']
        except Exception as e:
            _logger.error('获取Client Token失败: %s', str(e))
            raise

    def _get_stable_client_token(self):
        """获取Stable Client Token"""
        self.ensure_one()
        try:
            DouyinAPI = self.env['oudu.douyin.api']
            result = DouyinAPI.get_stable_client_token(self)

            if result.get('data', {}).get('access_token'):
                token_data = result['data']
                self.write({
                    'stable_client_token': token_data['access_token'],
                })
                return token_data['access_token']
        except Exception as e:
            _logger.error('获取Stable Client Token失败: %s', str(e))
            raise

    def get_auth_url(self, state=None):
        """生成授权URL"""
        self.ensure_one()
        # 移除scope中的*号，使用具体的权限范围
        scope = self.scope.replace('*', '').replace(',,', ',').strip(',')
        if not scope:
            scope = 'user_info'

        params = {
            'client_key': self.client_key,
            'response_type': 'code',
            'scope': scope,
            'redirect_uri': self.redirect_uri,
            'state': state or f"douyin_{int(datetime.now().timestamp())}",
        }

        # 过滤空值参数
        params = {k: v for k, v in params.items() if v}

        return f"{self.auth_url}?{urlencode(params)}"

    def action_auto_config(self):
        """自动配置：更新回调地址并测试连接"""
        self.ensure_one()
        try:
            # 更新回调地址
            self.update_redirect_uri()

            # 测试连接
            return self.action_test_connection()
        except Exception as e:
            raise UserError(_('自动配置失败: %s') % str(e))