# -*- coding: utf-8 -*-
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

    def _make_request(self, endpoint, method='POST', data=None, headers=None):
        """统一的API请求方法"""
        try:
            # 抖音API基础地址
            base_url = 'https://open.douyin.com'
            url = f"{base_url}{endpoint}"

            # 默认headers
            default_headers = {
                'Content-Type': 'application/json',
            }

            if headers:
                default_headers.update(headers)

            _logger.info('抖音API请求: %s %s, 数据: %s', method, url, data)

            timeout = 30

            if method.upper() == 'GET':
                response = requests.get(url, params=data, headers=default_headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=timeout)
            else:
                raise UserError(_('不支持的HTTP方法: %s') % method)

            response.raise_for_status()
            result = response.json()

            _logger.info('抖音API响应: %s', json.dumps(result, ensure_ascii=False))

            # 检查抖音API错误码
            if result.get('data', {}).get('error_code'):
                error_code = result['data']['error_code']
                error_msg = result['data'].get('description', '未知错误')
                raise UserError(_('抖音API错误[%s]: %s') % (error_code, error_msg))

            return result

        except requests.exceptions.RequestException as e:
            _logger.error('抖音API请求异常: %s', str(e))
            raise UserError(_('网络请求异常: %s') % str(e))
        except Exception as e:
            _logger.exception('抖音API未知异常')
            raise UserError(_('系统异常: %s') % str(e))

    def get_access_token(self, config, auth_code):
        """使用授权码获取access_token"""
        endpoint = '/oauth/access_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
        }
        return self._make_request(endpoint, method='POST', data=data)

    def refresh_access_token(self, config, refresh_token):
        """刷新access_token"""
        endpoint = '/oauth/refresh_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        return self._make_request(endpoint, method='POST', data=data)

    def get_client_token(self, config):
        """获取client_token"""
        endpoint = '/oauth/client_token/'
        data = {
            'client_key': config.client_key,
            'client_secret': config.client_secret,
            'grant_type': 'client_credential',
        }
        return self._make_request(endpoint, method='POST', data=data)

    def get_user_public_info(self, config, open_id, access_token):
        """
        获取用户公开信息
        文档: https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/get-account-open-info

        Args:
            config: 抖音配置对象
            open_id: 用户唯一标识
            access_token: 访问令牌

        Returns:
            dict: 用户公开信息
        """
        try:
            _logger.info('开始获取用户公开信息: open_id=%s', open_id)

            # 构建请求URL
            url = "https://open.douyin.com/api/douyin/v1/user/user_info/"

            # 构建请求参数
            params = {
                'open_id': open_id,
                'access_token': access_token
            }

            _logger.info('抖音用户公开信息API请求: GET %s, 参数: %s', url, params)

            # 发送GET请求
            response = requests.get(
                url,
                params=params,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=10
            )

            _logger.info('抖音用户公开信息API响应状态: %s', response.status_code)
            _logger.info('抖音用户公开信息API响应内容: %s', response.text)

            if response.status_code != 200:
                _logger.error('抖音用户公开信息API请求失败: %s', response.status_code)
                return {
                    'data': {
                        'error_code': response.status_code,
                        'description': f'HTTP请求失败: {response.status_code}'
                    },
                    'message': 'error'
                }

            result = response.json()

            # 检查API返回的错误码
            if result.get('data', {}).get('error_code') != 0:
                error_code = result.get('data', {}).get('error_code')
                error_msg = result.get('data', {}).get('description', '未知错误')
                _logger.error('抖音用户公开信息API业务错误: %s - %s', error_code, error_msg)

            return result

        except requests.exceptions.Timeout:
            _logger.error('获取用户公开信息请求超时')
            return {
                'data': {
                    'error_code': 'timeout',
                    'description': '请求超时'
                },
                'message': 'error'
            }
        except requests.exceptions.ConnectionError:
            _logger.error('获取用户公开信息连接错误')
            return {
                'data': {
                    'error_code': 'connection_error',
                    'description': '网络连接错误'
                },
                'message': 'error'
            }
        except Exception as e:
            _logger.exception('获取用户公开信息异常: %s', str(e))
            return {
                'data': {
                    'error_code': 'system_error',
                    'description': f'系统异常: {str(e)}'
                },
                'message': 'error'
            }