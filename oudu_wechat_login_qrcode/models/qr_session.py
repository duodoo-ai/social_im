from odoo import models, fields, api
from odoo.exceptions import ValidationError
import uuid
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WechatQRSession(models.Model):
    _name = 'wechat.qr.session'
    _description = '微信二维码会话'
    _order = 'create_date desc'

    name = fields.Char('会话ID', required=True, index=True, default=lambda self: str(uuid.uuid4()))
    user_id = fields.Many2one('res.users',
                              '用户',
                              index=True,
                              ondelete='cascade'
                              )
    state = fields.Selection([
        ('pending', '待扫描'),
        ('scanned', '已扫描'),
        ('confirmed', '已确认'),
        ('expired', '已过期'),
        ('canceled', '已取消')
    ], string='状态', default='pending', index=True)
    expire_date = fields.Datetime('过期时间', index=True)
    create_date = fields.Datetime('创建时间', default=fields.Datetime.now)
    active = fields.Boolean(default=True)

    @api.model
    def create_session(self, expiry_seconds=300):
        """创建新的二维码会话"""
        expire_date = fields.Datetime.to_string(
            datetime.now() + timedelta(seconds=expiry_seconds)
        )
        session = self.create({
            'expire_date': expire_date,
        })
        return session.name

    def check_expired(self):
        """检查会话是否过期"""
        now = fields.Datetime.now()
        for session in self:
            if session.state in ['pending', 'scanned'] and session.expire_date < now:
                session.state = 'expired'

    def mark_scanned(self):
        """标记为已扫描"""
        self.check_expired()
        if self.state == 'pending':
            self.state = 'scanned'
            return True
        return False

    def mark_confirmed(self, user_id):
        """标记为已确认"""
        self.check_expired()
        if self.state in ['pending', 'scanned']:
            self.write({
                'state': 'confirmed',
                'user_id': user_id
            })
            return True
        return False

    def mark_canceled(self):
        """标记为已取消"""
        if self.state in ['pending', 'scanned']:
            self.state = 'canceled'
            return True
        return False

    @api.model
    def cleanup_expired_sessions(self):
        """清理过期会话的定时任务"""
        expiry_date = fields.Datetime.to_string(datetime.now() - timedelta(days=1))
        expired_sessions = self.search([('create_date', '<', expiry_date)])
        if expired_sessions:
            expired_sessions.unlink()
            _logger.info("Cleaned up %d expired WeChat QR sessions", len(expired_sessions))