# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/25 16:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from . import models
from . import controllers

import logging
_logger = logging.getLogger(__name__)



def post_init_hook(cr, registry):
    """模块安装后初始化"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 创建默认配置
    config_model = env['oudu.douyin.config']
    if not config_model.search([]):
        config_model.create_default_config()

    _logger = logging.getLogger(__name__)
    _logger.info("抖音开放平台模块初始化完成")