# -*- coding: utf-8 -*-
{
    'name': "Odoo金蝶e-sHR集成 Odoo Kingdee e-shr Connector",

    'summary': """        
        Odoo and Kingdee e-shr Organizational Structure, 
        Employee Information Integration
        Odoo与金蝶e-shr组织架构、职工信息集成
    """,

    'description': """        
        Odoo and Kingdee e-shr Organizational Structure, 
        Employee Information Integration
        Odoo与金蝶e-shr组织架构、职工信息集成
        """,
    'version': '18.0.3.0.0',
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'Tools',
    'price': 100.00,
    'currency': 'USD',
    'depends': ['base','hr'],

    'data': [
        'data/eshr_cron.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_position_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "AGPL-3",
}
