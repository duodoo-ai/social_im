# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class DouyinMainController(http.Controller):
    """抖音主控制器，提供一些辅助功能"""

    @http.route('/douyin/auth/get_config', type='json', auth='public')
    def get_douyin_config(self, **kwargs):
        """获取抖音配置（前端调用）"""
        config = request.env['oudu.douyin.config'].search([('active', '=', True)], limit=1)
        if config:
            return {
                'client_key': config.client_key,
                'auth_url': config.get_auth_url(),
                'scope': config.scope,
            }
        return {}

    @http.route('/douyin/api/userinfo', type='json', auth='user')
    def get_user_info_api(self, **kwargs):
        """API接口：获取用户信息"""
        auth_id = kwargs.get('auth_id')
        if not auth_id:
            return {'error': '缺少auth_id参数'}

        auth_record = request.env['oudu.douyin.auth'].browse(auth_id)
        if auth_record.user_id != request.env.user:
            return {'error': '无权访问此记录'}

        try:
            user_info = auth_record.get_user_info()
            return {'success': True, 'data': user_info}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/douyin/api/mobile', type='json', auth='user')
    def get_user_mobile_api(self, **kwargs):
        """API接口：获取用户手机号"""
        auth_id = kwargs.get('auth_id')
        if not auth_id:
            return {'error': '缺少auth_id参数'}

        auth_record = request.env['oudu.douyin.auth'].browse(auth_id)
        if auth_record.user_id != request.env.user:
            return {'error': '无权访问此记录'}

        try:
            mobile_info = auth_record.get_user_mobile()
            return {'success': True, 'data': mobile_info}
        except Exception as e:
            return {'error': str(e)}