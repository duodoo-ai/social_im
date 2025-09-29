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

    def refresh_access_token(self):
        """刷新Access Token"""
        for record in self:
            if not record.refresh_token:
                raise UserError(_('缺少Refresh Token，无法刷新'))

            try:
                DouyinAPI = self.env['oudu.douyin.api']
                result = DouyinAPI.refresh_access_token(record.config_id, record.refresh_token)

                if result.get('data'):
                    token_data = result['data']
                    expires_time = datetime.now() + timedelta(seconds=token_data.get('expires_in', 7200))

                    record.write({
                        'access_token': token_data.get('access_token'),
                        'refresh_token': token_data.get('refresh_token', record.refresh_token),
                        'expires_in': token_data.get('expires_in'),
                        'token_expires': expires_time,
                    })
                    _logger.info('刷新Token成功: %s', record.code)
            except Exception as e:
                _logger.error('刷新Token失败: %s', str(e))
                raise UserError(_('刷新Token失败: %s') % str(e))

    def get_user_info(self):
        """获取用户信息"""
        for record in self:
            if not record.access_token or not record.open_id:
                raise UserError(_('缺少Access Token或OpenID'))

            try:
                DouyinAPI = self.env['oudu.douyin.api']
                user_info = DouyinAPI.get_user_info(record.config_id, record.open_id, record.access_token)

                if user_info.get('data'):
                    user_data = user_info['data']
                    record.write({
                        'nickname': user_data.get('nickname'),
                        'avatar': user_data.get('avatar'),
                        'gender': str(user_data.get('gender', '0')),
                        'country': user_data.get('country'),
                        'province': user_data.get('province'),
                        'city': user_data.get('city'),
                    })
                    return user_data
            except Exception as e:
                _logger.error('获取用户信息失败: %s', str(e))
                raise UserError(_('获取用户信息失败: %s') % str(e))

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