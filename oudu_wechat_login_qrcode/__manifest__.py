{
    'name': 'Odoo WeChat QR Code Login',
    'version': '18.0.2.0',
    'summary': 'WeChat QR Code Login for Odoo 18',
    'description': """
        Enable WeChat QR code login functionality for Odoo 18.
        Users can scan QR code with personal WeChat to login.
    """,
    'author': 'DuodooTEKr 多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'wechat',
    'price': 29.99,
    'currency': 'USD',
    'depends': ['base', 'web', 'auth_oauth', 'oudu_wechat_login'],
    'data': [
        'security/ir.model.access.csv',
        'data/wechat_data.xml',
        'views/qr_session_views.xml',
        'views/qr_templates.xml',
        'views/web_login.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'oudu_wechat_login_qrcode/static/src/js/*.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}