from odoo import models, fields, api


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    restaurant_order_id = fields.Many2one(
        'restaurant.purchase.order',
        string='关联餐厅订单'
    )

    shop_id = fields.Many2one(
        'restaurant.shop',
        string='门店',
        related='restaurant_order_id.shop_id',
        store=True
    )