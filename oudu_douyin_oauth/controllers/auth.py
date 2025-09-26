# -*- coding: utf-8 -*-

import logging
import json
import werkzeug
from datetime import datetime
from urllib.parse import urlencode

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DouyinAuthController(http.Controller):
    """抖音认证控制器"""

    @http.route('/douyin/auth/login', type='http', auth='public', website=True)
    def douyin_login(self, **kwargs):
        """抖音登录入口，生成授权URL并重定向"""
        config = request.env['oudu.douyin.config'].search([('active', '=', True)], limit=1)
        if not config:
            return request.render('oudu_douyin_oauth.douyin_config_missing')

        state = request.session.get('douyin_auth_state', 'oudu_douyin_auth')
        auth_url = config.get_auth_url(state=state)
        return werkzeug.utils.redirect(auth_url)

    @http.route('/douyin/auth/qrcode/login', type='http', auth='public', website=True)
    def douyin_qrcode_login(self, **kwargs):
        """抖音扫码登录页面"""
        # 使用get_default_config方法获取配置
        config = request.env['oudu.douyin.config'].sudo().get_default_config()
        if not config:
            return request.render('oudu_douyin_oauth.douyin_config_missing')

        # 生成唯一state参数
        import random
        import string
        state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        request.session['douyin_auth_state'] = state

        auth_url = config.get_auth_url(state=state)

        config_data = {
            'auth_url': auth_url,
            'client_key': config.client_key,
            'scope': config.scope,
            'redirect_uri': config.redirect_uri,
            'state': state,
        }

        return request.render('oudu_douyin_oauth.douyin_qrcode_login_enhanced', {
            'douyin_config': json.dumps(config_data),
        })

    @http.route('/douyin/auth/check_status', type='json', auth='public')
    def check_login_status(self, state=None, **kwargs):
        """检查扫码登录状态"""
        try:
            if not state:
                return {'status': 'error', 'message': '缺少状态参数'}

            # 检查是否有对应的授权记录
            auth_record = request.env['oudu.douyin.auth'].search([
                ('state', '=', state),
                ('status', '=', 'active')
            ], limit=1)

            if auth_record:
                # 登录成功，创建用户会话
                user = auth_record.user_id
                if user:
                    # 设置用户会话
                    request.session.uid = user.id
                    request.env.user = user
                    return {
                        'status': 'success',
                        'user_id': user.id,
                        'user_name': user.name
                    }

            # 检查state是否超时（超过10分钟）
            session_state = request.session.get('douyin_auth_state')
            if state != session_state:
                return {'status': 'invalid', 'message': '无效的状态参数'}

            return {'status': 'waiting', 'message': '等待扫码'}

        except Exception as e:
            _logger.error('检查登录状态失败: %s', str(e))
            return {'status': 'error', 'message': str(e)}

    @http.route('/douyin/auth/callback', type='http', auth='public', website=True, csrf=False)
    def douyin_callback(self, **kwargs):
        """抖音授权回调处理"""
        try:
            code = kwargs.get('code')
            state = kwargs.get('state')
            error = kwargs.get('error')

            if error:
                _logger.error('抖音授权回调错误: %s', error)
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': error,
                    'error_description': kwargs.get('error_description', '未知错误')
                })

            if not code:
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': 'missing_code',
                    'error_description': '授权码缺失'
                })

            config = request.env['oudu.douyin.config'].search([('active', '=', True)], limit=1)
            if not config:
                return request.render('oudu_douyin_oauth.douyin_config_missing')

            # 验证state参数
            session_state = request.session.get('douyin_auth_state')
            if state != session_state:
                _logger.warning('State参数不匹配: session=%s, callback=%s', session_state, state)
                # 不直接返回错误，继续处理，但记录警告

            # 获取access_token
            DouyinAPI = request.env['oudu.douyin.api']
            token_result = DouyinAPI.get_access_token(config, code)

            if not token_result.get('data'):
                error_data = token_result.get('data', {})
                error_code = error_data.get('error_code', 'unknown')
                error_msg = error_data.get('description', '获取Access Token失败')
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': error_code,
                    'error_description': error_msg
                })

            token_data = token_result['data']
            open_id = token_data.get('open_id')
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in')

            if not open_id or not access_token:
                return request.render('oudu_douyin_oauth.douyin_auth_error', {
                    'error': 'invalid_token',
                    'error_description': 'Token数据不完整'
                })

            # 查找或创建授权记录
            auth_record = request.env['oudu.douyin.auth'].search([
                ('open_id', '=', open_id),
                ('config_id', '=', config.id)
            ], limit=1)

            # 计算过期时间
            from datetime import timedelta
            expires_time = datetime.now() + timedelta(seconds=expires_in)

            auth_vals = {
                'config_id': config.id,
                'open_id': open_id,
                'union_id': token_data.get('union_id'),
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'token_expires': expires_time,
                'scope': token_data.get('scope'),
                'state': state,  # 保存state参数用于状态检查
                'auth_time': datetime.now(),
                'status': 'active',
            }

            if auth_record:
                auth_record.write(auth_vals)
            else:
                auth_vals['code'] = request.env['oudu.douyin.auth']._generate_code()
                auth_record = request.env['oudu.douyin.auth'].create(auth_vals)

            # 获取用户信息
            try:
                user_info = DouyinAPI.get_user_info(config, open_id, access_token)
                if user_info.get('data'):
                    user_data = user_info['data']
                    auth_record.write({
                        'nickname': user_data.get('nickname'),
                        'avatar': user_data.get('avatar'),
                        'gender': str(user_data.get('gender', '0')),
                        'country': user_data.get('country'),
                        'province': user_data.get('province'),
                        'city': user_data.get('city'),
                    })
            except Exception as e:
                _logger.warning('获取用户信息失败: %s', str(e))

            # 关联用户
            user = request.env.user
            if user and user._is_public():
                # 如果当前是公共用户，则创建或查找用户并登录
                user = request.env['res.users'].douyin_auth({
                    'open_id': open_id,
                    'union_id': token_data.get('union_id'),
                    'nickname': auth_record.nickname,
                    'avatar': auth_record.avatar,
                })
                if user:
                    # 设置用户会话
                    request.session.uid = user.id
                    request.env.user = user
                    auth_record.write({'user_id': user.id})

                    # 重定向到成功页面
                    return request.redirect('/douyin/auth/success')
            else:
                # 已登录用户，直接关联
                auth_record.write({'user_id': user.id})
                return request.redirect('/douyin/auth/success')

            # 如果是扫码登录流程，返回成功但暂不重定向
            return request.redirect('/web')

        except Exception as e:
            _logger.exception('抖音回调处理异常')
            return request.render('oudu_douyin_oauth.douyin_auth_error', {
                'error': 'exception',
                'error_description': str(e)
            })

    @http.route('/douyin/auth/success', type='http', auth='user', website=True)
    def douyin_success(self, **kwargs):
        """授权成功页面"""
        return request.render('oudu_douyin_oauth.douyin_auth_success')

    @http.route('/douyin/auth/error', type='http', auth='public', website=True)
    def douyin_error(self, **kwargs):
        """授权错误页面"""
        return request.render('oudu_douyin_oauth.douyin_auth_error', {
            'error': kwargs.get('error', 'unknown'),
            'error_description': kwargs.get('error_description', '未知错误')
        })

    @http.route('/douyin/auth/status', type='json', auth='user')
    def get_auth_status(self, **kwargs):
        """获取当前用户的授权状态"""
        auth_records = request.env['oudu.douyin.auth'].search([
            ('user_id', '=', request.env.user.id)
        ])
        return {
            'connected': len(auth_records) > 0,
            'records': [{
                'nickname': record.nickname,
                'avatar': record.avatar,
                'status': record.status,
            } for record in auth_records]
        }