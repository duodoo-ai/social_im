from odoo import models, fields, api
import os


class AIProviderConfig(models.Model):
    _inherit = 'oudu.bot.provider'

    @api.model
    def load_environment_config(self):
        """从环境变量加载配置"""
        providers = self.search([])
        env_mapping = {
            'DEEPSEEK_R1': 'DEEPSEEK_API_KEY',
            'ALIBABA_QWEN': 'ALIBABA_API_KEY',
            'BAIDU_WENXIN': 'BAIDU_API_KEY',
            'TENCENT_HUNYUAN': 'TENCENT_API_KEY',
            'BYTEDANCE_DOUBAO': 'BYTEDANCE_API_KEY',
            'OPENAI_GPT': 'OPENAI_API_KEY',
        }

        for provider in providers:
            env_var = env_mapping.get(provider.code)
            if env_var and env_var in os.environ:
                provider.write({
                    'api_key': os.environ[env_var],
                    'is_active': True
                })