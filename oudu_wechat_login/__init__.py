# -*- coding: utf-8 -*-
"""
@Time    : 2025/08/02 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from . import models
from . import controllers

from . import session_store
from odoo import http

# 覆盖 Odoo 的默认会话存储
http.session_store = session_store.global_session_store
