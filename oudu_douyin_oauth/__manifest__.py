# -*- coding: utf-8 -*-
{
    'name': '抖音开放平台集成 Odoo Douyin Service Account SSO',
    'version': '18.0.3.0.0',
    'summary': '抖音OAuth2.0登录和API集成',
    'description': """
        OUDU 抖音开放平台集成模块
        ========================

        基于抖音开放平台OpenAPI的完整集成方案：
        - 抖音扫码登录Odoo系统
        - OAuth2.0授权流程管理
        - Token自动刷新机制
        - 用户信息获取和管理
        - 多应用配置支持
    """,
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'Authentication',
    'price': 100,
    'currency': 'USD',
    'depends': [
        'base',
        'web',
        'auth_oauth',
        'base_setup',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/douyin_config.xml',
        'views/douyin_config_views.xml',
        'views/douyin_auth_views.xml',
        'views/res_users_views.xml',
        'views/templates.xml',
        'views/douyin_login.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'assets': {
        'web.assets_backend': [
            'oudu_douyin_oauth/static/src/js/douyin_oauth.js',
            'oudu_douyin_oauth/static/src/css/douyin_oauth.css',
        ],
        'web.assets_frontend': [

        ],
    'web.assets_common': [
            'oudu_douyin_oauth/static/src/css/social_login.css',
            'oudu_douyin_oauth/static/src/js/social_login.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'post_init_hook': 'post_init_hook',  # 添加初始化钩子
}