odoo.define('oudu_douyin_oauth.SocialLogin', function (require) {
    "use strict";

    // 正确的依赖声明
    var publicWidget = require('web.public.widget');

    var SocialLogin = publicWidget.Widget.extend({
        selector: '.oe_login_form, .login-form',

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._initSocialLogin();
            });
        },

        /**
         * 初始化社交登录按钮效果
         */
        _initSocialLogin: function () {
            var buttons = document.querySelectorAll('.social-login-btn, .oe_login_buttons a');

            buttons.forEach(function(button) {
                button.addEventListener('click', function(e) {
                    // 添加简单的点击反馈
                    var originalText = this.innerHTML;
                    var originalBackground = this.style.background;

                    this.innerHTML = '<i class="fa fa-spinner fa-spin mr-2"></i>加载中...';
                    this.style.opacity = '0.7';
                    this.style.pointerEvents = 'none';

                    // 3秒后恢复
                    setTimeout(function() {
                        this.innerHTML = originalText;
                        this.style.opacity = '1';
                        this.style.pointerEvents = 'auto';
                    }.bind(this), 3000);
                });
            });

            // 添加按钮悬停效果
            this._addButtonHoverEffects();
        },

        /**
         * 添加按钮悬停效果
         */
        _addButtonHoverEffects: function () {
            var style = document.createElement('style');
            style.textContent = `
                .oe_login_buttons a {
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }
                .oe_login_buttons a:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                }
                .oe_login_buttons a:active {
                    transform: translateY(0);
                }
                .oe_login_buttons a.loading {
                    cursor: not-allowed;
                }
            `;
            document.head.appendChild(style);
        }
    });

    // 注册公共组件
    publicWidget.registry.SocialLogin = SocialLogin;

    return SocialLogin;
});