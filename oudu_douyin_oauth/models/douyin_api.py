# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/25 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
import json
import logging
import requests
from urllib.parse import urlencode
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DouyinAPI(models.AbstractModel):
    """抖音开放平台API封装"""
    _name = 'oudu.douyin.api'
    _description = '抖音API接口'

    def _make_request(self, config, endpoint, method='GET', params=None, data=None, headers=None):
        """统一的API请求方法"""
        try:
            url = f"{config.api_base_url}{endpoint}"

            # 默认headers
            default_headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }

            if headers:
                default_headers.update(headers)

            _logger.info('抖音API请求: %s %s', method, url)

            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=default_headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            else:
                raise UserError(_('不支持的HTTP方法: %s') % method)

            response.raise_for_status()
            result = response.json()

            _logger.info('抖音API响应: %s', json.dumps(result, ensure_ascii=False))

            # 检查错误码
            if result.get('data', {}).get('error_code'):
                error_code = result['data']['error_code']
                error_msg = result['data'].get('description', '未知错误')
                raise UserError(_('抖音API错误[%s]: %s') % (error_code, error_msg))

            return result

        except requests.exceptions.RequestException as e:
            _logger.error('抖音API请求异常: %s', str(e))
            raise UserError(_('网络请求异常: %s') % str(e))
        except json.JSONDecodeError as e:
            _logger.error('抖音API响应解析失败: %s', str(e))
            raise UserError(_('响应数据解析失败: %s') % str(e))

    def get_client_token(self, config):
        """获取client_token"""
        endpoint = '/oauth/client_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'grant_type': 'client_credential',
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def get_stable_client_token(self, config):
        """获取stable_client_token"""
        endpoint = '/oauth/stable_client_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'grant_type': 'client_credential',
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def get_access_token(self, config, auth_code):
        """使用授权码获取access_token"""
        endpoint = '/oauth/access_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def refresh_access_token(self, config, refresh_token):
        """刷新access_token"""
        endpoint = '/oauth/refresh_token/'
        data = {
            'client_key': config.client_key,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def get_user_info(self, config, open_id, access_token):
        """获取用户公开信息"""
        endpoint = '/oauth/userinfo/'
        params = {
            'open_id': open_id,
            'access_token': access_token,
        }
        return self._make_request(config, endpoint, method='GET', params=params)

    def get_user_mobile(self, config, access_token):
        """获取用户手机号"""
        endpoint = '/api/apps/v2/user/phone/obtain/'
        data = {
            'access_token': access_token,
        }
        headers = {
            'access-token': access_token,
        }
        return self._make_request(config, endpoint, method='POST', data=data, headers=headers)

    def get_enterprise_info(self, config, open_id, access_token):
        """获取用户经营身份信息"""
        endpoint = '/api/enterprise/leads/user/list/'
        data = {
            'open_id': open_id,
            'access_token': access_token,
            'cursor': 0,
            'count': 10,
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def revoke_auth(self, config, open_id, access_token):
        """撤销授权"""
        endpoint = '/oauth/revoke/'
        data = {
            'open_id': open_id,
            'access_token': access_token,
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def get_client_code(self, config, access_token):
        """获取client_code"""
        endpoint = '/oauth/client_code/'
        data = {
            'client_key': config.client_key,
            'access_token': access_token,
            'grant_type': 'client_code',
        }
        return self._make_request(config, endpoint, method='POST', data=data)

    def get_access_code(self, config, client_code):
        """获取access_code"""
        endpoint = '/oauth/access_code/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'client_code': client_code,
            'grant_type': 'access_code',
        }
        return self._make_request(config, endpoint, method='POST', data=data)