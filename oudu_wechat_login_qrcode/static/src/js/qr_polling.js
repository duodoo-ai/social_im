odoo.define('oudu_wechat_login_qrcode.qr_polling', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;

    function checkLoginStatus(session_id) {
        var retries = 0;
        var maxRetries = 30;
        var baseDelay = 2000;

        function poll() {
            if (retries >= maxRetries) {
                handleQRCodeExpired();
                return;
            }

            ajax.jsonRpc('/wechat/qr/status', 'call', {
                session_id: session_id
            }).then(function(result) {
                if (result.status === 'success') {
                    handleLoginSuccess(result.redirect_url);
                } else if (result.status === 'scanned') {
                    updateStatusMessage(_t('请在手机端确认登录'));
                    setTimeout(poll, baseDelay);
                } else if (result.status === 'pending') {
                    setTimeout(poll, baseDelay);
                } else if (result.status === 'expired') {
                    handleQRCodeExpired();
                } else if (result.status === 'canceled') {
                    handleQRCodeCanceled();
                } else {
                    retries++;
                    setTimeout(poll, baseDelay * Math.pow(1.5, retries));
                }
            }).catch(function(error) {
                console.error('Polling error:', error);
                retries++;
                setTimeout(poll, baseDelay * Math.pow(1.5, retries));
            });
        }

        function updateStatusMessage(message) {
            var statusElement = document.getElementById('status_message');
            if (statusElement) {
                statusElement.textContent = message;
            }
        }

        function handleLoginSuccess(redirectUrl) {
            updateStatusMessage(_t('登录成功，正在跳转...'));
            setTimeout(function() {
                window.location.href = redirectUrl || '/web';
            }, 1000);
        }

        function handleQRCodeExpired() {
            updateStatusMessage(_t('二维码已过期，请刷新页面重试'));
            showRefreshButton();
        }

        function handleQRCodeCanceled() {
            updateStatusMessage(_t('用户取消登录'));
            showRefreshButton();
        }

        function showRefreshButton() {
            var actionsElement = document.querySelector('.actions');
            if (actionsElement) {
                var refreshBtn = document.createElement('button');
                refreshBtn.className = 'btn btn-primary ml-2';
                refreshBtn.textContent = _t('刷新二维码');
                refreshBtn.onclick = function() {
                    window.location.reload();
                };
                actionsElement.appendChild(refreshBtn);
            }
        }

        // 开始轮询
        poll();
    }

    // 更新状态显示函数
    function updateStatusMessage(message) {
        var statusElement = document.getElementById('status_message');
        if (statusElement) statusElement.textContent = message;
    }

    // 更新按钮显示函数
    function showRefreshButton() {
        var actionsElement = document.getElementById('qr_actions');
        if (actionsElement) {
            actionsElement.innerHTML = '';

            var refreshBtn = document.createElement('button');
            refreshBtn.className = 'btn btn-primary ml-2';
            refreshBtn.textContent = _t('刷新二维码');
            refreshBtn.onclick = function() {
                window.location.reload();
            };
            actionsElement.appendChild(refreshBtn);
        }
    }

    return {
        checkLoginStatus: checkLoginStatus,
        updateStatusMessage: updateStatusMessage,
        showRefreshButton: showRefreshButton
    };
});
