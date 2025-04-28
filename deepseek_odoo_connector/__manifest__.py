# -*- coding: utf-8 -*-
{
    'name': "Odoo DeepSeek Connector",

    'summary': """        
        Integration of Odoo and DeepSeek AI Large Model
        Odoo与DeepSeek-AI大模型集成
    """,

    'description': """        
        Integration of Odoo and DeepSeek AI Large Model
        Odoo与DeepSeek-AI大模型集成
        More support：
        18951631470
        zou.jason@qq.com
        """,

    'author': "Jason Zou",
    'website': "-",

    'category': 'AI/ai-deepseek',
    'version': '1.0',

    'depends': ['base'],
    'data': [
        'data/deepseek_data.xml',
        'data/deepseek_cron.xml',
        'security/ir.model.access.csv',
        # 'views/hr_department_views.xml',
        'views/deepseek_interface_views.xml',
        'views/deepseek_user_balance_views.xml',
        'views/deepseek_cue_word_views.xml',
        'views/deepseek_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "AGPL-3",
}
