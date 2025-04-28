{
    'name': 'MCP Odoo Base',
    'version': '1.0',
    'category': 'Technical',
    'summary': 'Model Context Protocol for Odoo',
    'description': """
        基于MCP协议的Odoo集成基础模块
        - 支持API密钥管理
        - 提供MCP标准接口
        - 实现基础资源访问
    """,
    'author': 'Yizuo XiaoHai',
    'website': 'https://www.yizuo.ltd',
    'depends': ['base'],
    'data': [
        'security/mcp_security.xml',
        'security/ir.model.access.csv',
        # 'data/ir_config_parameter.xml',
        'views/res_users_views.xml',
        'views/mcp_menus.xml',
        'views/qcc_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "AGPL-3",
} 