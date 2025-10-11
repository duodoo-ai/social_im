# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/26 10:26
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@mobile  : 18951631470
"""
import logging
import pymssql
from .eshr_conn import *
from odoo import fields, models, api
_logger = logging.getLogger(__name__)


class EShrJob(models.Model):
    _inherit = 'hr.job'

    fid = fields.Char(string='e-shr Position FID')   # 职位唯一ID

