# oudu_wechat_login_qrcode/controllers/main.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import logging
import qrcode
import io
import base64
from urllib.parse import quote

_logger = logging.getLogger(__name__)


class WechatQRLoginController(http.Controller):
    """微信二维码登录控制器"""

    @http.route('/wechat/qr/login', type='http', auth='public', website=True, lang='zh_CN')
    def wechat_qr_login_page(self, **kwargs):
        """显示二维码登录页面"""
        try:
            # 生成二维码数据
            qr_data = self.generate_qr_code()
            if 'error' in qr_data:
                return request.render('oudu_wechat_login_qrcode.qr_error_template', {
                    'error_message': qr_data['error']
                })

            return request.render('oudu_wechat_login_qrcode.qr_template', {
                'qr_img': qr_data['qr_img'],
                'session_id': qr_data['session_id']
            })
        except Exception as e:
            _logger.error('QR login page failed: %s', e)
            return request.render('oudu_wechat_login_qrcode.qr_error_template', {
                'error_message': '系统错误，请稍后重试'
            })

    @http.route('/wechat/qr/generate', type='json', auth='public', lang='zh_CN')
    def generate_qr_code(self, **kwargs):
        """生成二维码数据"""
        try:
            # 复用原有的二维码生成逻辑
            session_id = request.env['wechat.qr.session'].sudo().create_session()

            # 获取微信配置
            config = request.env['wechat.sso.config'].sudo().get_active_config()
            if not config:
                return {'error': '微信登录未配置'}

            # 生成微信登录URL
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            redirect_uri = quote(f"{base_url}/wechat/qr/callback")
            wechat_url = (
                f"https://open.weixin.qq.com/connect/qrconnect"
                f"?appid={config.app_id}"
                f"&redirect_uri={redirect_uri}"
                f"&response_type=code"
                f"&scope=snsapi_login"
                f"&state=qr_{session_id}"
                f"#wechat_redirect"
            )

            # 生成二维码图片
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(wechat_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            qr_img_base64 = base64.b64encode(buffered.getvalue()).decode()

            return {
                'session_id': session_id,
                'qr_img': qr_img_base64,
                'wechat_url': wechat_url
            }

        except Exception as e:
            _logger.error('QR code generation failed: %s', e)
            return {'error': str(e)}

    @http.route('/wechat/qr/callback', type='http', auth='public', lang='zh_CN')
    def wechat_qr_callback(self, **kwargs):
        """微信回调处理"""
        code = kwargs.get('code')
        state = kwargs.get('state')

        if not code or not state:
            return Response('Invalid request parameters')

        # 提取会话ID
        if not state.startswith('qr_'):
            return Response('Invalid state parameter')

        session_id = state[3:]

        try:
            # 复用现有模块的微信认证功能
            config = request.env['wechat.sso.config'].sudo().get_active_config()
            if not config:
                return Response('微信登录未配置')

            # 调用现有模块的微信认证方法
            user_obj = request.env['res.users'].sudo()
            user = user_obj.with_context(wechat_config=config).auth_wechat('wechat', code, kwargs)

            if not user:
                return Response('微信用户认证失败')

            # 更新会话状态
            session = request.env['wechat.qr.session'].sudo().search([('name', '=', session_id)])
            if session:
                session.mark_confirmed(user.id)

            return Response('登录成功！请返回原页面')

        except Exception as e:
            _logger.error('WeChat callback failed: %s', e)
            return Response('微信登录处理异常')

    @http.route('/wechat/qr/status', type='json', auth='public', lang='zh_CN')
    def qr_login_status(self, **kwargs) -> dict:  # 改为使用**kwargs接收所有参数
        """检查登录状态"""
        session_id = kwargs.get('session_id')  # 从kwargs中获取session_id

        if not session_id:
            return {'status': 'error', 'message': '缺少session_id参数'}

        try:
            session = request.env['wechat.qr.session'].sudo().search([
                ('name', '=', session_id)
            ])

            if not session:
                return {'status': 'expired', 'message': '会话不存在'}

            session.check_expired()

            if session.state == 'confirmed' and session.user_id:
                # 直接使用现有模块的登录方法
                request.session.authenticate(request.db, session.user_id.login, 'wechat', login=True)
                return {
                    'status': 'success',
                    'redirect_url': '/web'
                }
            else:
                return {'status': session.state}

        except Exception as e:
            _logger.error('Status check failed: %s', e)
            return {'status': 'error', 'message': str(e)}