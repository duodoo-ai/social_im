# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/23 10:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import models, fields, api, _
from typing import Optional


class WechatUserMessage(models.Model):
    _name = 'wechat.user.message'
    _description = '微信用户消息记录'
    _order = 'send_time DESC'

    wechat_message_id = fields.Many2one(
        'wechat.message',
        string='微信消息',
        required=True,
        ondelete='cascade'
    )

    user_id = fields.Many2one(
        'res.users',
        string='用户',
        required=True
    )

    wechat_openid = fields.Char(
        string='微信OpenID',
        related='user_id.wechat_openid',
        readonly=True,
        store=True
    )

    state = fields.Selection([
        ('sent', '已发送'),
        ('delivered', '已送达'),
        ('read', '已阅读'),
        ('clicked', '已点击'),
        ('failed', '发送失败')
    ], string='状态', default='sent', required=True)

    message_id = fields.Char(string='微信消息ID')
    error_message = fields.Text(string='错误信息')

    send_time = fields.Datetime(string='发送时间')
    read_time = fields.Datetime(string='阅读时间')
    click_time = fields.Datetime(string='点击时间')

    click_count = fields.Integer(string='点击次数', default=0)

    # 索引优化
    _sql_constraints = [
        ('unique_message_user', 'unique(wechat_message_id, user_id)', '同一消息对同一用户只能有一条记录!'),
    ]

    def mark_as_clicked(self) -> None:
        """标记为已点击"""
        self.write({
            'state': 'clicked',
            'click_time': fields.Datetime.now(),
            'click_count': self.click_count + 1
        })