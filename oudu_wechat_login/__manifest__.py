{
    'name': '微信服务号免登录集成 Odoo WeChat Service Account SSO',
    'version': '18.0.2.0',
    'summary': 'Single Sign-On via WeChat Service Account（微信服务号SSO）',
    'description': """
        This module enables single sign-on (SSO) for Odoo using WeChat Service Account.
        It allows users to log in to Odoo through WeChat by scanning a QR code or via WeChat official account.
    """,
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'Authentication',
    'depends': ['base', 'web', 'auth_oauth'],
    'data': [
        'security/ir.model.access.csv',
        'data/wechat_data.xml',
        'views/res_config_views.xml',
        'views/res_users_views.xml',
    ],
    # 'assets': {
    #     'web.assets_frontend': [
    #
    #     ],
    # },
    'images': [
        'static/description/banner.png',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'post_init_hook': 'post_init_hook',
}