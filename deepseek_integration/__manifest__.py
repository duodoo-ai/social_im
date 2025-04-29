# -*- coding: utf-8 -*-
{
    'name': "Odoo DeepSeek Integration",

    'summary': """        
        Integration with Deepseek AI Platform
    """,

    'description': """        
        Odoo module for integrating Deepseek AI services
        Features:
        - API Configuration Management
        - Request History Tracking
        - Interactive Chat Interface
        More support：
        18951631470
        zou.jason@qq.com
        """,

    'author': "Jason Zou",
    'website': "-",

    'category': 'LLM',
    'version': '1.0',

    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/deepseek_configuration_views.xml',
        'views/deepseek_request_history_views.xml',
        'views/deepseek_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'deepseek_integration/static/src/js/deepseek_widget.js'
        ]
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "AGPL-3",
}
