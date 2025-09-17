# -*- coding: utf-8 -*-
"""
@Time    : 2025/08/02 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import http, api, SUPERUSER_ID, _
from odoo.http import request, Response, Session
from odoo.exceptions import ValidationError, MissingError
from odoo.modules.registry import Registry
import json
import time
import logging
import re
from . import core_controller
# 从模块根目录导入 session_store
from odoo.addons.oudu_wechat_login import session_store

# 设置全局会话存储
http.session_store = session_store.global_session_store

_logger = logging.getLogger(__name__)



class WechatLoginController(http.Controller):

    def _validate_session(self, session_id, db_name=None):
        """从PipelineApiController迁移的会话验证方法"""
        if not db_name:
            db_name = getattr(request, 'db', None) or config.get('db_name')
            if not db_name:
                _logger.error("Session storage test failed: No database specified")
                return None

        try:
            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                cr.execute("""
                    SELECT uid, write_date 
                    FROM ir_session 
                    WHERE sid = %s 
                    AND write_date >= NOW() - interval '24 hours'
                """, (session_id,))
                result = cr.fetchone()

                if result:
                    uid, write_date = result
                    user = env['res.users'].sudo().browse(uid)
                    if user.exists() and user.active:
                        return user
        except Exception as e:
            if "relation \"ir_session\" does not exist" in str(e):
                self._ensure_session_table(db_name)
                return self._validate_session(session_id, db_name)
            _logger.error("Session storage test failed: %s", str(e), exc_info=True)
        return None

    def _authenticate_user(self, session_id):
        """通过会话ID验证用户身份"""
        try:
            # 处理带数据库前缀的session_id
            if '.' in session_id:
                db_name, clean_session_id = session_id.split('.', 1)
            else:
                db_name = None
                clean_session_id = session_id

            # 验证会话ID格式
            if not re.match(r'^[a-zA-Z0-9_\-]+$', clean_session_id):
                _logger.error("Session storage test failed: Invalid session ID format: %s", clean_session_id)
                return None

            # 验证会话
            user = self._validate_session(clean_session_id, db_name)
            if user:
                # 设置当前环境用户
                request.update_env(user=user.id)
                return user.id  # 返回用户ID

            return None
        except Exception as e:
            _logger.error("Session storage test failed: %s", str(e), exc_info=True)
            return None

    def _save_session_to_db(self, db_name, session_id, user_id):
        """保存会话到数据库（使用PostgreSQL的UPSERT操作）"""
        try:
            registry = Registry(db_name)
            with registry.cursor() as cr:
                # 使用ON CONFLICT语法实现插入或更新
                cr.execute("""
                        INSERT INTO ir_session (sid, uid, db, context)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (sid) DO UPDATE
                        SET uid = EXCLUDED.uid,
                            context = EXCLUDED.context,
                            write_date = CURRENT_TIMESTAMP
                    """, (session_id, user_id, db_name, json.dumps(request.session.context or {})))
        except Exception as e:
            _logger.error("Session storage test failed: %s", str(e), exc_info=True)

    def _cors_response(self, data, status=200):
        """CORS兼容的响应"""
        # 允许的前端域名
        allowed_origins = [
            "*",
            "https://your-production-frontend.com"
        ]

        # 获取并验证请求来源
        request_origin = request.httprequest.headers.get('Origin', '')
        origin = request_origin if request_origin in allowed_origins else allowed_origins[0]

        headers = [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Origin, Content-Type, Accept, Authorization, X-Requested-With'),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Max-Age', '86400'),
        ]

        # 处理OPTIONS请求
        if request.httprequest.method == 'OPTIONS':
            headers.append(('Content-Length', '0'))
            return Response(headers=headers, status=200)

        return Response(
            json.dumps(data, ensure_ascii=False),
            headers=headers,
            status=status
        )

    @http.route('/wechat/callback', type='http', auth='none')
    def wechat_callback(self, **kw):
        """微信回调处理 - 修复会话管理问题"""
        _logger.info("接收到微信回调请求，参数: %s", kw)
        code = kw.get('code')
        state = kw.get('state')

        if not code:
            return request.redirect('/web/login?error=缺少授权码')

        try:
            config = request.env['wechat.sso.config'].sudo().get_active_config()
            if not config:
                return request.redirect('/web/login?error=微信登录未配置')

            _logger.info("正在处理微信回调，code: %s", code)

            # 使用当前请求的环境处理用户认证，避免多连接问题
            user_obj = request.env['res.users'].sudo()
            user = user_obj.with_context(wechat_config=config).auth_wechat('wechat', code, kw)

            if user:
                _logger.info("微信用户认证成功, user_id: %s", user.id)

                # 立即提交事务，确保用户记录持久化
                request.env.cr.commit()

                # 重新获取用户对象，确保在当前环境中可用
                # 添加重试机制，防止事务隔离问题
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        user = request.env['res.users'].sudo().browse(user.id)

                        # 检查用户是否存在
                        if not user.exists():
                            _logger.warning("用户记录不存在，尝试 %s/%s", attempt + 1, max_retries)
                            if attempt < max_retries - 1:
                                time.sleep(0.1)  # 短暂等待后重试
                                continue
                            else:
                                raise MissingError(_("用户记录不存在或已被删除"))

                        _logger.info("用户信息: %s", user.name)
                        break

                    except MissingError:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(0.1)
                        continue

                # 确保用户环境正确设置
                request.update_env(user=user.id)
                _logger.info("请求环境用户ID: %s", request.env.uid)

                # 直接设置会话信息，避免使用可能无效的session.save()
                request.session.uid = user.id
                request.session.login = user.login
                request.session.db = request.db
                _logger.info("会话ID: %s", request.session.sid)
                _logger.info("会话登录: %s", request.session.login)

                # 确保session_token被正确设置
                if not request.session.session_token:
                    request.session.session_token = user._compute_session_token(request.session.sid)
                    _logger.info("会话令牌已设置")

                # 更新会话上下文
                user_context = request.env['res.users'].context_get() or {}
                request.session.context = user_context
                _logger.info("会话上下文已更新")

                # 标记会话为脏并保存
                request.session.is_dirty = True
                request._save_session()

                request.env.cr.commit()
                _logger.info("正在跳转, url: %s", '/snatch_hall')
                return request.redirect('/snatch_hall')
            else:
                return request.redirect('/web/login?error=用户验证失败')

        except MissingError as e:
            _logger.error("用户记录不存在: %s", str(e))
            return request.redirect('/web/login?error=用户记录不存在或已被删除')
        except Exception as e:
            _logger.exception("微信登录处理异常: %s", str(e))
            # 回滚当前事务，避免后续操作失败
            try:
                request.env.cr.rollback()
            except Exception:
                pass
            return request.redirect('/web/login?error=系统异常')

