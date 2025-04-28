# -*- coding: utf-8 -*-
"""
@Time    : 2025/03/31 15:44
@Author  : Jason Zou
@Email   : zou.jason@qq.com
"""
from odoo import models, fields, exceptions
import os
import logging
_logger = logging.getLogger(__name__)
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
headers = {'content-type': 'application/json'}


class DeepSeekApiKeys(models.Model):
    _name = 'deepseek.api.keys'
    _description = 'DeepSeek API keys'

    name = fields.Char(string='Name', required=True, tracking=True)
    secret = fields.Char(string='API keys', required=True, tracking=True, help='')
    description = fields.Text(string='Deepseek Interface Description', tracking=True)

    # def gen_contacts_access_token(self):
    #     """授权信息，获取企微通讯录Access Token"""
    #     access_obj = self.env['ewi.wechat.config']
    #     access_record = access_obj.search([('name', '=', '企业微信接口')])
    #     _logger.info(f"企业ID --- {access_record.corp_id} --- ")
    #     corp_id = access_record.corp_id
    #     corp_secret = access_record.secret
    #     if not corp_id or not corp_secret:
    #         _logger.info(f"通讯录授权信息 {corp_id}----{corp_secret}为空，请填入！")
    #         return
    #     token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
    #     for line in self:
    #         line.write({'errmsg': False})
    #         try:
    #             ret = requests.get(token_url, headers=headers)
    #             ret.raise_for_status()
    #             result = ret.json()
    #             if result.get('errcode') == 40001:
    #                 _logger.error(f"通讯录访问请求返回结果：{result}")
    #                 return
    #             if result.get('errcode') == 0:
    #                 line.write({'access_token': result['access_token'],
    #                                      'errcode': result['errcode'],
    #                                      'errmsg': result['errmsg'],
    #                                      'expires_in': result['expires_in'],
    #                                      })
    #                 return result['access_token']
    #             else:
    #                 _logger.error(f"获取企微通讯录Access Token失败: {result.get('errmsg')}")
    #                 return None
    #         except requests.RequestException as e:
    #             _logger.error(f"请求获取企微通讯录Access Token时出错: {str(e)}")
    #             return None

