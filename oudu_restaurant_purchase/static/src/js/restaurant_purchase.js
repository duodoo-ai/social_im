odoo.define('oudu_restaurant_purchase.RestaurantPurchase', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var rpc = require('web.rpc');

var _t = core._t;

var RestaurantPurchaseWidget = Widget.extend({
    template: 'RestaurantPurchaseWidget',

    events: {
        'click .toggle-purchased': '_onTogglePurchased',
        'click .btn-barcode-scan': '_onBarcodeScan'
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = options || {};
    },

    start: function () {
        return this._super.apply(this, arguments);
    },

    _onTogglePurchased: function (ev) {
        ev.preventDefault();
        var self = this;
        var lineId = $(ev.currentTarget).data('line-id');

        this._rpc({
            model: 'restaurant.purchase.order.line',
            method: 'action_toggle_purchased',
            args: [[lineId]]
        }).then(function (result) {
            if (result) {
                self.do_notify(_t('成功'), _t('状态已更新'));
                // 重新加载页面
                self._super.apply(this, arguments);
            } else {
                self.do_warn(_t('错误'), _t('操作失败'));
            }
        });
    },

    _onBarcodeScan: function (ev) {
        ev.preventDefault();
        var self = this;

        // 模拟条码扫描
        this._rpc({
            model: 'product.product',
            method: 'search_read',
            args: [[], ['name', 'barcode', 'default_code'], 10]
        }).then(function (products) {
            if (products.length > 0) {
                var randomProduct = products[Math.floor(Math.random() * products.length)];
                self.$('.barcode-input').val(randomProduct.barcode);
                self.do_notify(_t('扫描成功'), _t('已扫描: ') + randomProduct.name);
            }
        });
    }
});

// 采购进度组件
var PurchaseProgress = Widget.extend({
    template: 'PurchaseProgress',

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.orderId = options.orderId;
    },

    start: function () {
        this._loadProgress();
        return this._super.apply(this, arguments);
    },

    _loadProgress: function () {
        var self = this;

        this._rpc({
            model: 'restaurant.purchase.order',
            method: 'read',
            args: [[this.orderId], ['product_count', 'purchased_count']]
        }).then(function (results) {
            if (results.length > 0) {
                var order = results[0];
                var progress = (order.purchased_count / order.product_count) * 100;

                self.$('.progress-bar')
                    .css('width', progress + '%')
                    .text(order.purchased_count + '/' + order.product_count);
            }
        });
    }
});

// 注册组件
core.action_registry.add('restaurant_purchase_widget', RestaurantPurchaseWidget);
core.action_registry.add('purchase_progress', PurchaseProgress);

return {
    RestaurantPurchaseWidget: RestaurantPurchaseWidget,
    PurchaseProgress: PurchaseProgress
};
});