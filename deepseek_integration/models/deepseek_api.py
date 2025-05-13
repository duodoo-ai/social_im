# -*- coding: utf-8 -*-
"""
@Time    : 2025/04/29 15:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
import time
import requests
import logging
from openai import OpenAI
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)

class DeepseekAPI(models.AbstractModel):
    _name = 'deepseek.api'
    _description = 'Deepseek API Handler'

    def _get_api_key(self):
        return self.env['deepseek.config'].sudo().search([('name', '=', 'deepseek-chat')]).api_key

    def generate_text(self, prompt, max_tokens=500):
        api_key = self._get_api_key()

        client = OpenAI(
            base_url="https://api.deepseek.com/v1/",
            api_key=f"{api_key}",
        )
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        try:
            return completion.choices[0].message.content
        except Exception as e:
            _logger.error("DeepSeek API调用失败: %s", str(e))
            return False
