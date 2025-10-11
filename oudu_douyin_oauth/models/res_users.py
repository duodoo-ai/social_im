# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    """扩展用户模型，支持抖音登录"""
    _inherit = 'res.users'

    douyin_open_id = fields.Char(string='抖音OpenID', copy=False, index=True)
    douyin_nickname = fields.Char(string='抖音昵称')
    douyin_avatar = fields.Char(string='抖音头像')
    douyin_union_id = fields.Char(string='抖音UnionID', copy=False, index=True)

    douyin_auth_ids = fields.One2many(
        'oudu.douyin.auth',
        'user_id',
        string='抖音授权记录'
    )

    @api.model
    def douyin_auth(self, auth_data):
        """抖音授权登录处理"""
        try:
            open_id = auth_data.get('open_id')
            union_id = auth_data.get('union_id')
            nickname = auth_data.get('nickname', '抖音用户')

            if not open_id:
                raise UserError(_('无效的授权数据: 缺少OpenID'))

            # 首先通过union_id查找用户
            user = None
            if union_id:
                user = self.search([('douyin_union_id', '=', union_id)], limit=1)

            # 如果没找到，再通过open_id查找
            if not user:
                user = self.search([('douyin_open_id', '=', open_id)], limit=1)

            if not user:
                # 生成唯一的登录名
                login = f'douyin_{open_id}'
                counter = 1
                while self.search([('login', '=', login)]):
                    login = f'douyin_{open_id}_{counter}'
                    counter += 1

                # 创建新用户
                user_vals = {
                    'name': nickname,
                    'login': login,
                    'douyin_open_id': open_id,
                    'douyin_union_id': union_id,
                    'douyin_nickname': nickname,
                    'douyin_avatar': auth_data.get('avatar'),
                    'active': True,
                }

                user = self.sudo().create(user_vals)
                _logger.info('创建新的抖音用户: %s (ID: %s)', user.name, user.id)
            else:
                # 更新用户信息
                update_vals = {
                    'douyin_nickname': nickname,
                    'douyin_avatar': auth_data.get('avatar'),
                }
                if union_id and not user.douyin_union_id:
                    update_vals['douyin_union_id'] = union_id

                user.write(update_vals)
                _logger.info('更新抖音用户信息: %s (ID: %s)', user.name, user.id)

            return user

        except Exception as e:
            _logger.error('抖音授权登录失败: %s', str(e))
            raise UserError(_('抖音登录失败: %s') % str(e))