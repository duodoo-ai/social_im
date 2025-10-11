完整的集成示例和使用方法
示例：在销售模块中使用AI能力
python
from odoo import models, fields, api
from odoo.exceptions import UserError
from typing import Dict, Any

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def analyze_sales_opportunity(self) -> Dict[str, Any]:
        """使用AI分析销售机会"""
        try:
            # 调用AI代理分析销售订单
            result = self.env['oudu_bot.agent'].call_ai_agent(
                'sales_analyst',
                f"""
                分析以下销售订单的潜在机会和风险：
                客户：{self.partner_id.name}
                订单金额：{self.amount_total}
                产品数量：{len(self.order_line)}
                订单日期：{self.date_order}
                
                请提供：
                1. 风险评估
                2. 潜在追加销售机会
                3. 客户关系建议
                """,
                {
                    'order_data': {
                        'partner_id': self.partner_id.id,
                        'amount_total': self.amount_total,
                        'order_lines_count': len(self.order_line),
                        'products': [line.product_id.name for line in self.order_line]
                    }
                }
            )
            
            return {
                'success': True,
                'analysis': result.get('content', ''),
                'recommendations': result.get('tool_calls', [])
            }
            
        except Exception as e:
            raise UserError(f"销售机会分析失败: {str(e)}")
    
    def create_customer_from_chat(self, conversation_data: Dict[str, Any]) -> Any:
        """从聊天对话创建客户记录"""
        try:
            # 使用讨论机器人创建客户记录
            result = self.env['oudu_discuss.bot'].create_record_from_conversation(
                'res.partner',
                conversation_data
            )
            
            if result.get('success'):
                # 更新销售订单的客户
                self.partner_id = result['record_id']
                return self.partner_id
            else:
                raise UserError("客户记录创建失败")
                
        except Exception as e:
            raise UserError(f"客户创建失败: {str(e)}")
示例：客户服务自动化工作流
python
class CustomerServiceWorkflow(models.Model):
    _name = 'oudu_bot.workflow'
    _inherit = 'oudu_bot.workflow'
    
    def create_customer_service_workflow(self) -> 'CustomerServiceWorkflow':
        """创建客户服务工作流"""
        workflow_data = {
            'name': '客户服务自动化',
            'code': 'customer_service_auto',
            'workflow_steps': [
                {
                    'type': 'llm_call',
                    'name': '分析客户问题',
                    'prompt_template': '分析以下客户问题并提供解决方案：{input_data.customer_query}',
                    'data_extraction': {
                        'extract_json': True,
                        'output_keys': ['problem_type', 'urgency', 'suggested_solution']
                    }
                },
                {
                    'type': 'condition',
                    'name': '判断紧急程度',
                    'condition': '{workflow_data.urgency} == "high"',
                    'true_branch': [
                        {
                            'type': 'tool_call',
                            'name': '创建高优先级工单',
                            'tool_name': 'create_helpdesk_ticket',
                            'arguments': {
                                'name': '紧急问题：{workflow_data.problem_type}',
                                'priority': '3',
                                'description': '{workflow_data.suggested_solution}'
                            }
                        }
                    ],
                    'false_branch': [
                        {
                            'type': 'tool_call', 
                            'name': '创建普通工单',
                            'tool_name': 'create_helpdesk_ticket',
                            'arguments': {
                                'name': '问题：{workflow_data.problem_type}',
                                'priority': '2',
                                'description': '{workflow_data.suggested_solution}'
                            }
                        }
                    ]
                },
                {
                    'type': 'llm_call',
                    'name': '生成客户回复',
                    'prompt_template': '基于问题分析和解决方案，生成给客户的友好回复：{workflow_data.suggested_solution}'
                }
            ]
        }
        
        return self.create(workflow_data)
配置和使用指南
1. 配置AI提供商
python
# 在安装模块后，配置DeepSeek提供商
deepseek_provider = env['oudu_bot.provider'].create({
    'name': 'DeepSeek-R1',
    'code': 'DEEPSEEK',
    'provider_type': 'deepseek',
    'api_key': 'your_deepseek_api_key',
    'base_url': 'https://api.deepseek.com/v1',
    'default_model': 'deepseek-chat',
    'is_active': True
})
2. 创建AI代理
python
# 创建销售助手代理
sales_agent = env['oudu_bot.agent'].create({
    'name': '销售助手',
    'code': 'sales_assistant',
    'provider_id': deepseek_provider.id,
    'model_name': 'deepseek-chat',
    'system_prompt': """
    你是一个专业的销售助手，专注于：
    - 分析销售机会
    - 提供产品建议
    - 客户关系维护
    - 销售预测分析
    
    请用专业、有帮助的语气回复。
    """,
    'enable_tool_calling': True,
    'enable_knowledge_retrieval': True
})
3. 配置讨论机器人
python
# 创建讨论机器人
discuss_bot = env['oudu_discuss.bot'].create({
    'name': '客服机器人',
    'code': 'customer_service_bot',
    'agent_id': sales_agent.id,
    'user_id': env.ref('base.user_demo').id,
    'response_mode': 'mention',
    'allowed_models': ['res.partner', 'sale.order', 'project.task'],
    'auto_create_records': True,
    'require_confirmation': False
})


部署和运维指南
1. 安装依赖
bash
pip install requests
2. 配置环境变量
bash
# 在Odoo配置文件中添加
export DEEPSEEK_API_KEY="your_api_key_here"
export ALIBABA_API_KEY="your_alibaba_key_here"
3. 权限配置
确保以下用户组有适当权限：

group_ai_admin - AI系统管理员

group_ai_developer - AI开发人员

group_ai_user - AI普通用户

group_discuss_bot_admin - 讨论机器人管理员

group_discuss_bot_user - 讨论机器人用户

4. 监控和维护
python
# 健康检查脚本
def check_ai_system_health():
    """检查AI系统健康状态"""
    providers = env['oudu_bot.provider'].search([('is_active', '=', True)])
    for provider in providers:
        if not provider.test_connection():
            _logger.warning(f"Provider {provider.name} connection failed")
    
    bots = env['oudu_discuss.bot'].search([('is_active', '=', True)])
    for bot in bots:
        if not bot.agent_id.is_active:
            _logger.warning(f"Bot {bot.name} has inactive agent")

---------------------------------------

安装后配置指南
1. 激活提供商
安装模块后，管理员需要：

进入 AI Gateway → AI Providers

选择要使用的提供商

点击"编辑"，设置正确的API密钥

勾选"Active"复选框

点击"Test Connection"验证配置

2. 配置环境变量
对于生产环境，建议使用环境变量而非在界面中直接存储API密钥：

bash
# 在系统环境变量中设置
export DEEPSEEK_API_KEY="sk-your-actual-key"
export OPENAI_API_KEY="sk-your-actual-key"
3. 提供商特定的配置说明
DeepSeek-R1
支持工具调用 (function calling)

上下文长度：32K tokens

需要申请API密钥：https://platform.deepseek.com/

阿里通义千问
支持多种模型版本

需要阿里云账号：https://dashscope.aliyun.com/

百度文心一言
需要百度智能云账号

申请地址：https://cloud.baidu.com/product/wenxinworkshop

腾讯混元
需要腾讯云账号

申请地址：https://cloud.tencent.com/product/hunyuan

字节豆包
支持工具调用

申请地址：https://www.volcengine.com/product/ark

OpenAI
国际通用，支持最广泛的工具调用

申请地址：https://platform.openai.com/

故障排除
常见问题
连接测试失败

检查API密钥是否正确

验证网络连接和防火墙设置

确认服务端点URL是否正确

速率限制错误

调整 rate_limit 设置

实现请求队列和重试机制

令牌超限

减少 max_tokens 设置

优化提示词长度

演示模式配置

演示提供商默认激活，用于测试

生产环境请使用真实的AI提供商API密钥
