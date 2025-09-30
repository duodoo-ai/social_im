# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class DouyinAPI(models.Model):
    _name = 'oudu.douyin.api'
    _description = '抖音API接口'

    @api.model
    def get_user_public_info(self, config, open_id, access_token):
        """
        获取用户公开信息
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

    @api.model
    def get_access_token(self, config, auth_code):
        """使用授权码获取access_token"""
        try:
            url = "https://open.douyin.com/oauth/access_token/"
            data = {
                'client_key': config.client_key,
                'client_secret': config.client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
            }

            response = requests.post(url, data=data, timeout=10)
            result = response.json()

            _logger.info('获取Access Token响应: %s', result)
            return result

        except Exception as e:
            _logger.error('获取Access Token失败: %s', str(e))
            return {
                'data': {
                    'error_code': 'request_failed',
                    'description': str(e)
                },
                'message': 'error'
            }

