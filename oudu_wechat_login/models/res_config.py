# -*- coding: utf-8 -*-
"""
@Time    : 2025/08/02 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging, requests, json, time
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class WechatConfig(models.Model):
    _name = 'wechat.sso.config'
    _description = '微信服务号配置'
    _order = 'sequence, id'
    _sql_constraints = [
        ('unique_active_company', 'unique(company_id, active)', '每个公司只能有一个活跃的微信配置!'),
    ]

    name = fields.Char('配置名称', required=True, index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company', '公司',
        default=lambda self: self.env.company,
        required=True
    )
    app_id = fields.Char('App ID', required=True, help='微信开发者后台的AppID')
    app_secret = fields.Char('App Secret', required=True, help='微信开发者后台的AppSecret')
    active = fields.Boolean('启用登录', default=True)
    auto_create_user = fields.Boolean('自动创建用户', default=True,
                                      help='当微信用户首次登录时自动创建Odoo用户账户')
    token_expiration = fields.Integer('令牌有效期(秒)', default=7200,
                                      help='微信访问令牌的有效时间')
    qrcode_expiry = fields.Integer('二维码有效期(秒)', default=300,
                                   help='登录二维码的有效时间')
    default_user_group = fields.Many2one(
        'res.groups', string='默认用户组',
        help='自动创建用户时分配的默认权限组')
    auth_scope = fields.Selection([
        ('snsapi_base', '静默授权(snsapi_base)'),
        ('snsapi_userinfo', '用户信息授权(snsapi_userinfo)')],
        string='授权范围', default='snsapi_userinfo',
        required=True)
    redirect_uri = fields.Char('回调地址', compute='_compute_redirect_uri',
                               help='微信回调地址，需配置到微信后台')
    token = fields.Char(string='令牌token', help='微信验证令牌token')
    encoding_aes_key = fields.Char(string='编码AES密钥token', help='微信验证令牌token')
    # 添加 force_refresh 字段（用于紧急刷新）
    force_refresh = fields.Boolean(string='强制刷新', default=False)
    access_token_expires = fields.Char(string='Access Token过期时间', help='access_token过期时间戳')
    refresh_token_expires = fields.Char(string='Refresh Token过期时间', help='refresh_token过期时间戳')
    template_id = fields.Char(string='模板ID',
                              default='XGJp1jOypqrjRrjzok6FLbUnzTIKH2EAdirPRcr6By8',
                              help='微信模板消息的模板ID，用于发送报告消息')

    @api.depends('company_id')
    def _compute_redirect_uri(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for config in self:
            config.redirect_uri = f"{base_url}/wechat/callback"

    @api.constrains('auto_create_user', 'default_user_group')
    def _check_default_group(self):
        for config in self:
            if config.auto_create_user and not config.default_user_group:
                raise ValidationError(_("启用自动创建用户时必须设置默认用户组"))

    @api.constrains('token_expiration', 'qrcode_expiry')
    def _check_time_values(self):
        if any(r.token_expiration < 60 for r in self):
            raise ValidationError(_('令牌有效期不能小于60秒'))
        if any(r.qrcode_expiry < 60 for r in self):
            raise ValidationError(_('二维码有效期不能小于60秒'))

    @api.constrains('active')
    def _check_active_config(self):
        """确保每个公司只有一个活跃配置"""
        for config in self:
            if config.active:
                active_configs = self.search([
                    ('company_id', '=', config.company_id.id),
                    ('active', '=', True),
                    ('id', '!=', config.id)
                ])
                if active_configs:
                    raise ValidationError(_(
                        '每个公司只能有一个活跃的微信配置。请先禁用其他配置。'
                    ))

    def get_active_config(self, company_id=None):
        """获取指定公司的活跃配置"""
        try:
            config = self.search([
                ('active', '=', True),
                ('company_id', '=', 1)
            ], limit=1)

            if not config:
                _logger.warning("未找到公司[%s]的活跃微信配置", company_id)
            return config
        except Exception as e:
            _logger.error("查询微信配置时发生异常: %s", str(e))
            raise

    def get_wechat_access_token(self):
        """使用稳定版接口获取 token (适配微信最新要求)"""
        self.ensure_one()
        now = datetime.now()

        # 检查缓存有效性（提前5分钟刷新）
        if self.token and self.access_token_expires:
            try:
                expires_time = datetime.strptime(self.access_token_expires, '%Y-%m-%d %H:%M:%S')
                if now < expires_time - timedelta(minutes=5):  # 有效期内且未到刷新窗口
                    _logger.info("使用缓存的稳定版 token (过期时间: %s)", self.access_token_expires)
                    return self.token
            except Exception as e:
                _logger.error("解析过期时间失败: %s", str(e))

        # 调用稳定版接口
        url = "https://api.weixin.qq.com/cgi-bin/stable_token"
        data = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
            "force_refresh": self.force_refresh  # 仅在泄漏等紧急情况下启用
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            _logger.error("稳定版 token 获取失败: %s", str(e))
            raise UserError(_("微信接口连接失败: %s") % str(e))

        if 'access_token' in result:
            expires_in = result.get('expires_in', 7200)
            # 计算过期时间点
            expires_time = now + timedelta(seconds=expires_in)
            expires_str = expires_time.strftime('%Y-%m-%d %H:%M:%S')

            # 更新记录
            self.write({
                'token': result['access_token'],
                'access_token_expires': expires_str
            })
            _logger.info("更新稳定版 token (有效期至: %s)", expires_str)
            return self.token
        else:
            error_msg = _("稳定版 token 错误 [%s]: %s") % (result.get('errcode'), result.get('errmsg'))
            _logger.error(error_msg)
            raise UserError(error_msg)

    def cron_update_access_token(self):
        """定时任务：更新所有活跃配置的微信token"""
        # 获取所有活跃的微信配置
        active_configs = self.search([('active', '=', True)])

        for config in active_configs:
            try:
                # 直接调用方法更新token
                config.get_wechat_access_token()
                _logger.info("成功更新微信配置ID:%s的token", config.id)
            except Exception as e:
                _logger.error("更新微信配置ID:%s 的token失败: %s", config.id, str(e))
                continue
        return True