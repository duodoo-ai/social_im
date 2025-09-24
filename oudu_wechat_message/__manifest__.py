# -*- coding: utf-8 -*-
{
    "name": "微信服务号模板消息 WeChat Subscription Notification",
    "summary": "提供微信服务号模板消息发送的公共服务",
    "description": """
        该模块提供独立的微信服务号消息发送服务，其他模块可以调用其公共方法发送模板消息。
        包含完整的消息存储、权限控制和运营分析功能。        
    """,
    "version": "18.0.3.0",
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'Authentication',
    'price': 29.99,
    'currency': 'USD',
    "depends": [
        'base',
        'web',
        'website',
        'auth_oauth',
        'oudu_wechat_login'
    ],
    "data": [
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/wechat_message_views.xml',
        'views/wechat_user_message_views.xml',
        'views/templates.xml',
    ],
    "assets": {
        "web.assets_frontend": [
            # 'oudu_wechat_message/static/src/css/style.css',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    'license': 'AGPL-3',
}