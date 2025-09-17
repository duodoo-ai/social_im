import json
import logging
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.http import Session

_logger = logging.getLogger(__name__)


class DBSessionStore:
    """自定义数据库会话存储"""

    def __init__(self, db_name=None):
        self.db = db_name

    def get(self, sid, db_name=None):
        """从数据库获取会话"""
        db = db_name or self.db
        if not db:
            return None

        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                cr.execute("""
                    SELECT uid, context, write_date
                    FROM ir_session
                    WHERE sid = %s
                    AND write_date >= NOW() - interval '24 hours'
                """, (sid,))
                result = cr.fetchone()

                if result:
                    uid, context, write_date = result
                    # 创建会话对象
                    session = Session(self, sid, json.loads(context) if context else {})
                    session.uid = uid
                    session.write_date = write_date
                    return session
            return None
        except Exception as e:
            _logger.error("Session storage error: %s", str(e))
            return None

    def save(self, session, db_name=None):
        """保存会话到数据库"""
        db = db_name or self.db
        if not db:
            return False

        try:
            registry = Registry(db)
            with registry.cursor() as cr:
                context = json.dumps(session.context) if session.context else None

                cr.execute("""
                    INSERT INTO ir_session (sid, uid, context, db, write_date)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (sid)
                    DO UPDATE SET
                        uid = EXCLUDED.uid,
                        context = EXCLUDED.context,
                        write_date = NOW()
                """, (session.sid, session.uid, context, db))
            return True
        except Exception as e:
            _logger.error("Session storage error: %s", str(e))
            return False

    def _table_exists(self, cr, table_name):
        """检查表是否存在"""
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        return cr.fetchone()[0]

    def _ensure_session_table(self, cr):
        """确保会话表存在"""
        _logger.info("Creating session table: ir_session")

        cr.execute("""
            CREATE TABLE IF NOT EXISTS ir_session (
                id SERIAL PRIMARY KEY,
                sid VARCHAR NOT NULL,
                uid INTEGER NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
                context TEXT,
                db VARCHAR NOT NULL,
                session_token VARCHAR NOT NULL,
                write_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cr.execute("CREATE INDEX IF NOT EXISTS ir_session_sid_idx ON ir_session (sid)")
        cr.execute("CREATE INDEX IF NOT EXISTS ir_session_uid_idx ON ir_session (uid)")
        cr.execute("CREATE INDEX IF NOT EXISTS ir_session_token_idx ON ir_session (session_token)")

        # 添加唯一约束
        try:
            cr.execute("ALTER TABLE ir_session ADD CONSTRAINT unique_sid UNIQUE (sid)")
        except Exception:
            # 约束可能已存在
            pass
        cr.commit()


# 全局会话存储实例
global_session_store = DBSessionStore()