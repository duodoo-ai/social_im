odoo.define('oudu_douyin_oauth.SocialLogin', function (require) {
    "use strict";

    // 简单的社交登录功能
    function initSocialLogin() {
        // 添加按钮点击效果
        var buttons = document.querySelectorAll('.social-login-btn, .oe_login_wechat_qr a, .oe_login_douyin_qr a');

        buttons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                // 添加简单的点击反馈
                var originalText = this.innerHTML;
                this.innerHTML = '<i class="fa fa-spinner fa-spin mr-2"></i>加载中...';
                this.style.opacity = '0.7';

                setTimeout(function() {
                    this.innerHTML = originalText;
                    this.style.opacity = '1';
                }.bind(this), 1000);
            });
        });
    }

    // 页面加载完成后初始化
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(initSocialLogin, 100);
    });

    return {
        initSocialLogin: initSocialLogin
    };
});