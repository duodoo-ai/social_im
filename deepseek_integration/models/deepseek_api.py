# -*- coding: utf-8 -*-
"""
@Time    : 2025/04/29 15:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
import requests
import json
import time
from odoo import models, fields, api, _


class DeepseekAPI(models.AbstractModel):
    _name = 'deepseek.api'
    _description = 'Deepseek API Handler'

    def _send_request(self, prompt):
        config = self.env['deepseek.config'].get_active_config()
        if not config:
            raise ValueError("No active Deepseek configuration found")

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        start_time = time.time()
        try:
            response = requests.post(
                config.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            duration = time.time() - start_time

            if response.status_code == 200:
                return self._handle_success(response, duration)
            else:
                return self._handle_error(response, duration)

        except Exception as e:
            return self._handle_exception(e)

    def _handle_success(self, response, duration):
        data = response.json()
        return {
            'status': 'success',
            'response': data['choices'][0]['message']['content'],
            'cost': data.get('usage', {}).get('total_cost', 0),
            'model': data.get('model'),
            'duration': duration
        }

    def _handle_error(self, response, duration):
        error_msg = f"API Error ({response.status_code}): {response.text}"
        return {
            'status': 'failed',
            'response': error_msg,
            'duration': duration
        }

    def _handle_exception(self, exception):
        return {
            'status': 'failed',
            'response': str(exception),
            'duration': 0
        }
