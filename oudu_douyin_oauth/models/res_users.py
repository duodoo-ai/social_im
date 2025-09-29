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

    def _get_login_token(self):
        """生成登录令牌"""
        self.ensure_one()
        # 使用Odoo的密码重置机制
        return self.sudo()._get_reset_token()

    @api.model
    def douyin_auth(self, values):
        """抖音授权登录"""
        try:
            open_id = values.get('open_id')
            if not open_id:
                raise UserError(_('缺少open_id参数'))

            # 查找已存在的用户
            user = self.search([('douyin_open_id', '=', open_id)], limit=1)
            if user:
                return user

            # 生成用户名称 - 确保不为空
            nickname = values.get('nickname') or f"抖音用户_{open_id[-8:]}"
            login = f"douyin_{open_id}"  # 确保登录名唯一

            # 创建用户
            user_vals = {
                'name': nickname,  # 确保名称不为空
                'login': login,
                'password': 'DouYin',
                'douyin_open_id': open_id,
                'douyin_union_id': values.get('union_id'),
            }

            user = self.sudo().create(user_vals)
            _logger.info('创建抖音用户: %s (ID: %s)', user.name, user.id)

            return user

        except Exception as e:
            _logger.error('抖音授权登录失败: %s', str(e))
            raise UserError(_('抖音登录失败: %s') % str(e))

