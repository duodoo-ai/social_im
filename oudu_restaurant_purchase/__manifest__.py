{
    'name': '餐厅门店食材及货品采购管理 Odoo Restaurant Ingredients and Purchase Management',
    'version': '18.0.3.0.0',
    'summary': '餐厅门店食材及货品采购管理',
    'description': """
    餐厅门店食材及货品采购管理 Odoo Restaurant Ingredients and Purchase Management
    ================

    特色功能:
    --------
    - 采购管理核心功能：包括采购订单的创建、编辑、删除、状态跟踪等。
    - 多门店支持：能够为不同门店独立管理采购订单。
    - 微信集成功能：支持通过微信小程序或网页端进行采购订单的创建和管理。
    - 商品与数据管理：能够管理采购商品的信息，包括商品名称、规格、单价、库存等。
    - 工作台与界面功能：提供直观的采购订单管理工作台，方便用户查看和操作采购订单。
    - 采购进度实时跟踪：能够实时跟踪采购订单的进度，包括订单状态、采购数量、采购金额等。

    支持流程:
    --------
    1. 主厨下单 → 2. 采购员采购 → 3. 收货确认 → 4. 完成结算
    """,
    'author': 'DuodooTEKr多度科技',
    'phone': '18951631470',
    'email': 'zou.jason@qq.com',
    'website': 'http://www.duodoo.tech',
    'category': 'Purchases',
    'price': 200,
    'currency': 'USD',
    'depends': [
        'purchase',
        'product',
        'mail',
        'web',
        'website',
        'oudu_wechat_message',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'demo/demo.xml',
        'views/restaurant_purchase_views.xml',
        'views/purchase_order_views.xml',
        'views/templates.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oudu_restaurant_purchase/static/src/js/restaurant_purchase.js',
            'oudu_restaurant_purchase/static/src/css/restaurant_purchase.css',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}