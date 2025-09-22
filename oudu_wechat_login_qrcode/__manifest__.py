# -*- coding: utf-8 -*-
{
    'name': '微信扫描二维码登录 Odoo WeChat QRCode Login',
    'version': '18.0.2.0',
    'summary': 'WeChat QRCode Single Sign-On for Odoo',
    'description': """
        This module enables QR code based single sign-on (SSO) for Odoo using WeChat Service Account.
        Users can log in to Odoo by scanning a WeChat QR code.
        
        Features:
        - Beautiful and responsive QR code display
        - Three status states: pending, scanned, expired
        - Countdown timer after successful scan
        - Automatic redirection after login
    """,
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'Authentication',
    'price': 29.99,
    'currency': 'USD',
    'depends': ['base', 'web', 'website', 'auth_oauth', 'oudu_wechat_login'],
    'data': [
        'data/wechat_data.xml',
        'security/ir.model.access.csv',
        'views/qr_session_views.xml',
        'views/web_login.xml',
        'views/qr_templates.xml',
    ],
    'assets': {

    },
    'images': [
        'static/description/icon.png',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}