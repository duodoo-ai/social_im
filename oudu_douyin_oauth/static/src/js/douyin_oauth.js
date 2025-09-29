odoo.define('oudu_douyin_oauth.DouyinOAuth', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');

    var DouyinOAuth = Widget.extend({
        template: 'DouyinOAuthWidget',

        events: {
            'click .douyin-connect': '_onConnectDouyin',
            'click .douyin-disconnect': '_onDisconnectDouyin',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.config = options.config || {};
        },

        /**
         * 连接抖音
         */
        _onConnectDouyin: function (ev) {
            ev.preventDefault();
            var self = this;

            this._rpc({
                route: '/douyin/auth/get_config',
            }).then(function (config) {
                if (config && config.auth_url) {
                    // 显示加载状态
                    self._showLoading(ev.target);
                    window.location.href = config.auth_url;
                } else {
                    self._showError('错误', '抖音配置缺失，请联系管理员。');
                }
            }).catch(function (error) {
                console.error('获取抖音配置失败:', error);
                self._showError('错误', '获取配置失败，请稍后重试。');
            });
        },

        /**
         * 断开抖音连接
         */
        _onDisconnectDouyin: function (ev) {
            ev.preventDefault();
            var self = this;

            Dialog.confirm(this, "确定要解除抖音绑定吗？", {
                confirm_callback: function() {
                    self._rpc({
                        route: '/douyin/auth/disconnect',
                    }).then(function(result) {
                        if (result.success) {
                            self._showSuccess('成功', '已成功解除抖音绑定');
                            // 刷新页面
                            setTimeout(function() {
                                window.location.reload();
                            }, 1500);
                        }
                    }).catch(function(error) {
                        console.error('解除绑定失败:', error);
                        self._showError('错误', '解除绑定失败，请稍后重试。');
                    });
                }
            });
        },

        /**
         * 显示加载状态
         */
        _showLoading: function (element) {
            var originalHtml = element.innerHTML;
            element.innerHTML = '<i class="fa fa-spinner fa-spin mr-2"></i>连接中...';
            element.classList.add('loading');

            // 3秒后恢复
            setTimeout(function() {
                element.innerHTML = originalHtml;
                element.classList.remove('loading');
            }, 3000);
        },

        /**
         * 显示错误消息
         */
        _showError: function (title, message) {
            Dialog.alert(this, message, {
                title: title,
            });
        },

        /**
         * 显示成功消息
         */
        _showSuccess: function (title, message) {
            Dialog.alert(this, message, {
                title: title,
            });
        }
    });

    core.action_registry.add('douyin_oauth', DouyinOAuth);

    return DouyinOAuth;
});