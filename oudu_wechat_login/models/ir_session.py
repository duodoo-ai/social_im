# -*- coding: utf-8 -*-
"""
@Time    : 2025/08/02 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import models, fields, api, _
import logging, json
from odoo import SUPERUSER_ID
from odoo.api import Registry

_logger = logging.getLogger(__name__)


class IrSession(models.Model):
    _name = 'ir.session'
    _description = 'Odoo Sessions'

    sid = fields.Char('Session ID', required=True, index=True)
    uid = fields.Many2one('res.users', 'User', required=True, ondelete='cascade')
    context = fields.Text('Context')
    db = fields.Char('Database', required=True)
    session_token = fields.Char('Session Token', required=True, index=True)  # 新增字段
    write_date = fields.Datetime('Last Updated', default=fields.Datetime.now)

    def _save_session_to_db(self, db_name, session_id, user_id):
        """保存会话到数据库（修复约束问题）"""
        try:
            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                # 首先检查会话是否已存在
                cr.execute("SELECT 1 FROM ir_session WHERE sid = %s", (session_id,))
                session_exists = cr.fetchone()

                context = env['res.users'].context_get() or {}
                context_str = json.dumps(context)

                if session_exists:
                    # 更新现有会话
                    cr.execute("""
                        UPDATE ir_session 
                        SET uid = %s, context = %s, write_date = CURRENT_TIMESTAMP
                        WHERE sid = %s
                    """, (user_id, context_str, session_id))
                else:
                    # 插入新会话
                    cr.execute("""
                        INSERT INTO ir_session (sid, uid, db, context)
                        VALUES (%s, %s, %s, %s)
                    """, (session_id, user_id, db_name, context_str))

                cr.commit()
        except Exception as e:
            _logger.error("保存会话到数据库失败: %s", str(e), exc_info=True)
