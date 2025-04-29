# -*- coding: utf-8 -*-
"""
@Time    : 2025/04/29 16:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    deepseek_widget_field = fields.Text(string='Deepseek Widget Field',
                                        help="输入问题后点击右侧按钮获取AI响应",
                                        store=False,
                                        compute="_compute_dummy_field",
                                        inverse="_inverse_dummy_field")

    def _compute_dummy_field(self):
        """ 保持字段可编辑的技术性计算字段 """
        for record in self:
            record.deepseek_temp_input = False

    def _inverse_dummy_field(self):
        """ 接收前端输入但不实际存储 """
        pass

