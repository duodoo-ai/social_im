odoo.define('oudu_douyin_oauth.DouyinQRCode', function (require) {
    "use strict";

    // 正确的依赖声明
    var publicWidget = require('web.public.widget');
    var rpc = require('web.rpc');

    var DouyinQRCode = publicWidget.Widget.extend({
        selector: '#douyin_qrcode_page',
        events: {
            'click .refresh-qrcode': '_onRefreshQRCode',
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._initQRCode();
                self._startPolling();
            });
        },

        /**
         * 初始化二维码
         */
        _initQRCode: function () {
            var authUrl = this.$el.data('auth-url');
            var qrcodeContainer = this.$el.find('#douyin_qrcode')[0];

            if (authUrl && qrcodeContainer && typeof QRCode !== 'undefined') {
                // 使用QRCode.js生成二维码
                new QRCode(qrcodeContainer, {
                    text: authUrl,
                    width: 200,
                    height: 200,
                    colorDark: "#000000",
                    colorLight: "#ffffff",
                    correctLevel: QRCode.CorrectLevel.H
                });
            } else {
                console.warn('QRCode library not loaded or missing auth URL');
            }
        },

        /**
         * 开始轮询登录状态
         */
        _startPolling: function () {
            this.state = this.$el.data('state');
            this.pollInterval = 3000; // 3秒轮询一次
            this.timeout = 300000; // 5分钟超时
            this.startTime = Date.now();

            this._checkLoginStatus();
        },

        /**
         * 检查登录状态
         */
        _checkLoginStatus: function () {
            var self = this;

            if (Date.now() - this.startTime > this.timeout) {
                this._updateStatus('expired', '二维码已过期，请刷新页面');
                return;
            }

            // 使用 rpc 进行调用
            rpc.query({
                route: '/douyin/auth/check_status',
                params: { state: this.state }
            }).then(function (result) {
                if (result.status === 'success') {
                    self._updateStatus('success', '登录成功，正在跳转...');
                    setTimeout(function() {
                        window.location.href = result.redirect_url || '/web';
                    }, 2000);
                } else if (result.status === 'waiting') {
                    self._updateStatus('waiting', result.message);
                    setTimeout(function() {
                        self._checkLoginStatus();
                    }, self.pollInterval);
                } else if (result.status === 'invalid') {
                    self._updateStatus('expired', result.message);
                } else {
                    self._updateStatus('error', result.message);
                    setTimeout(function() {
                        self._checkLoginStatus();
                    }, self.pollInterval);
                }
            }).catch(function (error) {
                console.error('检查登录状态失败:', error);
                self._updateStatus('error', '网络错误，重试中...');
                setTimeout(function() {
                    self._checkLoginStatus();
                }, self.pollInterval);
            });
        },

        /**
         * 更新状态显示
         */
        _updateStatus: function (status, message) {
            var statusElement = this.$el.find('.status-message');
            var qrContainer = this.$el.find('.qrcode-container');

            // 移除所有状态类
            statusElement.removeClass('status-waiting status-success status-error status-expired');
            qrContainer.removeClass('qr-waiting qr-success qr-error qr-expired');

            // 添加新状态类
            statusElement.addClass('status-' + status);
            qrContainer.addClass('qr-' + status);
            statusElement.text(message);
        },

        /**
         * 刷新二维码
         */
        _onRefreshQRCode: function () {
            window.location.reload();
        }
    });

    // 注册公共组件
    publicWidget.registry.DouyinQRCode = DouyinQRCode;

    return DouyinQRCode;
});