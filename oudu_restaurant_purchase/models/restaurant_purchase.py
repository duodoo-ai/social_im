# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class RestaurantPurchaseOrder(models.Model):
    _name = 'restaurant.purchase.order'
    _description = '餐厅采购订单'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date DESC'

    name = fields.Char(
        string='订单编号',
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )

    shop_id = fields.Many2one(
        'restaurant.shop',
        string='门店',
        required=True,
        tracking=True
    )

    chef_id = fields.Many2one(
        'res.users',
        string='下单主厨',
        required=True,
        tracking=True
    )

    order_date = fields.Date(
        string='下单日期',
        default=fields.Date.context_today,
        required=True
    )

    delivery_date = fields.Date(
        string='需求日期',
        required=True,
        default=fields.Date.context_today
    )

    state = fields.Selection([
        ('draft', '草稿'),
        ('chef_submitted', '主厨提交'),
        ('purchasing', '采购中'),
        ('received', '已收货'),
        ('done', '完成')
    ], string='状态', default='draft', tracking=True)

    line_ids = fields.One2many(
        'restaurant.purchase.order.line',
        'order_id',
        string='采购明细'
    )

    purchaser_id = fields.Many2one(
        'res.users',
        string='采购员',
        tracking=True
    )

    receiver_id = fields.Many2one(
        'res.users',
        string='收货人',
        tracking=True
    )

    total_amount = fields.Float(
        string='总金额',
        compute='_compute_total_amount',
        store=True
    )

    notes = fields.Text(string='备注')

    # 统计字段
    product_count = fields.Integer(
        string='商品数量',
        compute='_compute_product_count'
    )

    purchased_count = fields.Integer(
        string='已采购数量',
        compute='_compute_purchased_count'
    )

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.line_ids)

    @api.depends('line_ids')
    def _compute_product_count(self):
        for order in self:
            order.product_count = len(order.line_ids)

    @api.depends('line_ids.is_purchased')
    def _compute_purchased_count(self):
        for order in self:
            order.purchased_count = len(order.line_ids.filtered(lambda l: l.is_purchased))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.purchase.order') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        """主厨提交订单"""
        for order in self:
            if order.state != 'draft':
                raise UserError(_('只能提交草稿状态的订单'))
            order.write({'state': 'chef_submitted'})

            # 发送微信通知给采购员
            self._send_wechat_notification(order)

    def action_start_purchasing(self):
        """开始采购"""
        for order in self:
            if order.state != 'chef_submitted':
                raise UserError(_('只能对已提交的订单开始采购'))
            order.write({
                'state': 'purchasing',
                'purchaser_id': self.env.user.id
            })

    def action_receive(self):
        """收货确认"""
        for order in self:
            if order.state != 'purchasing':
                raise UserError(_('只能对采购中的订单进行收货'))
            order.write({
                'state': 'received',
                'receiver_id': self.env.user.id
            })

    def action_done(self):
        """完成订单"""
        for order in self:
            if order.state != 'received':
                raise UserError(_('只能对已收货的订单完成'))
            order.write({'state': 'done'})

    def action_reset_draft(self):
        """重置为草稿"""
        for order in self:
            if order.state not in ['chef_submitted', 'purchasing']:
                raise UserError(_('当前状态不能重置'))
            order.write({'state': 'draft'})

    def _send_wechat_notification(self, order):
        """发送微信通知"""
        try:
            wechat_service = self.env['wechat.notification.service']

            message_content = f"""
门店：{order.shop_id.name}
下单主厨：{order.chef_id.name}
需求日期：{order.delivery_date}
商品数量：{order.product_count}种
请及时处理采购需求。
            """

            success = wechat_service.send_quick_notification(
                title=f"新的采购需求 - {order.shop_id.name}",
                content=message_content,
                message_type='采购通知',
                target='采购人员',
                redirect_url=f"/web#id={order.id}&model=restaurant.purchase.order&view_type=form"
            )

            if success:
                _logger.info(f"微信通知发送成功: {order.name}")
            else:
                _logger.warning(f"微信通知发送失败: {order.name}")

        except Exception as e:
            _logger.error(f"发送微信通知异常: {str(e)}")


class RestaurantPurchaseOrderLine(models.Model):
    _name = 'restaurant.purchase.order.line'
    _description = '餐厅采购订单明细'

    order_id = fields.Many2one(
        'restaurant.purchase.order',
        string='采购订单',
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='商品',
        required=True,
        domain=[('purchase_ok', '=', True)]
    )

    product_code = fields.Char(
        string='商品编码',
        related='product_id.default_code',
        readonly=True
    )

    product_barcode = fields.Char(
        string='商品条码',
        related='product_id.barcode',
        readonly=True
    )

    product_uom = fields.Many2one(
        'uom.uom',
        string='单位',
        required=True
    )

    product_qty = fields.Float(
        string='数量',
        required=True,
        default=1.0
    )

    price_unit = fields.Float(
        string='单价',
        digits='Product Price'
    )

    subtotal = fields.Float(
        string='小计',
        compute='_compute_subtotal',
        store=True
    )

    is_purchased = fields.Boolean(
        string='已采购',
        default=False
    )

    actual_qty = fields.Float(
        string='实际数量',
        help='收货时确认的实际数量'
    )

    notes = fields.Char(string='行备注')

    @api.depends('product_qty', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.product_qty * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
            self.price_unit = self.product_id.standard_price

    def action_toggle_purchased(self):
        """切换已采购状态"""
        for line in self:
            line.is_purchased = not line.is_purchased