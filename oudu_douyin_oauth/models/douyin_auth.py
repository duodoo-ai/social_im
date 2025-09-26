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
    """抖音授权记录模型"""
    _name = 'oudu.douyin.auth'
    _description = '抖音授权记录'
    _order = 'create_date desc'
    _rec_name = 'open_id'

    # 序列号
    code = fields.Char(
        string='授权码',
        required=True,
        default=lambda self: self._generate_code(),
        index=True
    )

    # 关联配置
    config_id = fields.Many2one(
        'oudu.douyin.config',
        string='抖音配置',
        required=True,
        ondelete='cascade'
    )

    # 用户关联
    user_id = fields.Many2one('res.users', string='关联用户')
    partner_id = fields.Many2one('res.partner', string='关联联系人')

    # Token信息
    access_token = fields.Char(string='Access Token')
    refresh_token = fields.Char(string='Refresh Token')
    expires_in = fields.Integer(string='过期时间(秒)')
    token_expires = fields.Datetime(string='Token过期时间')

    # 用户信息
    open_id = fields.Char(string='用户OpenID', index=True)
    union_id = fields.Char(string='用户UnionID', index=True)
    nickname = fields.Char(string='用户昵称')
    avatar = fields.Char(string='头像URL')
    gender = fields.Selection([
        ('0', '未知'),
        ('1', '男性'),
        ('2', '女性')
    ], string='性别')
    country = fields.Char(string='国家')
    province = fields.Char(string='省份')
    city = fields.Char(string='城市')

    # 手机号信息
    mobile = fields.Char(string='手机号')
    mobile_code = fields.Char(string='手机区号')

    # 授权信息
    scope = fields.Char(string='授权范围')
    state = fields.Char(string='状态参数', help='OAuth2.0 state参数，用于防止CSRF攻击')

    # 状态管理
    status = fields.Selection([
        ('pending', '待授权'),
        ('active', '已授权'),
        ('expired', '已过期'),
        ('revoked', '已撤销')
    ], string='状态', default='pending', index=True)

    # 时间戳
    auth_time = fields.Datetime(string='授权时间')
    last_sync_time = fields.Datetime(string='最后同步时间')

    # 经营身份信息
    enterprise_info = fields.Text(string='企业信息', help='JSON格式的经营身份信息')

    _sql_constraints = [
        ('open_id_config_unique', 'unique(open_id, config_id)', '同一配置下OpenID必须唯一!'),
    ]

    @api.model
    def _generate_code(self):
        """生成唯一授权码"""
        sequence = self.env['ir.sequence'].next_by_code('oudu.douyin.auth.code') or '/'
        return f'DOUYIN_AUTH_{sequence}'

    def _check_token_expiry(self):
        """检查Token是否过期"""
        self.ensure_one()
        if self.token_expires and datetime.now() > self.token_expires:
            self.status = 'expired'
            return True
        return False

    def refresh_access_token(self):
        """刷新Access Token"""
        self.ensure_one()
        try:
            DouyinAPI = self.env['oudu.douyin.api']
            result = DouyinAPI.refresh_access_token(self.config_id, self.refresh_token)

            if result.get('data'):
                token_data = result['data']
                expires_in = token_data.get('expires_in', 7200)
                expires_time = datetime.now() + timedelta(seconds=expires_in)

                self.write({
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data['refresh_token'],
                    'expires_in': expires_in,
                    'token_expires': expires_time,
                    'status': 'active',
                    'last_sync_time': datetime.now(),
                })
                return True
        except Exception as e:
            _logger.error('刷新Access Token失败: %s', str(e))
            self.status = 'expired'
            raise UserError(_('刷新Token失败: %s') % str(e))

    def get_user_info(self):
        """获取用户公开信息"""
        self.ensure_one()
        if self._check_token_expiry():
            self.refresh_access_token()

        try:
            DouyinAPI = self.env['oudu.douyin.api']
            result = DouyinAPI.get_user_info(self.config_id, self.open_id, self.access_token)

            if result.get('data'):
                user_data = result['data']
                self.write({
                    'nickname': user_data.get('nickname'),
                    'avatar': user_data.get('avatar'),
                    'gender': str(user_data.get('gender', '0')),
                    'country': user_data.get('country'),
                    'province': user_data.get('province'),
                    'city': user_data.get('city'),
                    'last_sync_time': datetime.now(),
                })
                return user_data
        except Exception as e:
            _logger.error('获取用户信息失败: %s', str(e))
            raise

    def get_user_mobile(self):
        """获取用户手机号"""
        self.ensure_one()
        if self._check_token_expiry():
            self.refresh_access_token()

        try:
            DouyinAPI = self.env['oudu.douyin.api']
            result = DouyinAPI.get_user_mobile(self.config_id, self.access_token)

            if result.get('data'):
                mobile_data = result['data']
                self.write({
                    'mobile': mobile_data.get('mobile'),
                    'mobile_code': mobile_data.get('mobile_code'),
                    'last_sync_time': datetime.now(),
                })
                return mobile_data
        except Exception as e:
            _logger.error('获取用户手机号失败: %s', str(e))
            raise

    def get_enterprise_info(self):
        """获取用户经营身份信息"""
        self.ensure_one()
        if self._check_token_expiry():
            self.refresh_access_token()

        try:
            DouyinAPI = self.env['oudu.douyin.api']
            result = DouyinAPI.get_enterprise_info(self.config_id, self.open_id, self.access_token)

            if result.get('data'):
                enterprise_data = result['data']
                self.write({
                    'enterprise_info': json.dumps(enterprise_data, ensure_ascii=False),
                    'last_sync_time': datetime.now(),
                })
                return enterprise_data
        except Exception as e:
            _logger.error('获取经营身份信息失败: %s', str(e))
            raise

    def action_revoke_auth(self):
        """撤销授权"""
        self.ensure_one()
        try:
            DouyinAPI = self.env['oudu.douyin.api']
            DouyinAPI.revoke_auth(self.config_id, self.open_id, self.access_token)

            self.write({
                'status': 'revoked',
                'access_token': False,
                'refresh_token': False,
                'token_expires': False,
            })
        except Exception as e:
            _logger.error('撤销授权失败: %s', str(e))
            raise UserError(_('撤销授权失败: %s') % str(e))