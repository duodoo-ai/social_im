# -*- coding: utf-8 -*-
import logging
import json
import werkzeug
from datetime import datetime
from urllib.parse import urlencode, quote

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DouyinAuthController(http.Controller):
    """抖音认证控制器"""

    @http.route('/douyin/auth/direct', type='http', auth='public', website=True)
    def douyin_direct_auth(self, **kwargs):
        """直接抖音授权跳转"""
        try:
            import secrets
            state = secrets.token_urlsafe(16)
            request.session['douyin_auth_state'] = state
            # 强制保存session
            request.session.modified = True
            _logger.info('设置session state: %s', state)

            # 获取基础URL用于回调地址
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = f"{base_url}/douyin/auth/callback"

            # 对redirect_uri进行URL编码
            redirect_uri_encoded = quote(redirect_uri, safe='')

            client_key = "aw0i6ui20ji5rf7y"
            scope = 'trial.whitelist'

            # 构建抖音授权URL
            douyin_url = (
                "https://open.douyin.com/platform/oauth/connect"
                f"?client_key={client_key}"
                f"&response_type=code"
                f"&scope={scope}"
                f"&redirect_uri={redirect_uri_encoded}"
                f"&state={state}"
            )
            _logger.info('直接跳转抖音授权: %s', douyin_url)

            # 修复：构建完整的HTML重定向页面
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="0; url={douyin_url}">
            </head>
            <body>
                <script>window.location.href = "{douyin_url}";</script>
            </body>
            </html>
            """
            return html

        except Exception as e:
            _logger.exception('直接授权跳转异常: %s', str(e))
            return request.redirect('/web/login?error=douyin_auth_failed')

    @http.route('/douyin/auth/qrcode/login', type='http', auth='public', website=True)
    def douyin_qrcode_login(self, **kwargs):
        """抖音扫码登录页面"""
        try:
            config = request.env['oudu.douyin.config'].sudo().get_default_config()
            if not config:
                return request.render('oudu_douyin_oauth.douyin_config_missing')

            # 生成唯一state参数
            import secrets
            state = secrets.token_urlsafe(16)
            request.session['douyin_auth_state'] = state

            # 生成授权URL
            auth_url = config.get_auth_url(state=state)
            _logger.info('生成抖音授权URL: %s', auth_url)

            return request.render('oudu_douyin_oauth.douyin_qrcode_page', {
                'auth_url': auth_url,
                'state': state,
            })

        except Exception as e:
            _logger.exception('扫码登录页面异常')
            return request.render('oudu_douyin_oauth.douyin_auth_error', {
                'error': 'system_error',
                'error_description': '系统异常，请稍后重试'
            })

    @http.route('/douyin/auth/callback', type='http', auth='public', website=True, csrf=False)
    def douyin_callback(self, **kwargs):
        """抖音授权回调处理"""
        try:
            code = kwargs.get('code')
            state = kwargs.get('state')
            error = kwargs.get('error')
            error_description = kwargs.get('error_description')

            _logger.info('抖音回调接收: code=%s, state=%s, error=%s',
                         code, state, error)

            if error:
                _logger.error('抖音授权回调错误: %s - %s', error, error_description)
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': error,
                    'error_description': error_description or '授权失败'
                })

            if not code:
                _logger.error('授权码缺失')
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': 'missing_code',
                    'error_description': '授权码缺失'
                })

            # 验证state参数 - 增加容错处理
            session_state = request.session.get('douyin_auth_state')
            _logger.info('State验证: session=%s, callback=%s', session_state, state)

            if state != session_state:
                _logger.warning('State参数不匹配: session=%s, callback=%s', session_state, state)
                # 对于state不匹配的情况，可以尝试继续处理，但记录警告
                # 或者返回错误页面
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': 'invalid_state',
                    'error_description': '会话已过期，请重新授权'
                })

            config = request.env['oudu.douyin.config'].sudo().get_default_config()
            if not config:
                return request.render('oudu_douyin_oauth.douyin_config_missing')

            # 获取access_token
            DouyinAPI = request.env['oudu.douyin.api']
            token_result = DouyinAPI.get_access_token(config, code)

            if not token_result.get('data'):
                error_data = token_result.get('data', {})
                error_code = error_data.get('error_code', 'unknown')
                error_msg = error_data.get('description', '获取Access Token失败')
                _logger.error('获取Access Token失败: %s - %s', error_code, error_msg)
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': error_code,
                    'error_description': error_msg
                })

            token_data = token_result['data']
            open_id = token_data.get('open_id')
            access_token = token_data.get('access_token')

            if not open_id or not access_token:
                _logger.error('Token数据不完整: open_id=%s, access_token=%s', open_id, access_token)
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': 'invalid_token',
                    'error_description': 'Token数据不完整'
                })

            _logger.info('成功获取Access Token, open_id: %s', open_id)

            # 创建或更新授权记录
            auth_record = self._find_or_create_auth_record(config, open_id, token_data, state)

            # 跳过用户信息获取（测试阶段）
            # self._sync_user_info(config, auth_record, open_id, access_token)

            # 直接设置默认用户信息
            auth_record.sudo().write({
                'nickname': f"抖音用户_{open_id[-8:]}",
                'status': 'active',
            })

            # 处理用户登录
            return self._handle_user_login(auth_record)

        except UserError as e:
            _logger.error('抖音回调业务异常: %s', str(e))
            return request.render('oudu_douyin_oauth.douyin_auth_error', {
                'error': 'business_error',
                'error_description': str(e)
            })
        except Exception as e:
            _logger.exception('抖音回调处理异常')
            return request.render('oudu_douyin_oauth.douyin_auth_error', {
                'error': 'system_error',
                'error_description': '系统异常，请稍后重试'
            })

    def _find_or_create_auth_record(self, config, open_id, token_data, state):
        """查找或创建授权记录"""
        auth_record = request.env['oudu.douyin.auth'].sudo().search([
            ('open_id', '=', open_id),
            ('config_id', '=', config.id)
        ], limit=1)

        # 计算过期时间
        from datetime import timedelta
        expires_time = datetime.now() + timedelta(seconds=token_data.get('expires_in', 7200))

        auth_vals = {
            'config_id': config.id,
            'open_id': open_id,
            'union_id': token_data.get('union_id'),
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in'),
            'token_expires': expires_time,
            'scope': token_data.get('scope'),
            'state': state,
            'auth_time': datetime.now(),
            'status': 'active',
        }

        if auth_record:
            auth_record.write(auth_vals)
            _logger.info('更新授权记录: %s', auth_record.code)
        else:
            auth_vals['state'] = state
            auth_record = request.env['oudu.douyin.auth'].sudo().create(auth_vals)
            _logger.info('创建授权记录: %s', auth_record.code)

        return auth_record

    def _sync_user_info(self, config, auth_record, open_id, access_token):
        """同步用户信息"""
        try:
            DouyinAPI = request.env['oudu.douyin.api']
            user_info = DouyinAPI.get_user_info(config, open_id, access_token)

            if user_info.get('data'):
                user_data = user_info['data']
                auth_record.sudo().write({
                    'nickname': user_data.get('nickname'),
                    'avatar': user_data.get('avatar'),
                    'gender': str(user_data.get('gender', '0')),
                    'country': user_data.get('country'),
                    'province': user_data.get('province'),
                    'city': user_data.get('city'),
                })
                _logger.info('同步用户信息成功: %s', user_data.get('nickname'))
        except Exception as e:
            _logger.warning('获取用户信息失败: %s', str(e))

    def _handle_user_login(self, auth_record):
        """处理用户登录逻辑"""
        # 清理session
        request.session.pop('douyin_auth_state', None)

        # 创建或查找用户并登录
        user = request.env['res.users'].sudo().douyin_auth({
            'open_id': auth_record.open_id,
            'union_id': auth_record.union_id,
            'nickname': auth_record.nickname,
            'avatar': auth_record.avatar,
        })

        if user:
            auth_record.sudo().write({'user_id': user.id})
            request.session.uid = user.id
            request.env.user = user

            _logger.info('用户登录成功: %s (ID: %s)', user.name, user.id)
            return request.redirect('/web')

        return request.redirect('/web/login')

    @http.route('/douyin/auth/success', type='http', auth='user', website=True)
    def douyin_success(self, **kwargs):
        """授权成功页面"""
        return request.render('oudu_douyin_oauth.douyin_auth_success')

    @http.route('/douyin/auth/check_status', type='json', auth='public', methods=['POST'])
    def check_login_status(self, **kwargs):
        """检查登录状态 - 供前端轮询调用"""
        try:
            state = kwargs.get('state')
            if not state:
                return {'status': 'error', 'message': '缺少state参数'}

            # 查找授权记录
            auth_record = request.env['oudu.douyin.auth'].sudo().search([
                ('state', '=', state),
                ('status', '=', 'active')
            ], limit=1)

            if auth_record and auth_record.user_id:
                return {
                    'status': 'success',
                    'message': '登录成功',
                    'redirect_url': '/web'
                }
            else:
                # 检查是否有pending状态的记录
                pending_record = request.env['oudu.douyin.auth'].sudo().search([
                    ('state', '=', state),
                    ('status', '=', 'pending')
                ], limit=1)

                if pending_record:
                    return {
                        'status': 'waiting',
                        'message': '等待用户授权...'
                    }
                else:
                    return {
                        'status': 'invalid',
                        'message': '授权状态无效或已过期'
                    }

        except Exception as e:
            _logger.error('检查登录状态失败: %s', str(e))
            return {'status': 'error', 'message': '系统错误'}