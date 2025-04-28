# -*- coding: utf-8 -*-
"""
@Time    : 2025/04/01 10:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
from odoo import models, fields, exceptions
import os
import logging
import requests
_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
headers = {'content-type': 'application/json'}


class DeepseekCueWord(models.Model):
    _name = 'deepseek.cue.word'
    _description = 'Deepseek Cue Word'

    name = fields.Char(string='模型提示词生成', default='模型提示词生成')
    model = fields.Selection([
        ('deepseek-chat', 'deepseek-chat')
    ], string='Model', default='deepseek-chat', tracking=True)
    role_system = fields.Char(string='Role System')
    content_system = fields.Text(string='Content System')
    role_user = fields.Char(string='Role User')
    content_user = fields.Text(string='Content User')
    description = fields.Text(string='Description')



