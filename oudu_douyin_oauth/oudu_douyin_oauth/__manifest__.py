# -*- coding: utf-8 -*-
{
    'name': '抖音开放平台OAuth2.0集成 Odoo Douyin Service Account SSO',
    'version': '18.0.3.0.0',
    'summary': '抖音开放平台OAuth2.0集成，支持扫码登录、用户信息获取',
    'description': """
        抖音开放平台OAuth2.0集成模块
        ========================
        
        功能特性：
        - 抖音扫码登录Odoo系统
        - 获取用户基本信息
        - 获取用户手机号（需申请权限）
        - Token自动刷新
        - 多配置支持
        - 安全的授权流程，防止CSRF攻击
        - 自动清理过期Token
        
        配置说明：
        1. 在抖音开放平台创建应用
        2. 配置Client Key和Client Secret
        3. 设置回调地址为: https://your-domain.com/douyin/auth/callback
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
        'data/cron_data.xml',
        'views/douyin_config_views.xml',
        'views/res_users_views.xml',
        'views/templates.xml',
        'views/douyin_login.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    # 'assets': {
        # 'web.assets_frontend': [
        #     'oudu_douyin_oauth/static/src/js/social_login.js',
        #     'oudu_douyin_oauth/static/src/js/douyin_qrcode.js',
        # ],
        # 'web.assets_backend': [
        #     'oudu_douyin_oauth/static/src/js/douyin_oauth.js',
        # ],
    # },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}