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


class DeepSeekUserBalance(models.Model):
    _name = 'deepseek.user.balance'
    _description = 'Get User Balance'

    name = fields.Char(string='Get User Balance', default='Get User Balance')
    is_available = fields.Boolean(string='Is Available', required=True, tracking=True)
    currency = fields.Char(string='Currency', tracking=True)
    total_balance = fields.Float(string='Total Balance', digits=(18, 2), tracking=True)
    granted_balance = fields.Float(string='Granted Balance', digits=(18, 2), tracking=True)
    topped_up_balance = fields.Float(string='Topped Up Balance', digits=(18, 2), tracking=True)

    def cron_gen_user_balance_from_deepseek(self):
        """授权信息，获取企微通讯录Access Token"""
        balance_obj = self.env['deepseek.user.balance']
        balance_id = balance_obj.search([('name', '=', 'Get User Balance')])
        url = f"https://api.deepseek.com/user/balance"
        payload = {}
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer sk-031b34475d704c96aa8d984f9b439950'
        }
        try:
            ret = requests.request("GET", url, headers=headers, data=payload)
            result = ret.json()
            if balance_id:
                balance_id.write(
                    {
                        'total_balance': result['balance_infos'][0]['total_balance'],
                        'granted_balance': result['balance_infos'][0]['granted_balance'],
                        'topped_up_balance': result['balance_infos'][0]['topped_up_balance'],
                    })
                return
            else:
                _logger.error(f"获取企微通讯录Access Token失败: {result.get('errmsg')}")
                return None
        except requests.RequestException as e:
            _logger.error(f"请求获取企微通讯录Access Token时出错: {str(e)}")
            return None


