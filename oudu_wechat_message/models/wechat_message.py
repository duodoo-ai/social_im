# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/23 10:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
from urllib.parse import quote
from datetime import datetime
import pytz

_logger = logging.getLogger(__name__)

# 在类顶部添加新方法
def format_to_eight(dt_str, format_str="%Y年%m月%d日 %H:%M:%S"):
    """统一将UTC时间转换为东8区时间"""
    if not dt_str:
        return ""
    try:
        # 转换为datetime对象（UTC时区）
        utc_dt = fields.Datetime.from_string(dt_str)
        # 设置目标时区（东8区）
        target_tz = pytz.timezone('Asia/Shanghai')
        # 转换时区
        local_dt = utc_dt.astimezone(target_tz)
        # 格式化为字符串
        # 东8区时间
        _logger.debug("东8区时间转换: %s", local_dt.strftime(format_str))
        return local_dt.strftime(format_str)
    except Exception as e:
        _logger.error("东8区时间转换失败: %s", str(e))
        return dt_str  # 出错时返回原始值

class WechatMessage(models.Model):
    _name = 'wechat.message'
    _description = '微信消息记录'
    _order = 'create_date DESC'
    _rec_name = 'message_title'

    # 序列号生成
    message_sequence = fields.Char(
        string='消息编号',
        readonly=True,
        copy=False,
        index=True,
        default=lambda self: _('New')
    )

    # 基础信息字段
    message_title = fields.Char(
        string='消息标题',
        required=True,
        help='消息的标题，如"新增商机通知"'
    )

    message_type = fields.Selection([
        ('system_notification', '系统通知'),
        ('business_report', '业务报告'),
        ('alert_warning', '预警提醒'),
        ('custom_message', '自定义消息')
    ], string='消息类型', required=True, default='system_notification')

    # 五个核心报告字段
    report_title = fields.Char(string='主题名称', required=True, help='单据的报告的主题名称，如"新增商机通知"')
    report_type = fields.Char(string='单据状态', required=True, help='单据的订单状态，如"自主采购"、"报备线索"等')
    report_target = fields.Char(string='交货地址', required=True, help='单据的交货地址，如"中国-北京"')
    report_time = fields.Datetime(string='截止日期', required=True,
                                  default=lambda self: self.format_to_eight(fields.Datetime.now()),
                                  help='单据的截止日期，格式为YYYY-MM-DD HH:MM:SS')
    report_content = fields.Text(string='报告内容',
                                 help='单据的报告的详细内容，如"新增商机名称：XX公司，交货地址：中国-北京，截止日期：2025-09-23 10:00:00"')

    # 跳转配置
    redirect_url = fields.Text(
        string='跳转链接',
        help='用户点击消息后跳转的URL，支持Odoo内部路径或外部链接'
    )

    redirect_model = fields.Char(
        string='关联模型',
        help='关联的Odoo模型名称，用于生成详情页链接'
    )

    redirect_res_id = fields.Integer(
        string='关联记录ID',
        help='关联的Odoo记录ID'
    )

    # 微信配置关联
    wechat_config_id = fields.Many2one(
        'wechat.sso.config',
        string='微信配置',
        required=True,
        default=lambda self: self._get_default_wechat_config()
    )

    # 状态跟踪
    state = fields.Selection([
        ('draft', '草稿'),
        ('sending', '发送中'),
        ('sent', '已发送'),
        ('failed', '发送失败'),
        ('cancelled', '已取消')
    ], string='状态', default='draft', readonly=True, index=True)

    # 发送统计
    total_recipients = fields.Integer(
        string='目标用户数',
        compute='_compute_send_stats',
        store=True
    )

    sent_count = fields.Integer(
        string='成功发送数',
        default=0,
        readonly=True
    )

    failed_count = fields.Integer(
        string='失败发送数',
        default=0,
        readonly=True
    )

    open_count = fields.Integer(
        string='打开次数',
        default=0,
        readonly=True,
        help='用户点击消息查看详情的次数'
    )

    # 时间字段
    scheduled_send_time = fields.Datetime(string='计划发送时间')
    actual_send_time = fields.Datetime(string='实际发送时间', readonly=True)

    # 技术字段
    template_id = fields.Char(string='微信模板ID')
    message_id = fields.Char(string='微信消息ID', readonly=True)
    error_message = fields.Text(string='错误信息', readonly=True)

    # 关联的用户消息记录
    user_message_ids = fields.One2many(
        'wechat.user.message',
        'wechat_message_id',
        string='用户消息记录'
    )

    # 计算字段和方法
    @api.depends('user_message_ids')
    def _compute_send_stats(self):
        """计算发送统计信息"""
        for record in self:
            record.total_recipients = len(record.user_message_ids)
            record.sent_count = len(record.user_message_ids.filtered(lambda m: m.state == 'sent'))
            record.failed_count = len(record.user_message_ids.filtered(lambda m: m.state == 'failed'))

    @api.model
    def _get_default_wechat_config(self):
        """获取默认的微信配置"""
        config_model = self.env['wechat.sso.config']
        config = config_model.get_active_config()
        return config.id if config else None

    # 约束和验证
    @api.constrains('scheduled_send_time')
    def _check_scheduled_time(self):
        """验证计划发送时间"""
        for record in self:
            if record.scheduled_send_time and record.scheduled_send_time < fields.Datetime.now():
                raise ValidationError(_('计划发送时间不能早于当前时间'))

    # 序列号生成逻辑
    @api.model_create_multi
    def create(self, vals_list):
        """创建时生成序列号"""
        for vals in vals_list:
            if vals.get('message_sequence', _('New')) == _('New'):
                vals['message_sequence'] = self.env['ir.sequence'].next_by_code('wechat.message') or _('New')
        return super().create(vals_list)

    def _prepare_redirect_url(self):
        """准备跳转URL - 动态构建微信OAuth授权URL"""
        # 优先使用配置的跳转链接
        if self.redirect_url:
            return self.redirect_url

        # 构建目标路径
        if self.redirect_model and self.redirect_res_id:
            target_path = f"/wechat/message/redirect/{self.id}"
        else:
            # 默认跳转到门户首页
            target_path = "/snatch_hall"

        # 构建微信OAuth授权URL
        return self._build_oauth_url(target_path)

    def _build_oauth_url(self, target_path):
        """构建微信OAuth授权URL"""
        try:
            # 获取微信配置
            wechat_config = self.wechat_config_id or self.env['wechat.sso.config'].sudo().search(
                [('active', '=', True)], limit=1)
            if not wechat_config or not wechat_config.app_id:
                _logger.error("未找到有效的微信配置或缺少app_id")
                return f"{self.get_base_url()}{target_path}"

            app_id = wechat_config.app_id
            base_url = self.get_base_url()

            # 构建回调URL
            callback_url = f"{base_url}/wechat/callback"
            encoded_callback_url = quote(callback_url, safe='')

            # 构建state参数，包含目标路径
            state = f"redirect_{self.id}_{quote(target_path, safe='')}"

            # 构建OAuth授权URL
            oauth_url = (
                f"https://open.weixin.qq.com/connect/oauth2/authorize?"
                f"appid={app_id}&"
                f"redirect_uri={encoded_callback_url}&"
                f"response_type=code&"
                f"scope=snsapi_userinfo&"
                f"state={state}&"
                f"forcePopup=true"
                f"#wechat_redirect"
            )

            return oauth_url
        except Exception as e:
            _logger.error(f"构建OAuth授权URL失败: {str(e)}")
            # 失败时返回普通URL
            return f"{self.get_base_url()}{target_path}"

    def action_send_message(self):
        """发送微信消息 - 手动发送入口"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('只能发送草稿状态的消息'))

            try:
                # 通过服务类发送消息
                notification_service = self.env['wechat.notification.service']
                success = notification_service.send_wechat_message(record)

                if success:
                    _logger.info(f"微信消息发送完成: {record.message_sequence}")
                else:
                    record.write({
                        'state': 'failed',
                        'error_message': _('发送服务返回失败')
                    })
                    return False

            except Exception as e:
                _logger.error(f"发送微信消息失败: {str(e)}")
                record.write({
                    'state': 'failed',
                    'error_message': str(e)
                })
                return False

        return True

    def action_view_user_messages(self):
        """查看用户消息记录"""
        return {
            'name': _('用户消息记录'),
            'type': 'ir.actions.act_window',
            'res_model': 'wechat.user.message',
            'view_mode': 'list,form',
            'domain': [('wechat_message_id', '=', self.id)],
            'context': {'default_wechat_message_id': self.id}
        }

    def action_preview_message(self):
        """预览消息内容"""
        return {
            'name': _('消息预览'),
            'type': 'ir.actions.act_window',
            'res_model': 'wechat.message',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'flags': {'mode': 'preview'}
        }