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


class DeepseekRequestHistory(models.Model):
    _name = 'deepseek.history'
    _description = 'Deepseek API Request History'
    _order = 'create_date desc'

    config_id = fields.Many2one('deepseek.config', string='Configuration')
    prompt = fields.Text(string='Input Prompt', required=True)
    response = fields.Text(string='API Response')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Status', default='draft')
    cost = fields.Float(string='API Cost')
    model = fields.Char(string='Model Used')
    duration = fields.Float(string='Response Time (s)')

