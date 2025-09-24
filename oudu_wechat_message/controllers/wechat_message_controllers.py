# -*- coding: utf-8 -*-
"""
@Time    : 2025/09/23 10:33
@Author  : Jason Zou
@Email   : zou.jason@qq.com
@Mobile  ：18951631470
@Website: http://www.duodoo.tech
"""
from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import AccessError, MissingError, UserError
import logging
from typing import Optional, Dict, Any, List

_logger = logging.getLogger(__name__)


class WechatMessageController(http.Controller):

    @http.route('/wechat/message/redirect/<int:message_id>', type='http', auth='public', website=True)
    def wechat_message_redirect(self, message_id: int, **kw):
        """
        微信消息跳转处理
        用户点击微信消息后跳转到此链接，自动处理登录并重定向到目标页面
        """
        try:
            # 获取消息记录
            message = request.env['wechat.message'].sudo().browse(message_id)
            if not message.exists():
                return request.redirect('/web/login?error=消息不存在')

            # 记录点击行为
            self._log_message_click(message_id, request)

            # 如果用户已登录，直接跳转
            if request.env.user and request.env.user != request.website.user_id:
                return self._redirect_authenticated_user(message, request.env.user)

            # 处理微信自动登录
            wechat_user = self._authenticate_wechat_user(request, kw)
            if wechat_user:
                return self._redirect_authenticated_user(message, wechat_user)

            # 未认证用户跳转到登录页，登录后重定向回此页面
            redirect_url = f"/wechat/message/redirect/{message_id}"
            return request.redirect(f'/web/login?redirect={redirect_url}')

        except Exception as e:
            _logger.error(f"消息跳转处理异常: {str(e)}")
            return request.redirect('/web/login?error=系统异常')

    @http.route('/wechat/message/detail/<int:message_id>', type='http', auth='user', website=True)
    def wechat_message_detail(self, message_id: int, **kw):
        """消息详情页面"""
        try:
            message = request.env['wechat.message'].browse(message_id)

            # 检查用户权限
            if not self._can_user_access_message(request.env.user, message):
                return request.render('oudu_wechat_message.access_denied_template', {
                    'error_message': _('您没有权限查看此消息')
                })

            # 更新消息打开统计
            self._update_message_open_stats(message_id, request.env.user)

            return request.render('oudu_wechat_message.message_detail_template', {
                'message': message,
                'user': request.env.user
            })

        except AccessError:
            return request.render('oudu_wechat_message.access_denied_template', {
                'error_message': _('权限拒绝')
            })
        except Exception as e:
            _logger.error(f"消息详情页异常: {str(e)}")
            return request.render('oudu_wechat_message.error_template', {
                'error_message': _('系统异常')
            })

    @http.route('/wechat/message/list', type='http', auth='user', website=True)
    def wechat_message_list(self, **kw):
        """用户消息列表页面"""
        try:
            # 获取用户有权限查看的消息
            user_messages = self._get_user_accessible_messages(request.env.user)

            return request.render('oudu_wechat_message.message_list_template', {
                'messages': user_messages,
                'user': request.env.user
            })

        except Exception as e:
            _logger.error(f"消息列表页异常: {str(e)}")
            return request.render('oudu_wechat_message.error_template', {
                'error_message': _('系统异常')
            })

    def _log_message_click(self, message_id: int, request) -> None:
        """记录消息点击行为"""
        try:
            # 查找对应的用户消息记录
            user_message = request.env['wechat.user.message'].sudo().search([
                ('wechat_message_id', '=', message_id),
                ('user_id.wechat_openid', '=', request.params.get('openid'))
            ], limit=1)

            if user_message:
                user_message.mark_as_clicked()

                # 更新总点击次数
                message = request.env['wechat.message'].sudo().browse(message_id)
                message.write({'open_count': message.open_count + 1})

        except Exception as e:
            _logger.error(f"记录点击行为失败: {str(e)}")

    def _authenticate_wechat_user(self, request, params) -> Optional[Any]:
        """微信用户认证"""
        try:
            # 检查是否有微信认证参数
            code = params.get('code')
            state = params.get('state')

            if code and state == 'wechat_message':
                # 使用oudu_wechat_login模块的认证逻辑
                user_obj = request.env['res.users'].sudo()
                user = user_obj.auth_wechat('wechat', code, params)

                if user:
                    # 登录用户
                    request.session.authenticate(request.db, user.login, 'wechat')
                    return user

        except Exception as e:
            _logger.error(f"微信用户认证失败: {str(e)}")

        return None

    def _redirect_authenticated_user(self, message, user) -> Response:
        """重定向已认证用户"""
        try:
            # 优先使用自定义跳转链接
            if message.redirect_url:
                return request.redirect(message.redirect_url)

            # 其次使用模型关联跳转
            if message.redirect_model and message.redirect_res_id:
                # 这里可以根据具体模型生成对应的详情页链接
                redirect_url = f"/web#id={message.redirect_res_id}&model={message.redirect_model}&view_type=form"
                return request.redirect(redirect_url)

            # 默认跳转到消息详情页
            return request.redirect(f'/wechat/message/detail/{message.id}')

        except Exception as e:
            _logger.error(f"重定向用户失败: {str(e)}")
            return request.redirect('/web')

    def _can_user_access_message(self, user, message) -> bool:
        """检查用户是否有权限访问消息"""
        # 用户只能查看自己接收到的消息
        user_message = request.env['wechat.user.message'].search([
            ('wechat_message_id', '=', message.id),
            ('user_id', '=', user.id)
        ], limit=1)

        return bool(user_message)

    def _get_user_accessible_messages(self, user) -> List[Any]:
        """获取用户可访问的消息列表"""
        user_messages = request.env['wechat.user.message'].search([
            ('user_id', '=', user.id)
        ])

        return user_messages.mapped('wechat_message_id')

    def _update_message_open_stats(self, message_id: int, user) -> None:
        """更新消息打开统计"""
        try:
            user_message = request.env['wechat.user.message'].search([
                ('wechat_message_id', '=', message_id),
                ('user_id', '=', user.id)
            ], limit=1)

            if user_message and user_message.state != 'clicked':
                user_message.mark_as_clicked()

        except Exception as e:
            _logger.error(f"更新消息统计失败: {str(e)}")