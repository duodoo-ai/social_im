# -*- coding: utf-8 -*-

from . import douyin_config
from . import douyin_auth
from . import res_users
# from . import douyin_api

import logging
_logger = logging.getLogger(__name__)


# 模块安装时的初始化
def post_init_hook(cr, registry):
    """模块安装后初始化默认配置"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['oudu.douyin.config'].create_default_config()

    _logger = logging.getLogger(__name__)
    _logger.info("抖音开放平台模块初始化完成")