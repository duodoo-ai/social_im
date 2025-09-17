// static/src/js/embedded_qr.js
odoo.define('oudu_wechat_login_qrcode.embedded_qr', function (require) {
    "use strict";

    var ajax = require('web.ajax');

    function initQRCode() {
        var container = document.getElementById('qr_code_img');
        if (!container) {
            console.error("二维码容器未找到!");
            return;
        }

        var statusMessage = document.getElementById('status_message');
        var qrActions = document.getElementById('qr_actions');

        // 显示加载状态
        statusMessage.textContent = '正在生成二维码...';

        // 通过AJAX获取二维码
        ajax.jsonRpc('/wechat/qr/generate', 'call')
            .then(function (result) {
                if (result.error) {
                    statusMessage.textContent = '错误: ' + result.error;
                } else {
                    // 创建二维码图像
                    var img = document.createElement('img');
                    img.src = 'data:image/png;base64,' + result.qr_img;
                    img.alt = '微信扫码登录';
                    img.style.maxWidth = '200px';
                    container.innerHTML = '';
                    container.appendChild(img);

                    statusMessage.textContent = '请使用微信扫描二维码登录';

                    // 启动轮询
                    require('oudu_wechat_login_qrcode.qr_polling')
                        .then(function (polling) {
                            polling.checkLoginStatus(result.session_id);
                        });
                }
            })
            .catch(function (error) {
                console.error('QR code generation failed:', error);
                statusMessage.textContent = '获取二维码失败，请重试';
                if (qrActions) {
                    qrActions.innerHTML = '<button class="btn btn-primary" onclick="window.location.reload()">刷新页面</button>';
                }
            });
    }

    return {
        initQRCode: initQRCode
    };
});