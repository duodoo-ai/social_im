# controllers/main.py
from urllib.parse import quote
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessDenied
from odoo import fields
import io
from datetime import datetime
import base64, qrcode, uuid, json, requests
import logging
from io import BytesIO
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessDenied
import time

_logger = logging.getLogger(__name__)


class WechatQRLoginController(http.Controller):
    """微信二维码登录控制器"""

    @http.route('/wechat/qr/login', type='http', auth='public', website=True)
    def wechat_login(self, **kwargs):
        # 创建新的二维码会话
        session_id = request.env['wechat.qr.session'].sudo().create_session()
        _logger.debug("Generated new session: %s", session_id)
        # 获取微信配置
        config_model = request.env['wechat.sso.config'].sudo()
        config = config_model.get_active_config()

        if not config:
            _logger.error("No active WeChat config found")
            return request.render('oudu_wechat_login_qrcode.qr_error_template', {
                'error_message': '微信登录未配置'
            })

        # 生成微信登录URL
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = quote(f"{base_url}/wechat/qr/callback")

        scope = config.auth_scope or 'snsapi_login'
        wechat_url = (
            f"https://open.weixin.qq.com/connect/oauth2/authorize"
            f"?appid={config.app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&state=qr_{session_id}"
            f"#wechat_redirect"
        )

        # 创建二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(wechat_url)
        qr.make(fit=True)

        # 生成二维码图像
        img = qr.make_image(fill_color="black", back_color="white")

        # 将图像转换为base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_img = base64.b64encode(buffered.getvalue()).decode()

        return request.render('oudu_wechat_login_qrcode.qr_template', {
            'qr_img': qr_img,
            'session_id': session_id,
        })

    @http.route('/wechat/qr/callback', type='http', auth='public', csrf=False)
    def wechat_qr_callback(self, **kwargs):
        _logger.debug("WeChat QR callback received: %s", kwargs)

        # 检查是否在微信环境中
        user_agent = request.httprequest.headers.get('User-Agent', '').lower()
        if 'micromessenger' not in user_agent:
            _logger.warning("Not in WeChat environment: %s", user_agent)
            return Response("请使用微信APP扫描上方二维码")

        code = kwargs.get('code')
        state = kwargs.get('state')

        if not code or not state:
            _logger.error("Missing code or state in callback: code=%s, state=%s", code, state)
            return Response('请求参数无效')

        # 提取会话ID
        if not state.startswith('qr_'):
            _logger.error("Invalid state format: %s", state)
            return Response('状态参数无效')

        session_id = state[3:]
        _logger.info("Processing WeChat callback for session: %s", session_id)

        try:
            # 首先检查会话是否存在
            session = request.env['wechat.qr.session'].sudo().search([
                ('name', '=', session_id),
                ('state', 'not in', ['expired', 'canceled'])
            ], limit=1)

            if not session:
                _logger.error("Session not found or expired: %s", session_id)
                return Response('会话不存在或已过期，请重新扫描二维码')

            # 检查会话是否已过期
            session.check_expired()
            # 重新加载会话对象以确保获取最新状态
            session = request.env['wechat.qr.session'].sudo().search([
                ('id', '=', session.id)
            ], limit=1)

            if session.state == 'expired':
                _logger.error("Session expired: %s", session_id)
                return Response('二维码已过期，请重新扫描')

            # 使用现有模块的认证逻辑
            config = request.env['wechat.sso.config'].sudo().get_active_config()
            if not config:
                _logger.error("No active WeChat config found")
                return Response('微信登录未配置')

            # 获取微信用户信息
            wechat_user_info = self._get_wechat_user_info(code, config)
            if not wechat_user_info:
                _logger.error("Failed to get WeChat user info for session: %s", session_id)
                session.mark_canceled()
                return Response('获取微信用户信息失败')

            # 查找或创建用户
            user = self._find_or_create_user(wechat_user_info, config)
            if not user:
                _logger.error("Failed to find or create user for session: %s", session_id)
                session.mark_canceled()
                return Response('用户创建失败')

            # 标记会话为已确认
            if not session.mark_confirmed(user.id):
                _logger.error("Failed to confirm session: %s", session_id)
                return Response('会话确认失败')

            _logger.info("Session confirmed: %s, user: %s", session_id, user.login)

            # 设置会话成功标记，用于跨标签页通信
            try:
                request.session['wechat_login_success'] = True
                request.session['wechat_login_session_id'] = session_id
            except Exception as e:
                _logger.warning("Failed to set session marker: %s", e)

            # 获取用户重定向URL
            redirect_url = self._get_user_redirect_url(user)

            # 为移动端设置会话信息
            try:
                # 确保数据库连接
                db_name = request.session.db

                # 直接设置会话信息
                request.session.uid = user.id
                request.session.login = user.login
                request.session.db = db_name

                # 计算会话令牌
                session_token = user._compute_session_token(request.session.sid)
                request.session.session_token = session_token

                # 更新会话上下文
                user_context = request.env['res.users'].context_get() or {}
                request.session.context = user_context

                # 标记会话为脏并保存
                request.session.is_dirty = True
                request._save_session()

                _logger.info("移动端用户登录成功: %s (ID: %s)", user.login, user.id)

                # 如果是移动端，直接重定向到目标页面
                return request.redirect(redirect_url)

            except Exception as mobile_auth_error:
                _logger.error("移动端认证失败: %s", mobile_auth_error)
                # 如果移动端认证失败，仍然返回HTML页面
                pass

            # 返回成功页面
            # 在wechat_qr_callback方法中添加localStorage设置，用于跨页面通信
            html_content = \
                f"""<!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>登录成功</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 20px;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                        }}
                        .success-container {{
                            background: white;
                            padding: 30px;
                            border-radius: 12px;
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                            text-align: center;
                            max-width: 400px;
                            width: 100%;
                        }}
                        .success-icon {{
                            color: #07C160;
                            font-size: 48px;
                            margin-bottom: 20px;
                        }}
                        h2 {{
                            color: #333;
                            margin-bottom: 10px;
                        }}
                        p {{
                            color: #666;
                            margin-bottom: 20px;
                        }}
                        .countdown {{
                            font-weight: bold;
                            color: #07C160;
                            font-size: 1.2em;
                        }}
                    </style>
                    <script>
                        // 设置倒计时（5秒）
                        var seconds = 5;
                        var redirectUrl = '{redirect_url}';
                        var sessionId = '{session_id}';

                        function updateCountdown() {{
                            document.getElementById('countdown').textContent = seconds;
                            seconds--;

                            if (seconds < 0) {{
                                // 倒计时结束后跳转
                                window.location.href = redirectUrl;
                            }} else {{
                                setTimeout(updateCountdown, 1000);
                            }}
                        }}

                        // 设置localStorage标记，通知其他标签页登录成功
                        document.addEventListener('DOMContentLoaded', function() {{
                            try {{
                                localStorage.setItem('wechat_login_success_' + sessionId, 'true');
                                localStorage.setItem('wechat_login_timestamp_' + sessionId, new Date().getTime());
                                localStorage.setItem('wechat_redirect_url_' + sessionId, redirectUrl);
                                localStorage.setItem('wechat_user_session_' + sessionId, '{user.id}');
                            }} catch (e) {{
                                console.warn('Failed to set localStorage:', e);
                            }}

                            // 启动倒计时
                            updateCountdown();
                        }});
                    </script>
                </head>
                <body>
                    <div class="success-container">
                        <div class="success-icon">✓</div>
                        <h2>登录成功！</h2>
                        <p>页面将在 <span id="countdown" class="countdown">5</span> 秒后自动跳转</p>
                    </div>
                </body>
                </html>"""
            return Response(html_content)

        except Exception as e:
            _logger.error("WeChat callback processing failed: %s", e, exc_info=True)
            return Response('微信登录处理异常，请稍后重试')

    def _find_or_create_user(self, wechat_user_info, config):
        """查找或创建用户"""
        try:
            nickname = wechat_user_info.get('nickname')
            openid = wechat_user_info.get('openid')
            unionid = wechat_user_info.get('unionid')
            login_name = f"wechat_{openid}"

            # 首先尝试通过openid查找用户
            user = request.env['res.users'].sudo().search([
                ('wechat_openid', '=', openid)
            ], limit=1)

            if user:
                _logger.info("Found existing user by openid: %s", user.login)
                return user

            # 如果没有找到，尝试通过unionid查找用户
            if unionid:
                user = request.env['res.users'].sudo().search([
                    ('wechat_unionid', '=', unionid)
                ], limit=1)

                if user:
                    _logger.info("Found existing user by unionid: %s", user.login)
                    # 更新openid
                    user.write({'wechat_openid': openid})
                    return user

            # 尝试通过登录名查找用户（防止重复创建）
            user = request.env['res.users'].sudo().search([
                ('login', '=', login_name)
            ], limit=1)

            if user:
                _logger.info("Found existing user by login: %s", user.login)
                # 更新微信信息
                user.write({
                    'wechat_openid': openid,
                    'wechat_unionid': unionid,
                    'wechat_nickname': nickname,
                    'wechat_sex': str(wechat_user_info.get('sex', '0')),
                    'wechat_city': wechat_user_info.get('city'),
                    'wechat_province': wechat_user_info.get('province'),
                    'wechat_country': wechat_user_info.get('country'),
                    'wechat_headimgurl': wechat_user_info.get('headimgurl'),
                })
                return user

            # 如果配置允许自动创建用户，则创建新用户
            if config.auto_create_user:
                _logger.info("Creating new portal user for openid: %s", openid)

                # 创建门户用户
                portal_user = request.env['res.users'].sudo().create({
                    'name': nickname or f"微信用户_{openid[:8]}",
                    'login': login_name,
                    'password': str(uuid.uuid4()),  # 随机密码
                    'wechat_openid': openid,
                    'wechat_unionid': unionid,
                    'wechat_nickname': nickname,
                    'wechat_sex': str(wechat_user_info.get('sex', '0')),
                    'wechat_city': wechat_user_info.get('city'),
                    'wechat_province': wechat_user_info.get('province'),
                    'wechat_country': wechat_user_info.get('country'),
                    'wechat_headimgurl': wechat_user_info.get('headimgurl'),
                    'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])]
                })

                _logger.info("Created new portal user: %s", portal_user.login)
                return portal_user
            else:
                _logger.warning("Auto create user is disabled and no existing user found for openid: %s", openid)
                return None

        except Exception as e:
            _logger.error("Failed to find or create user: %s", e)
            return None

    def _get_wechat_user_info(self, code: str, config) -> dict:
        """获取微信用户信息"""
        try:
            # 第一步：通过code获取access_token
            token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
            token_params = {
                'appid': config.app_id,
                'secret': config.app_secret,
                'code': code,
                'grant_type': 'authorization_code'
            }

            response = requests.get(token_url, params=token_params, timeout=10)
            token_data = response.json()

            if 'errcode' in token_data:
                _logger.error("WeChat token error: %s", token_data)
                return None

            # 第二步：通过access_token获取用户信息
            user_info_url = "https://api.weixin.qq.com/sns/userinfo"
            user_info_params = {
                'access_token': token_data['access_token'],
                'openid': token_data['openid'],
                'lang': 'zh_CN'
            }

            response = requests.get(user_info_url, params=user_info_params, timeout=10)
            user_info = response.json()

            if 'errcode' in user_info:
                _logger.error("WeChat user info error: %s", user_info)
                return None

            return user_info

        except Exception as e:
            _logger.error("Failed to get WeChat user info: %s", e)
            return None

    def _get_user_redirect_url(self, user):
        """根据用户类型获取重定向URL"""
        try:
            # 检查用户是否为内部用户
            user_group = request.env.ref('base.group_user')
            if user_group in user.groups_id:
                # 重定向到讨论页面
                return '/odoo/discuss'

            # 检查用户是否为门户用户
            portal_group = request.env.ref('base.group_portal')
            if portal_group in user.groups_id:
                return '/snatch_hall'

            # 默认重定向到网站首页
            return '/'
        except Exception as e:
            _logger.error("Error determining redirect URL: %s", e)
            return '/'

    def _validate_wechat_session(self, session_id):
        """
        微信会话验证标准方法
        :param session_id: 微信回调会话ID
        :return: 包含openid和session_key的字典
        """
        if not session_id:
            raise ValueError("缺少必要会话参数")

        session = request.env['wechat.qr.session'].sudo().search([
            ('name', '=', session_id),
            ('expire_date', '>', fields.Datetime.now())
        ], limit=1)
        _logger.info(f"正在验证会话ID: {session}")

        if not session:
            _logger.warning(f"无效会话ID: %s", session_id)
            raise AccessDenied("会话已过期或不存在")

        return session

    @http.route('/wechat/qr/do_login', type='http', auth='public', csrf=False)
    def wechat_qr_do_login(self, **kwargs):
        """使用令牌执行登录操作"""
        login_token = kwargs.get('token')
        redirect_url = kwargs.get('redirect_url', '/')

        _logger.info("尝试使用令牌登录: %s", login_token)

        if not login_token:
            _logger.error("缺少登录令牌")
            return request.redirect('/web/login?error=缺少登录令牌')

        # 从系统参数获取令牌值
        token_value = request.env['ir.config_parameter'].sudo().get_param(
            f'wechat_login_token_{login_token}'
        )

        if not token_value:
            _logger.error("无效的登录令牌: %s", login_token)
            return request.redirect('/web/login?error=无效的登录令牌')

        try:
            user_id, token_time = token_value.split(',')
            user_id = int(user_id)
            token_time = fields.Datetime.from_string(token_time)

            # 检查令牌是否过期（5分钟内有效）
            if (datetime.now() - token_time).total_seconds() > 300:
                # 删除过期令牌
                request.env['ir.config_parameter'].sudo().set_param(
                    f'wechat_login_token_{login_token}', False
                )
                _logger.error("登录令牌已过期: %s", login_token)
                return request.redirect('/web/login?error=登录令牌已过期')

            # 获取用户
            user = request.env['res.users'].sudo().browse(user_id)
            if not user.exists():
                _logger.error("用户不存在: %s", user_id)
                return request.redirect('/web/login?error=用户不存在')

            # 检查用户是否激活
            if not user.active:
                _logger.error("用户未激活: %s", user_id)
                return request.redirect('/web/login?error=用户未激活，请联系管理员')

            # 使用Odoo的标准登录方法
            try:
                # 确保数据库连接
                db_name = request.session.db

                # 直接设置会话信息
                request.session.uid = user.id
                request.session.login = user.login
                request.session.db = db_name

                # 计算会话令牌
                session_token = user._compute_session_token(request.session.sid)
                request.session.session_token = session_token

                # 更新会话上下文
                user_context = request.env['res.users'].context_get() or {}
                request.session.context = user_context

                # 标记会话为脏并保存
                request.session.is_dirty = True
                request._save_session()

                _logger.info("用户登录成功: %s (ID: %s)", user.login, user.id)

            except Exception as auth_error:
                _logger.error("认证失败: %s", auth_error)
                # 备用方案：使用更简单的方法
                try:
                    # 直接设置UID并跳过会话令牌检查
                    request.session.uid = user.id
                    request.session.login = user.login
                    # 设置一个简单的会话令牌
                    request.session.session_token = str(uuid.uuid4())
                    request.session.get_context()
                    _logger.info("使用备用方案登录成功: %s", user.login)
                except Exception as fallback_error:
                    _logger.error("备用登录方案也失败: %s", fallback_error)
                    return request.redirect('/web/login?error=认证失败，请联系管理员')

            # 删除已使用的令牌
            request.env['ir.config_parameter'].sudo().set_param(
                f'wechat_login_token_{login_token}', False
            )

            # 使用 _get_user_redirect_url 方法获取正确的重定向URL
            final_redirect_url = self._get_user_redirect_url(user)
            _logger.info("用户类型检测完成，重定向到: %s", final_redirect_url)

            # 检查重定向URL是否有效
            if not final_redirect_url or not final_redirect_url.startswith('/'):
                _logger.warning("无效的重定向URL: %s，使用默认URL", final_redirect_url)
                final_redirect_url = '/'

            # 重定向到目标页面
            return request.redirect(final_redirect_url)

        except Exception as e:
            _logger.error("登录处理失败: %s", e, exc_info=True)
            return request.redirect('/web/login?error=登录处理失败')

    @http.route('/wechat/qr/status', type='http', auth='public', csrf=False, methods=['POST'])
    def qr_login_status(self, **kw):
        # 处理预检请求
        if request.httprequest.method == 'OPTIONS':
            response = Response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            return response
        # 正常处理POST请求
        try:
            # 记录请求信息以便调试
            _logger.info("QR状态检查请求收到")
            _logger.debug("请求方法: %s", request.httprequest.method)
            _logger.debug("请求头: %s", dict(request.httprequest.headers))

            # 尝试从请求体中获取 JSON 数据
            data = {}
            if request.httprequest.data:
                try:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                    _logger.debug("请求体JSON数据: %s", data)
                except (ValueError, UnicodeDecodeError) as e:
                    _logger.error("解析JSON数据失败: %s", e)
                    # 如果解析失败，尝试从表单数据获取
                    data = request.params
                    _logger.debug("使用表单数据: %s", data)
            else:
                # 如果没有请求体数据，使用URL参数
                data = request.params
                _logger.debug("使用URL参数: %s", data)

            session_id = data.get('session_id')

            if not session_id:
                _logger.error("缺少session_id参数，可用数据: %s", data)
                return Response(json.dumps({
                    'status': 'error',
                    'code': 400,
                    'message': '缺少session_id参数'
                }), content_type='application/json', status=400)

            _logger.info("正在验证会话ID: %s", session_id)

            # 查找会话
            session = request.env['wechat.qr.session'].sudo().search([
                ('name', '=', session_id)
            ], limit=1)

            if not session:
                _logger.warning("无效会话ID: %s", session_id)
                return Response(json.dumps({
                    'status': 'error',
                    'code': 404,
                    'message': '会话不存在'
                }), content_type='application/json', status=404)

            # 检查会话是否已过期
            session.check_expired()

            # 重新加载会话对象以确保获取最新状态
            session = request.env['wechat.qr.session'].sudo().search([
                ('id', '=', session.id)
            ], limit=1)

            # 增加status状态判断，只有已确认的会话才返回成功
            if session.state == 'confirmed':
                # 检查用户是否存在
                user = request.env['res.users'].sudo().browse(session.user_id.id)
                _logger.info("用户存在: %s", user)

                if user:
                    # 获取重定向URL
                    redirect_url = self._get_user_redirect_url(user)

                    # 生成临时登录令牌
                    login_token = str(uuid.uuid4())
                    # 存储令牌和用户ID的映射关系
                    request.env['ir.config_parameter'].sudo().set_param(
                        f'wechat_login_token_{login_token}',
                        f'{user.id},{fields.Datetime.now()}'
                    )

                    result = {
                        'status': 'success',
                        'countdown': 5,  # 5秒倒计时
                        'redirect_url': redirect_url,
                        'user_id': user.id,  # 返回用户ID
                        'login_token': login_token  # 返回登录令牌
                    }
                    _logger.info("返回成功结果: %s", result)
                    response = Response(json.dumps(result), content_type='application/json')
                    response.headers.add('Access-Control-Allow-Origin', '*')
                    return response
                else:
                    return Response(json.dumps({
                        'status': 'error',
                        'code': 404,
                        'message': '用户不存在'
                    }), content_type='application/json', status=404)
            else:
                result = {'status': session.state, 'message': '等待扫码确认'}
                _logger.debug("返回状态结果: %s", result)
                response = Response(json.dumps(result), content_type='application/json')
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response

        except Exception as e:
            _logger.error("会话验证失败: %s", str(e), exc_info=True)
            response = Response(json.dumps({
                'status': 'error',
                'code': 500,
                'message': '会话验证失败'
            }), content_type='application/json', status=500)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

    @http.route('/web/session/logout', type='http', auth="public")
    def logout(self, **kwargs):
        """自定义登出路由"""
        try:
            # 清除当前会话
            request.session.logout(keep_db=True)
            _logger.info("User logged out successfully")
        except Exception as e:
            _logger.error("Logout failed: %s", e, exc_info=True)
        finally:
            # 始终重定向到登录页面
            return request.redirect('/web')


#  已实现移动端扫码登录系统功能
#  已实现登录验证功能，目前在处理按权限导航问题
#  成功实现内部用户/门户用户扫码二维码登录Odoo系统

