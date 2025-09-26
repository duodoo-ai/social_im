# -*- coding: utf-8 -*-

import json
import logging
import requests
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class DouyinClient:
    """抖音开放平台API客户端"""

    def __init__(self, client_key: str, client_secret: str, base_url: str = "https://open.douyin.com"):
        self.client_key = client_key
        self.client_secret = client_secret
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _request(self, endpoint: str, method: str = 'GET',
                 params: Optional[Dict] = None,
                 data: Optional[Dict] = None,
                 headers: Optional[Dict] = None) -> Dict[str, Any]:
        """统一请求方法"""
        url = f"{self.base_url}{endpoint}"

        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        try:
            _logger.info(f"抖音API请求: {method} {url}")

            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=request_headers, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=request_headers, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response.raise_for_status()
            result = response.json()

            _logger.info(f"抖音API响应: {json.dumps(result, ensure_ascii=False)}")

            # 检查抖音API错误码
            if result.get('data', {}).get('error_code'):
                error_code = result['data']['error_code']
                error_msg = result['data'].get('description', '未知错误')
                raise Exception(f"抖音API错误[{error_code}]: {error_msg}")

            return result

        except requests.exceptions.RequestException as e:
            _logger.error(f"抖音API请求异常: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            _logger.error(f"抖音API响应解析失败: {str(e)}")
            raise

    def get_client_token(self) -> Dict[str, Any]:
        """获取client_token"""
        endpoint = '/oauth/client_token/'
        data = {
            'client_key': self.client_key,
            'client_secret': self.client_secret,
            'grant_type': 'client_credential',
        }
        return self._request(endpoint, method='POST', data=data)

    def get_access_token(self, auth_code: str) -> Dict[str, Any]:
        """使用授权码获取access_token"""
        endpoint = '/oauth/access_token/'
        data = {
            'client_key': self.client_key,
            'client_secret': self.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
        }
        return self._request(endpoint, method='POST', data=data)

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新access_token"""
        endpoint = '/oauth/refresh_token/'
        data = {
            'client_key': self.client_key,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
        return self._request(endpoint, method='POST', data=data)

    def get_user_info(self, open_id: str, access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        endpoint = '/oauth/userinfo/'
        params = {
            'open_id': open_id,
            'access_token': access_token,
        }
        return self._request(endpoint, method='GET', params=params)