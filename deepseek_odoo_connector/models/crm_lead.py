# -*- coding: utf-8 -*-
"""
@Time    : 2025/04/29 16:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
import markdown
from odoo import fields, models, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    markdown_content = fields.Text(string="AI分析报告")
    html_content = fields.Html(string="HTML Content",
                               compute='_compute_html_content',
                               inverse='_inverse_html_content',
                               sanitize=False)

    @api.depends('markdown_content')
    def _compute_html_content(self):
        for record in self:
            record.html_content = markdown.markdown(record.markdown_content or '')

    def _inverse_html_content(self):
        pass

    def action_generate_analysis(self):
        prompt = f"""
        作为销售分析专家，请基于以下线索信息生成结构化报告：
        公司名称：{self.partner_name}
        预计收入：{self.expected_revenue}
        备注：{self.description}
        """
        response = self.env['deepseek.api'].generate_text(prompt)
        if response:
            self.write({'markdown_content': response})
