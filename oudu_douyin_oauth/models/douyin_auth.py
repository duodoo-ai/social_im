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
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class DouyinAuth(models.Model):
    _name = 'oudu.douyin.auth'
    _description = '抖音授权记录'
    _order = 'auth_time desc'

    # 基础字段
    code = fields.Char(string='授权码', default=lambda self: self._generate_auth_code())
    config_id = fields.Many2one('oudu.douyin.config', string='配置', required=True)
    user_id = fields.Many2one('res.users', string='关联用户')
    partner_id = fields.Many2one('res.partner', string='关联联系人')
    status = fields.Selection([
        ('pending', '待授权'),
        ('active', '已授权'),
        ('expired', '已过期'),
        ('revoked', '已撤销')
    ], string='状态', default='pending')

    # 授权状态字段
    state = fields.Char(string='State参数', help='OAuth2.0 state参数')

    # 抖音用户信息
    open_id = fields.Char(string='OpenID')
    union_id = fields.Char(string='UnionID')
    nickname = fields.Char(string='用户昵称')
    avatar = fields.Char(string='头像')
    gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('unknown', '未知')
    ], string='性别')
    country = fields.Char(string='国家')
    province = fields.Char(string='省份')
    city = fields.Char(string='城市')

    # Token信息
    access_token = fields.Char(string='Access Token')
    refresh_token = fields.Char(string='Refresh Token')
    token_expires = fields.Datetime(string='Token过期时间')
    expires_in = fields.Integer(string='过期时间(秒)')

    # 手机号信息
    mobile = fields.Char(string='手机号')
    mobile_code = fields.Char(string='手机区号')

    # 企业信息
    enterprise_info = fields.Json(string='经营身份信息')

    # 时间信息
    auth_time = fields.Datetime(string='授权时间', default=fields.Datetime.now)
    create_date = fields.Datetime(string='创建时间', default=fields.Datetime.now)

    # 权限范围
    scope = fields.Char(string='授权范围')

    @api.model
    def _generate_auth_code(self):
        """生成授权码序列"""
        return self.env['ir.sequence'].next_by_code('oudu.douyin.auth.code') or 'DOUYIN_AUTH_00000'

    def get_client_token(self, config):
        """获取client_token"""
        endpoint = '/oauth/client_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'grant_type': 'client_credential',
        }
        return self._make_request(endpoint, method='POST', data=data)

    def action_revoke_auth(self):
        """撤销授权"""
        for record in self:
            record.write({
                'status': 'revoked',
                'access_token': False,
                'refresh_token': False,
            })
            _logger.info('撤销授权: %s', record.code)

    @api.model
    def cleanup_expired_tokens(self):
        """清理过期Token的定时任务"""
        expired_records = self.search([
            ('token_expires', '<', datetime.now()),
            ('status', '=', 'active')
        ])

        expired_records.write({'status': 'expired'})
        _logger.info('清理了 %s 个过期Token', len(expired_records))


