# oudu_wechat_login_qrcode/models/qr_session.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
import uuid

_logger = logging.getLogger(__name__)


class WechatQRSession(models.Model):
    """微信二维码登录会话管理"""
    _name = 'wechat.qr.session'
    _description = 'WeChat QR Code Login Session'
    _order = 'create_date desc'

    name = fields.Char(string='Session ID', required=True, index=True, default=lambda self: str(uuid.uuid4()))
    state = fields.Selection([
        ('pending', '待扫描'),
        ('scanned', '已扫描'),
        ('confirmed', '已确认'),
        ('expired', '已过期'),
        ('canceled', '已取消')
    ], string='状态', default='pending', required=True)

    user_id = fields.Many2one(
        'res.users', string='关联用户',
        help='扫码登录成功后关联的系统用户'
    )
    openid = fields.Char(
        string='微信OpenID',
        help='微信用户的唯一标识'
    )
    create_date = fields.Datetime(
        string='创建时间', default=fields.Datetime.now
    )
    expire_date = fields.Datetime(
        string='过期时间', compute='_compute_expire_date', store=True
    )
    scan_date = fields.Datetime(string='扫码时间')
    confirm_date = fields.Datetime(string='确认时间')

    @api.depends('create_date')
    def _compute_expire_date(self) -> None:
        """计算二维码过期时间（默认5分钟）"""
        for record in self:
            if record.create_date:
                record.expire_date = record.create_date + timedelta(minutes=5)
            else:
                record.expire_date = fields.Datetime.now() + timedelta(minutes=5)

    @api.model
    def create_session(self) -> str:
        """创建新的二维码会话"""
        session = self.create({'state': 'pending'})
        return session.name

    def check_expired(self) -> None:
        """检查会话是否过期"""
        current_time = fields.Datetime.now()
        expired_sessions = self.filtered(
            lambda s: s.expire_date and s.expire_date <= current_time and s.state in ['pending', 'scanned']
        )
        if expired_sessions:
            expired_sessions.write({'state': 'expired'})

    def mark_scanned(self, openid: str) -> None:
        """标记二维码已扫描"""
        self.ensure_one()
        if self.state != 'pending':
            raise ValidationError(_('二维码状态异常'))

        self.write({
            'state': 'scanned',
            'openid': openid,
            'scan_date': fields.Datetime.now()
        })

    def mark_confirmed(self, user_id: int) -> None:
        """标记二维码已确认登录"""
        self.ensure_one()
        if self.state not in ['pending', 'scanned']:
            raise ValidationError(_('二维码状态异常'))

        self.write({
            'state': 'confirmed',
            'user_id': user_id,
            'confirm_date': fields.Datetime.now()
        })

    def mark_canceled(self) -> None:
        """标记二维码已取消"""
        self.ensure_one()
        self.write({'state': 'canceled'})

    @api.model
    def cleanup_expired_sessions(self) -> None:
        """清理过期的会话记录"""
        expired_date = fields.Datetime.now() - timedelta(days=1)
        expired_sessions = self.search([
            ('create_date', '<', expired_date)
        ])
        expired_sessions.unlink()
        _logger.info("清理了 %d 个过期微信二维码会话", len(expired_sessions))