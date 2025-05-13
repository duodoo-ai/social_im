# -*- coding: utf-8 -*-
"""
@Time    : 2025/04/29 15:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
from odoo import models, fields, exceptions, api
import os
import logging
_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
headers = {'content-type': 'application/json'}


class DeepseekConfig(models.Model):
    _name = 'deepseek.config'
    _description = 'Deepseek API Configuration'

    name = fields.Char(string='Configuration Name', default='deepseek-chat', required=True)
    api_key = fields.Char(string='API Key', required=True)
    api_url = fields.Char(
        string='API Endpoint',
        default='https://api.deepseek.com/v1/'
    )
    max_tokens = fields.Integer(string='Max Tokens', default=1000)
    temperature = fields.Float(string='Temperature', default=0.7)
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def get_active_config(self):
        return self.search([('active', '=', True)], limit=1)


