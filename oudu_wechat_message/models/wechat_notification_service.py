# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
import logging
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class WechatNotificationService(models.Model):
    _name = 'wechat.notification.service'
    _description = '微信通知服务'

    @api.model
    def send_wechat_message(self, message_record):
        """发送微信消息的核心方法"""
        try:
            if not message_record or message_record._name != 'wechat.message':
                _logger.error("无效的消息记录")
                return False

            wechat_config = message_record.wechat_config_id
            if not wechat_config:
                _logger.error("未找到有效的微信配置")
                return False

            access_token = wechat_config.get_wechat_access_token()
            if not access_token:
                _logger.error("获取微信access_token失败")
                return False

            target_users = self._get_target_users()
            if not target_users:
                _logger.warning("没有找到目标用户")
                return False

            success_count = self._send_batch_messages(access_token, message_record, target_users)

            message_record.write({
                'state': 'sent',
                'actual_send_time': fields.Datetime.now(),
                'sent_count': success_count,
                'failed_count': len(target_users) - success_count
            })

            _logger.info(f"微信消息发送完成: {message_record.message_sequence}, 成功: {success_count}")
            return True

        except Exception as e:
            _logger.error(f"发送微信消息失败: {str(e)}")
            if message_record:
                message_record.write({'state': 'failed', 'error_message': str(e)})
            return False

    @api.model
    def create_and_send_message(self, message_vals):
        """创建并发送微信消息"""
        try:
            required_fields = ['report_title', 'report_type', 'report_target', 'report_content']
            if any(field not in message_vals for field in required_fields):
                _logger.error("缺少必要字段")
                return False, None

            default_vals = {
                'report_time': fields.Datetime.now(),
                'message_type': 'purchase_notification',
                'state': 'draft',
            }
            message_record = self.env['wechat.message'].create({**default_vals, **message_vals})
            success = self.send_wechat_message(message_record)
            return success, message_record.id if success else None

        except Exception as e:
            _logger.error(f"创建并发送消息失败: {str(e)}")
            return False, None

    @api.model
    def send_quick_notification(self, title, content, message_type='采购通知',
                                target='全体用户', redirect_url=None):
        """快速发送通知"""
        message_vals = {
            'report_title': title,
            'report_type': message_type,
            'report_target': target,
            'report_content': content,
            'redirect_url': redirect_url,
        }
        success, _ = self.create_and_send_message(message_vals)
        return success

    def _prepare_template_data(self, message_record):
        """准备模板消息数据"""
        redirect_url = message_record._prepare_redirect_url()
        base_url = self.get_base_url()
        full_url = f"{base_url}{redirect_url}" if '/wechat/message/redirect/' in redirect_url else redirect_url

        return {
            'thing16': {'value': self._truncate_content(message_record.report_title, 20)},  # 项目名称
            # 'const17': {'value': self._truncate_content(message_record.report_type, 20)},  # 订单状态
            'thing6': {'value': self._truncate_content(message_record.report_target, 20)},  # 交货地址
            'time13': {'value': self._format_report_time(message_record.report_time)},  # 截止日期
            'url': full_url
        }

    def _send_batch_messages(self, access_token, message_record, users):
        """批量发送消息"""
        template_data = self._prepare_template_data(message_record)
        success_count = 0

        for user in users:
            try:
                result = self._send_single_message(access_token, template_data, user.wechat_openid)
                if result.get('errcode') == 0:
                    success_count += 1
                    self._create_user_message_record(user, message_record, 'sent', result.get('msgid'))
                else:
                    self._create_user_message_record(user, message_record, 'failed',
                                                     error_message=result.get('errmsg'))
            except Exception as e:
                self._create_user_message_record(user, message_record, 'failed', error_message=str(e))

        return success_count

    def _send_single_message(self, access_token, template_data, openid):
        """发送单条消息到微信API"""
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
            template_id = self._get_template_id()
            message_data = self._build_wechat_message_data(openid, template_id, template_data)

            response = requests.post(url, json=message_data, timeout=10)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            _logger.error(f"发送微信消息异常: {str(e)}")
            return {'errcode': -1, 'errmsg': str(e)}

    def _build_wechat_message_data(self, openid, template_id, template_data):
        """构建微信消息数据"""
        return {
            "touser": openid,
            "template_id": template_id,
            "url": template_data.get('url', ''),
            "data": {
                key: {"value": template_data[key]['value']}
                for key in [
                    'thing16',
                    # 'const17',
                    'thing6',
                    'time13'
                    ]
            }
        }

    def _get_target_users(self):
        """获取目标用户列表"""
        return self.env['res.users'].search([
            ('wechat_openid', '!=', False),
            ('active', '=', True),
            # ('wechat_openid', '=', 'o0CMV2NfIVkzQRwX2Jp-xnJiRVQ0'),      # 测试用
        ])

    def _format_report_time(self, report_time):
        """格式化报告时间"""
        if isinstance(report_time, str):
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                try:
                    return datetime.strptime(report_time, fmt).strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    continue
            return report_time
        return report_time.strftime('%Y-%m-%d %H:%M')

    def _truncate_content(self, content, max_length):
        """截断内容"""
        if not content:
            return ""
        content = str(content).strip()
        return content if len(content) <= max_length else content[:max_length] + '...'

    def _get_template_id(self):
        """获取微信模板ID误"""
        # 修复：正确的搜索语法
        template_config = self.env['wechat.sso.config'].sudo().search([
            ('active', '=', True)
        ], limit=1)

        if template_config and template_config.template_id:
            return template_config.template_id

        # 备用方案：从系统参数获取
        return self.env['ir.config_parameter'].sudo().get_param(
            'wechat.message.template_id',
            'XGJp1jOypqrjRrjzok6FLa7KX5clXeRHRFtE3AojdqM'  # 默认模板ID
        )

    def _create_user_message_record(self, user, message_record, state, message_id=None, error_message=None):
        """创建用户消息记录"""
        self.env['wechat.user.message'].create({
            'wechat_message_id': message_record.id,
            'user_id': user.id,
            'state': state,
            'message_id': message_id,
            'error_message': error_message,
            'send_time': fields.Datetime.now()
        })

    @api.model
    def cron_retry_failed_messages(self):
        """定时重试失败的消息"""
        failed_messages = self.env['wechat.message'].search([
            ('state', '=', 'failed'),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=1))
        ])

        for message in failed_messages:
            try:
                self.send_wechat_message(message)
            except Exception as e:
                _logger.error(f"重试消息失败 {message.message_sequence}: {str(e)}")