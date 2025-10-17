from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RestaurantShop(models.Model):
    """餐厅门店模型"""
    _name = 'restaurant.shop'
    _description = '餐厅门店'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='门店名称', required=True, tracking=True)
    code = fields.Char(string='门店编码', required=True, tracking=True)
    address = fields.Text(string='门店地址', tracking=True)
    phone = fields.Char(string='联系电话')
    chef_id = fields.Many2one(
        'res.users',
        string='主厨',
        tracking=True,
        domain="[('groups_id', 'in', [group_restaurant_chef])]"
    )
    assistant_chef_ids = fields.Many2many(
        'res.users',
        'restaurant_shop_assistant_rel',
        'shop_id',
        'user_id',
        string='副厨师',
        domain="[('groups_id', 'in', [group_restaurant_chef])]"
    )
    active = fields.Boolean(string='激活', default=True)

    # 移除采购申请单相关统计字段
    order_count = fields.Integer(
        string='采购单数',
        compute='_compute_order_count'
    )

    total_purchase_amount = fields.Float(
        string='总采购金额',
        compute='_compute_purchase_stats'
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', '门店编码必须唯一!'),
    ]

    def _compute_order_count(self):
        """计算采购订单数量"""
        for shop in self:
            shop.order_count = self.env['restaurant.purchase.order'].search_count([
                ('shop_id', '=', shop.id)
            ])

    def _compute_purchase_stats(self):
        """计算采购统计"""
        for shop in self:
            orders = self.env['restaurant.purchase.order'].search([
                ('shop_id', '=', shop.id),
                ('state', '=', 'done')
            ])
            shop.total_purchase_amount = sum(order.total_amount for order in orders)

    @api.constrains('chef_id')
    def _check_chef_role(self):
        """验证主厨角色"""
        chef_group = self.env.ref('oudu_restaurant_purchase.group_restaurant_chef')
        for shop in self:
            if shop.chef_id and chef_group not in shop.chef_id.groups_id:
                raise ValidationError("主厨必须属于主厨角色组!")