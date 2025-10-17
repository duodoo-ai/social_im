from odoo import http, fields,  _
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


class RestaurantPurchaseController(http.Controller):

    @http.route('/restaurant/purchase/dashboard', type='http', auth='user', website=True)
    def purchase_dashboard(self, **kw):
        """采购工作台 - 集成所有功能"""
        try:
            # 获取今日采购订单
            today_orders = request.env['restaurant.purchase.order'].search([
                ('delivery_date', '=', fields.Date.today()),
                ('state', 'in', ['chef_submitted', 'purchasing', 'received'])
            ])

            # 获取待收货商品统计
            pending_stats = self._get_pending_receipts_stats()

            return request.render('oudu_restaurant_purchase.purchase_dashboard_template', {
                'orders': today_orders,
                'pending_stats': pending_stats,
                'user': request.env.user
            })
        except Exception as e:
            _logger.error(f"采购工作台异常: {str(e)}")
            return request.render('oudu_restaurant_purchase.error_template')

    def _get_pending_receipts_stats(self):
        """获取待收货统计信息"""
        try:
            today_orders = request.env['restaurant.purchase.order'].search([
                ('delivery_date', '=', fields.Date.today()),
                ('state', 'in', ['purchasing', 'received'])
            ])

            total_pending = 0
            pending_items = []

            for order in today_orders:
                for line in order.line_ids:
                    if not line.actual_qty or line.actual_qty == 0:
                        total_pending += 1
                        pending_items.append({
                            'product_name': line.product_id.name,
                            'barcode': line.product_barcode or line.product_code,
                            'shop_name': order.shop_id.name,
                            'planned_qty': line.product_qty,
                            'actual_qty': line.actual_qty,
                            'order_name': order.name
                        })

            return {
                'total_pending': total_pending,
                'pending_items': pending_items[:10]  # 只显示前10个
            }
        except Exception as e:
            _logger.error(f"获取待收货统计异常: {str(e)}")
            return {'total_pending': 0, 'pending_items': []}

    @http.route('/restaurant/purchase/start_purchasing', type='json', auth='user')
    def start_purchasing(self, order_id, **kw):
        """开始采购"""
        try:
            order = request.env['restaurant.purchase.order'].browse(order_id)
            if order.exists():
                order.action_start_purchasing()
                return {'success': True}
            return {'success': False, 'error': '订单不存在'}
        except Exception as e:
            _logger.error(f"开始采购异常: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/restaurant/purchase/receive_order', type='json', auth='user')
    def receive_order(self, order_id, **kw):
        """确认收货"""
        try:
            order = request.env['restaurant.purchase.order'].browse(order_id)
            if order.exists():
                order.action_receive()
                return {'success': True}
            return {'success': False, 'error': '订单不存在'}
        except Exception as e:
            _logger.error(f"确认收货异常: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/restaurant/purchase/complete_order', type='json', auth='user')
    def complete_order(self, order_id, **kw):
        """完成订单"""
        try:
            order = request.env['restaurant.purchase.order'].browse(order_id)
            if order.exists():
                order.action_done()
                return {'success': True}
            return {'success': False, 'error': '订单不存在'}
        except Exception as e:
            _logger.error(f"完成订单异常: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/restaurant/purchase/today', type='http', auth='user', website=True)
    def today_purchase_orders(self, **kw):
        """今日采购订单页面"""
        try:
            today_orders = request.env['restaurant.purchase.order'].search([
                ('delivery_date', '=', fields.Date.today()),
                ('state', 'in', ['chef_submitted', 'purchasing'])
            ])

            return request.render('oudu_restaurant_purchase.today_orders_template', {
                'orders': today_orders,
                'user': request.env.user
            })
        except Exception as e:
            _logger.error(f"获取今日订单异常: {str(e)}")
            return request.render('oudu_restaurant_purchase.error_template')

    @http.route('/restaurant/purchase/quick_receive', type='http', auth='user', website=True)
    def quick_receive_page(self, **kw):
        """快速收货页面"""
        try:
            return request.render('oudu_restaurant_purchase.quick_receive_template')
        except Exception as e:
            _logger.error(f"快速收货页面异常: {str(e)}")
            return request.render('oudu_restaurant_purchase.error_template')

    @http.route('/restaurant/purchase/search_product', type='json', auth='user')
    def search_product(self, barcode=None, name=None, **kw):
        """搜索商品"""
        try:
            domain = []
            if barcode:
                domain.append(('barcode', '=', barcode))
            if name:
                domain.append(('name', 'ilike', name))

            products = request.env['product.product'].search(domain, limit=20)

            result = []
            for product in products:
                result.append({
                    'id': product.id,
                    'name': product.name,
                    'barcode': product.barcode,
                    'default_code': product.default_code,
                    'uom_name': product.uom_id.name,
                    'standard_price': product.standard_price
                })

            return {'success': True, 'products': result}
        except Exception as e:
            _logger.error(f"搜索商品异常: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/restaurant/purchase/toggle_purchased', type='json', auth='user')
    def toggle_purchased(self, line_id, **kw):
        """切换已采购状态"""
        try:
            line = request.env['restaurant.purchase.order.line'].browse(line_id)
            if line.exists():
                line.action_toggle_purchased()
                return {'success': True, 'is_purchased': line.is_purchased}
            return {'success': False, 'error': '记录不存在'}
        except Exception as e:
            _logger.error(f"切换采购状态异常: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/restaurant/purchase/quick_receive_action', type='json', auth='user')
    def quick_receive_action(self, barcode, actual_qty, **kw):
        """快速收货操作"""
        try:
            # 根据条码查找商品
            product = request.env['product.product'].search([('barcode', '=', barcode)], limit=1)
            if not product:
                return {'success': False, 'error': '未找到对应商品'}

            # 查找今日需要收货的订单行
            today_orders = request.env['restaurant.purchase.order'].search([
                ('delivery_date', '=', fields.Date.today()),
                ('state', 'in', ['purchasing'])
            ])

            lines = today_orders.line_ids.filtered(
                lambda l: l.product_id.id == product.id and not l.actual_qty
            )

            if not lines:
                return {'success': False, 'error': '未找到待收货的商品'}

            # 更新实际数量
            for line in lines:
                line.write({'actual_qty': actual_qty})

            return {'success': True, 'message': f'成功更新{len(lines)}条记录'}
        except Exception as e:
            _logger.error(f"快速收货异常: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/restaurant/purchase/get_pending_receipts', type='json', auth='user')
    def get_pending_receipts(self, **kw):
        """获取今日待收货商品列表"""
        try:
            today_orders = request.env['restaurant.purchase.order'].search([
                ('delivery_date', '=', fields.Date.today()),
                ('state', 'in', ['purchasing', 'received'])
            ])

            pending_receipts = []
            for order in today_orders:
                for line in order.line_ids:
                    if not line.actual_qty or line.actual_qty == 0:  # 未收货的行
                        pending_receipts.append({
                            'product_name': line.product_id.name,
                            'barcode': line.product_barcode or line.product_code,
                            'shop_name': order.shop_id.name,
                            'planned_qty': line.product_qty,
                            'actual_qty': line.actual_qty
                        })

            return {'success': True, 'pending_receipts': pending_receipts}
        except Exception as e:
            _logger.error(f"获取待收货列表异常: {str(e)}")
            return {'success': False, 'error': str(e)}