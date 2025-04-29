# -*- coding: utf-8 -*-
{
    'name': "Odoo DeepSeek Connector",

    'summary': """        
        Integration of Odoo and DeepSeek AI Large Model Connector
    """,

    'description': """        
        Integration of Odoo and DeepSeek AI Large Model Connector
        More support：
        18951631470
        zou.jason@qq.com
        """,

    'author': "Jason Zou",
    'website': "-",

    'category': 'LLM',
    'version': '1.0',

    'depends': ['base', 'web', 'crm'],
    'data': [
        # 'data/deepseek_data.xml',
        # 'data/deepseek_cron.xml',
        # 'security/ir.model.access.csv',
        # 'views/hr_department_views.xml',
        # 'views/deepseek_interface_views.xml',
        # 'views/deepseek_user_balance_views.xml',
        'views/crm_lead_views.xml',
        # 'views/deepseek_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "AGPL-3",
}
