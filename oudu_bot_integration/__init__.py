from . import models
from . import controllers
from . import wizard


# def post_init_hook(cr):
#     """Post initialization hook"""
#     from odoo import api, SUPERUSER_ID
#
#     env = api.Environment(cr, SUPERUSER_ID, {})
#
#     # 初始化提供商的高级配置
#     env['oudu.bot.provider'].init_provider_configs()
#
#
# def uninstall_hook(cr, registry):
#     """Uninstall hook"""
#     pass