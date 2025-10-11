from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class AIToolExecuteWizard(models.TransientModel):  # 改为 TransientModel
    _name = 'oudu.bot.tool.execute.wizard'
    _description = 'AI Tool Execution Wizard'

    tool_id = fields.Many2one('oudu.bot.tool', string='Tool', required=True)
    tool_name = fields.Char(string='Tool Name', related='tool_id.name', readonly=True)

    # 修复：使用相同的 Selection 定义
    tool_type = fields.Selection(
        selection=[
            ('function', 'Function'),
            ('api', 'API Call'),
            ('odoo_method', 'Odoo Method'),
            ('python', 'Python Code'),
            ('webhook', 'Webhook')
        ],
        string='Tool Type',
        related='tool_id.tool_type',
        readonly=True
    )

    # 修复：使用 Text 字段显示格式化后的参数
    parameters_display = fields.Text(
        string='Parameters Schema',
        compute='_compute_parameters_display',
        readonly=True
    )

    input_arguments = fields.Text(
        string='Input Arguments (JSON)',
        help='Enter arguments in JSON format',
        default='{}'
    )

    result = fields.Text(string='Execution Result', readonly=True)

    @api.depends('tool_id.parameters')
    def _compute_parameters_display(self):
        """格式化显示参数 schema"""
        for record in self:
            if record.tool_id.parameters:
                try:
                    record.parameters_display = json.dumps(
                        record.tool_id.parameters,
                        indent=2,
                        ensure_ascii=False
                    )
                except:
                    record.parameters_display = str(record.tool_id.parameters)
            else:
                record.parameters_display = '{}'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # 提供示例JSON
        if 'input_arguments' in fields_list and not defaults.get('input_arguments'):
            defaults['input_arguments'] = '{\n  "example": "value"\n}'
        return defaults

    def action_execute(self):
        """Execute the tool with provided arguments."""
        self.ensure_one()

        try:
            # 解析输入参数
            arguments = json.loads(self.input_arguments)

            # 执行工具
            result = self.tool_id.execute_tool(arguments, {})

            # 格式化结果
            if isinstance(result, (dict, list)):
                formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
            else:
                formatted_result = str(result)

            self.write({'result': formatted_result})

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Tool Execution',
                    'message': 'Tool executed successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except json.JSONDecodeError as e:
            raise UserError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise UserError(f"Tool execution failed: {str(e)}")

    def action_test_demo(self):
        """Execute with demo arguments for testing."""
        self.ensure_one()

        # 根据工具类型和函数名提供demo参数
        demo_arguments = {}

        if self.tool_id.tool_type == 'python':
            if self.tool_id.function_name == 'calculate':
                demo_arguments = {'expression': '2 + 2 * 3'}
            elif self.tool_id.function_name == 'get_weather':
                demo_arguments = {'city': 'Beijing'}
        elif self.tool_id.tool_type == 'api':
            if self.tool_id.function_name == 'get_weather':
                demo_arguments = {'city': 'Beijing'}
        elif self.tool_id.tool_type == 'odoo_method':
            demo_arguments = {'search_term': 'demo', 'limit': 5}
        else:
            # 通用demo参数
            demo_arguments = {'test': 'demo_value'}

        self.input_arguments = json.dumps(demo_arguments, indent=2, ensure_ascii=False)
        return self.action_execute()