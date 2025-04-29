odoo.define('deepseek_integration.widget', function (require) {
"use strict";

const AbstractField = require('web.AbstractField');
const fieldRegistry = require('web.field_registry');

const DeepseekWidget = AbstractField.extend({
    template: 'DeepseekWidget',
    events: _.extend({}, AbstractField.prototype.events, {
        'click .send-request': '_onClickSend',
    }),

    _renderEdit: function() {
        this.$el.html(`
            <div class="input-group">
                <textarea class="form-control" rows="4"></textarea>
                <div class="input-group-append">
                    <button class="btn btn-primary send-request">
                        Send to Deepseek
                    </button>
                </div>
            </div>
            <div class="response-container mt-2"></div>
        `);
    },

    _onClickSend: function() {
        const prompt = this.$('textarea').val();
        this._rpc({
            model: 'deepseek.history',
            method: 'create_request',
            args: [prompt]
        }).then(result => {
            this.$('.response-container').html(`
                <div class="alert alert-success">
                    ${_.escape(result.response)}
                </div>
            `);
        });
    }
});

fieldRegistry.add('deepseek_widget', DeepseekWidget);
return { DeepseekWidget };
});