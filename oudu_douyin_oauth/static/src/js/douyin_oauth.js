odoo.define('oudu_douyin_oauth.DouyinOAuth', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');

    var DouyinOAuth = Widget.extend({
        template: 'DouyinOAuthWidget',

        events: {
            'click .douyin-connect': '_onConnectDouyin',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.config = options.config || {};
        },

        _onConnectDouyin: function (ev) {
            ev.preventDefault();
            var self = this;
            this._rpc({
                route: '/douyin/auth/get_config',
            }).then(function (config) {
                if (config && config.auth_url) {
                    window.location.href = config.auth_url;
                } else {
                    self.do_warn('错误', '抖音配置缺失，请联系管理员。');
                }
            });
        },
    });

    core.action_registry.add('douyin_oauth', DouyinOAuth);

    return DouyinOAuth;
});