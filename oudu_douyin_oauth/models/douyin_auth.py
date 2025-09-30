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

    def get_access_token(self, config, auth_code):
        """使用授权码获取access_token"""
        endpoint = '/oauth/access_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
        }
        return self._make_request(endpoint, method='POST', data=data)

    def get_client_token(self, config):
        """获取client_token"""
        endpoint = '/oauth/client_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'grant_type': 'client_credential',
        }
        return self._make_request(endpoint, method='POST', data=data)

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


    def get_user_public_info(self, config, open_id, access_token):
        """
        获取用户公开信息
        文档: https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/get-account-open-info

        Args:
            config: 抖音配置对象
            open_id: 用户唯一标识
            access_token: 访问令牌

        Returns:
            dict: 用户公开信息
        """
        try:
            _logger.info('开始获取用户公开信息: open_id=%s', open_id)

            # 构建请求URL
            url = "https://open.douyin.com/api/douyin/v1/user/user_info/"

            # 构建请求参数
            params = {
                'open_id': open_id,
                'access_token': access_token
            }

            _logger.info('抖音用户公开信息API请求: GET %s, 参数: %s', url, params)

            # 发送GET请求
            response = requests.get(
                url,
                params=params,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=10
            )

            _logger.info('抖音用户公开信息API响应状态: %s', response.status_code)
            _logger.info('抖音用户公开信息API响应内容: %s', response.text)

            if response.status_code != 200:
                _logger.error('抖音用户公开信息API请求失败: %s', response.status_code)
                return {
                    'data': {
                        'error_code': response.status_code,
                        'description': f'HTTP请求失败: {response.status_code}'
                    },
                    'message': 'error'
                }

            result = response.json()

            # 检查API返回的错误码
            if result.get('data', {}).get('error_code') != 0:
                error_code = result.get('data', {}).get('error_code')
                error_msg = result.get('data', {}).get('description', '未知错误')
                _logger.error('抖音用户公开信息API业务错误: %s - %s', error_code, error_msg)

            return result

        except requests.exceptions.Timeout:
            _logger.error('获取用户公开信息请求超时')
            return {
                'data': {
                    'error_code': 'timeout',
                    'description': '请求超时'
                },
                'message': 'error'
            }
        except requests.exceptions.ConnectionError:
            _logger.error('获取用户公开信息连接错误')
            return {
                'data': {
                    'error_code': 'connection_error',
                    'description': '网络连接错误'
                },
                'message': 'error'
            }
        except Exception as e:
            _logger.exception('获取用户公开信息异常: %s', str(e))
            return {
                'data': {
                    'error_code': 'system_error',
                    'description': f'系统异常: {str(e)}'
                },
                'message': 'error'
            }