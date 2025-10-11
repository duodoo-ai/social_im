{
    'name': 'AI智能体集成模块 Odoo AI Agent Integration Module',
    "version": "18.0.3.0",
    'category': 'Authentication',
    'price': 100,
    'currency': 'USD',
    'summary': 'Multi-AI Provider Integration with AutoAgent Capabilities',
    'description': """
        Enterprise AI Gateway supporting multiple AI providers (DeepSeek, Alibaba, Baidu, Tencent, ByteDance)
        with tool calling, knowledge retrieval, and workflow automation.
    """,
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ai_gateway_security.xml',
        'security/ir.model.access.csv',
        'data/ai_provider_data.xml',
        'data/cron_data.xml',
        'demo/demo_data.xml',
        'views/ai_provider_views.xml',
        'views/ai_agent_views.xml',
        'views/ai_tool_views.xml',
        'views/ai_workflow_views.xml',
        'views/ai_provider_balance_views.xml',
        'wizard/ai_tool_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oudu_bot_integration/static/src/js/ai_gateway.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'demo': [],
    "installable": True,
    "application": True,
    "auto_install": False,
    'license': 'LGPL-3',
}