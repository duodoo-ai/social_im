# -*- coding: utf-8 -*-
"""
@Time    : 2025/08/02 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
import logging, datetime
from odoo import http, fields, _, api, SUPERUSER_ID
from odoo import tools
from odoo.http import request, Response, root, Session
from odoo.exceptions import AccessDenied, UserError
from odoo.modules.registry import Registry
from odoo.tools import config

_logger = logging.getLogger(__name__)

class CorsMiddleware(object):
    """全局 CORS 中间件"""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # 处理 OPTIONS 预检请求
        if environ['REQUEST_METHOD'] == 'OPTIONS':
            start_response('200 OK', [
                ('Content-Type', 'text/plain'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Origin, Content-Type, Accept, Authorization, X-Requested-With'),
                ('Access-Control-Allow-Credentials', 'true'),
                ('Access-Control-Max-Age', '86400'),
                ('Content-Length', '0')
            ])
            return [b'']

        # 处理实际请求
        def custom_start_response(status, headers, exc_info=None):
            # 添加 CORS 头
            headers.append(('Access-Control-Allow-Origin', '*'))
            headers.append(('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'))
            headers.append(
                ('Access-Control-Allow-Headers', 'Origin, Content-Type, Accept, Authorization, X-Requested-With'))
            headers.append(('Access-Control-Allow-Credentials', 'true'))
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)


# 在 Odoo 应用初始化时添加中间件
root = CorsMiddleware(root)


