# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/25 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    """扩展用户模型，支持抖音登录"""
    _inherit = 'res.users'

    douyin_open_id = fields.Char(string='抖音OpenID', copy=False)
    douyin_union_id = fields.Char(string='抖音UnionID', copy=False)
    douyin_nickname = fields.Char(string='抖音昵称')
    douyin_avatar = fields.Char(string='抖音头像')

    douyin_auth_ids = fields.One2many(
        'oudu.douyin.auth',
        'user_id',
        string='抖音授权记录'
    )

    def action_douyin_login(self):
        """抖音登录动作"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/douyin/auth/login',
            'target': 'self',
        }

    @api.model
    def douyin_auth(self, auth_data):
        """抖音授权登录处理"""
        try:
            open_id = auth_data.get('open_id')
            union_id = auth_data.get('union_id')

            if not open_id:
                raise UserError(_('无效的授权数据: 缺少OpenID'))

            # 查找已存在的用户
            user = self.search([('douyin_open_id', '=', open_id)], limit=1)

            if not user:
                # 创建新用户
                login = f'douyin_{open_id}'
                user = self.create({
                    'name': auth_data.get('nickname', f'抖音用户_{open_id[-8:]}'),
                    'login': login,
                    'douyin_open_id': open_id,
                    'douyin_union_id': union_id,
                    'douyin_nickname': auth_data.get('nickname'),
                    'douyin_avatar': auth_data.get('avatar'),
                    'active': True,
                })

                _logger.info('创建新的抖音用户: %s (ID: %s)', user.name, user.id)

            return user
        except Exception as e:
            _logger.error('抖音授权登录失败: %s', str(e))
            raise UserError(_('抖音登录失败: %s') % str(e))