from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, Optional
import json
import logging

_logger = logging.getLogger(__name__)


class AITool(models.Model):
    _name = 'oudu.bot.tool'
    _description = 'AI Tool Definition'
    _order = 'sequence, name'

    # Basic Information
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(
        string='Tool Name',
        required=True,
        help="Display name for the tool"
    )
    code = fields.Char(
        string='Tool Code',
        required=True,
        help="Internal code for system reference"
    )
    description = fields.Text(
        string='Description',
        required=True,
        help="Detailed description of what the tool does"
    )

    # Tool Type Configuration
    tool_type = fields.Selection(
        selection=[
            ('python', 'Python Code'),
            ('api', 'API Call'),
            ('odoo_method', 'Odoo Method'),
            ('webhook', 'Webhook')
        ],
        string='Tool Type',
        required=True,
        default='python',
        help="Type of tool implementation"
    )

    # Function Definition
    function_name = fields.Char(
        string='Function Name',
        required=True,
        help="Name used in AI function calls"
    )
    parameters = fields.Json(
        string='Parameters Schema',
        default=lambda self: {
            "type": "object",
            "properties": {},
            "required": []
        },
        help="JSON schema for function parameters"
    )

    # Implementation Configuration
    python_code = fields.Text(
        string='Python Code',
        help="Python code to execute (for python type)"
    )
    api_endpoint = fields.Char(
        string='API Endpoint',
        help="API endpoint URL (for api type)"
    )
    api_method = fields.Selection(
        selection=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE')
        ],
        string='API Method',
        default='POST',
        help="HTTP method for API calls"
    )
    odoo_model = fields.Char(
        string='Odoo Model',
        help="Odoo model name (for odoo_method type)"
    )
    odoo_method = fields.Char(
        string='Odoo Method',
        help="Odoo method name to call (for odoo_method type)"
    )

    # Security and Access
    allowed_groups = fields.Many2many(
        'res.groups',
        string='Allowed Groups',
        help="User groups allowed to use this tool"
    )
    require_authentication = fields.Boolean(
        string='Require Authentication',
        default=True,
        help="Require user authentication for tool execution"
    )

    # Status
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="Enable or disable this tool"
    )
    # 新增字段：演示执行结果
    demo_execution_history = fields.One2many(
        'oudu.bot.tool.demo.result',
        'tool_id',
        string='Demo Execution History',
        readonly=True
    )
    last_demo_result = fields.Text(
        string='Last Demo Result',
        compute='_compute_last_demo_result',
        store=True
    )
    last_demo_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('not_tested', 'Not Tested')
    ], string='Last Demo Status', default='not_tested', compute='_compute_last_demo_result', store=True)

    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tool name must be unique!'),
        ('code_unique', 'unique(code)', 'Tool code must be unique!'),
    ]

    def execute_tool(self, arguments=None, context=None):
        """Execute the tool with given arguments."""
        if arguments is None:
            arguments = {}
        if context is None:
            context = {}

        try:
            # Check permissions
            if not self._check_permissions(context):
                raise UserError("Permission denied for tool execution")

            # Validate arguments against schema
            self._validate_arguments(arguments)

            # Execute based on tool type
            if self.tool_type == 'python':
                return self._execute_python_code(arguments, context)
            elif self.tool_type == 'odoo_method':
                return self._execute_odoo_method(arguments, context)
            elif self.tool_type == 'api':
                return self._execute_api_call(arguments, context)
            else:
                raise UserError(f"Unsupported tool type: {self.tool_type}")

        except Exception as e:
            _logger.error(f"Tool execution failed: {str(e)}")
            raise UserError(f"Tool execution failed: {str(e)}")

    @api.depends('demo_execution_history')
    def _compute_last_demo_result(self):
        """计算最后一次演示执行的结果和状态"""
        for tool in self:
            last_execution = self.env['oudu.bot.tool.demo.result'].search([
                ('tool_id', '=', tool.id)
            ], order='execution_date desc', limit=1)

            if last_execution:
                tool.last_demo_result = last_execution.result
                tool.last_demo_status = 'success' if last_execution.is_success else 'failed'
            else:
                tool.last_demo_result = ''
                tool.last_demo_status = 'not_tested'

    def execute_demo_tool(self):
        """Execute tool with demo arguments for testing and store results."""
        self.ensure_one()

        # 根据工具类型提供默认参数
        demo_arguments = {}

        if self.tool_type == 'python':
            if self.function_name == 'calculate':
                demo_arguments = {'expression': '2 + 2 * 3'}
            elif self.function_name == 'get_weather':
                demo_arguments = {'city': 'Beijing'}
            else:
                # 为其他 Python 工具提供通用参数
                demo_arguments = {'input': 'test'}
        elif self.tool_type == 'api':
            if self.function_name == 'get_weather':
                demo_arguments = {'city': 'Beijing'}
            else:
                demo_arguments = {'data': 'test'}
        elif self.tool_type == 'odoo_method':
            demo_arguments = {'search_term': 'demo', 'limit': 5}
        else:
            demo_arguments = {}

        try:
            result = self.execute_tool(demo_arguments, {})
            result_str = str(result)

            # 存储执行结果到历史记录
            demo_record = self.env['oudu.bot.tool.demo.result'].create({
                'tool_id': self.id,
                'arguments': json.dumps(demo_arguments, ensure_ascii=False),
                'result': result_str,
                'is_success': True,
                'execution_date': fields.Datetime.now()
            })

            # 显示结果通知
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Tool Execution: {self.name}',
                    'message': f'Execution successful! Result: {result_str}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_msg = str(e)

            # 存储错误结果到历史记录
            demo_record = self.env['oudu.bot.tool.demo.result'].create({
                'tool_id': self.id,
                'arguments': json.dumps(demo_arguments, ensure_ascii=False),
                'result': error_msg,
                'is_success': False,
                'execution_date': fields.Datetime.now()
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Tool Execution Failed: {self.name}',
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def clear_demo_history(self):
        """Clear all demo execution history for this tool."""
        self.ensure_one()
        self.demo_execution_history.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demo History Cleared',
                'message': f'All demo execution history for {self.name} has been cleared.',
                'type': 'info',
                'sticky': False,
            }
        }

    def _check_permissions(self, context: Dict[str, Any]) -> bool:
        """Check if current user has permission to use this tool."""
        if not self.require_authentication:
            return True

        user = self.env.user
        if not self.allowed_groups:
            return True

        return bool(user.groups_id & self.allowed_groups)

    def _validate_arguments(self, arguments):
        """Validate arguments against parameter schema."""
        if arguments is None:
            arguments = {}
        elif isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except:
                raise ValidationError(f"Invalid arguments format. Expected JSON, got: {arguments}")

        schema = self.parameters or {}

        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except:
                schema = {}

        required_params = schema.get('required', [])

        # Check required parameters
        for param in required_params:
            if param not in arguments:
                raise ValidationError(f"Missing required parameter: {param}")

    def _execute_python_code(self, arguments=None, context=None):
        """Execute Python code tool."""
        if arguments is None:
            arguments = {}
        elif isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except:
                raise UserError(f"Invalid arguments format. Expected JSON, got: {arguments}")

        local_vars = {
            'arguments': arguments,
            'context': context or {},
            'env': self.env,
            'result': None,
            'log': _logger.info,
            'json': json
        }

        try:
            exec(self.python_code or '', globals(), local_vars)
            return local_vars.get('result')
        except Exception as e:
            raise UserError(f"Python code execution failed: {str(e)}")

    def _execute_odoo_method(self, arguments=None, context=None):
        """Execute Odoo method tool."""
        if not self.odoo_model or not self.odoo_method:
            raise UserError("Odoo model and method must be specified")

        try:
            if arguments is None:
                arguments = {}
            elif isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    raise UserError(f"Invalid arguments format. Expected JSON, got: {arguments}")

            model = self.env[self.odoo_model]
            method = getattr(model, self.odoo_method, None)

            if not method:
                raise UserError(f"Method {self.odoo_method} not found in model {self.odoo_model}")

            return method(**arguments)

        except Exception as e:
            raise UserError(f"Odoo method execution failed: {str(e)}")

    def _execute_api_call(self, arguments=None, context=None):
        """Execute API call tool."""
        try:
            import requests

            if arguments is None:
                arguments = {}
            elif isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    raise UserError(f"Invalid arguments format. Expected JSON, got: {arguments}")

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-AI-Tool/1.0'
            }

            response = requests.request(
                method=self.api_method or 'GET',
                url=self.api_endpoint,
                headers=headers,
                json=arguments,
                timeout=30
            )

            response.raise_for_status()

            try:
                return response.json()
            except:
                return response.text

        except Exception as e:
            raise UserError(f"API call failed: {str(e)}")

    @api.model
    def call_tool(self, tool_code: str, arguments: Dict[str, Any] = None, context: Dict[str, Any] = None) -> Any:
        """Public method to call tool from other models.

        Args:
            tool_code (str): Code of the tool to execute
            arguments (Dict[str, Any]): Tool arguments
            context (Dict[str, Any]): Execution context

        Returns:
            Any: Tool execution result

        Example:
            result = self.env['oudu.bot.tool'].call_tool(
                'CALCULATOR',
                {'expression': '2 + 2 * 3'}
            )
        """
        tool = self.search([('code', '=', tool_code), ('is_active', '=', True)], limit=1)
        if not tool:
            raise UserError(f"Tool with code '{tool_code}' not found or inactive")

        return tool.execute_tool(arguments or {}, context or {})


class AIToolDemoResult(models.Model):
    _name = 'oudu.bot.tool.demo.result'
    _description = 'AI Tool Demo Execution Result'
    _order = 'execution_date desc'

    tool_id = fields.Many2one(
        'oudu.bot.tool',
        string='Tool',
        required=True,
        ondelete='cascade'
    )
    execution_date = fields.Datetime(
        string='Execution Date',
        default=fields.Datetime.now,
        required=True
    )
    arguments = fields.Text(
        string='Arguments',
        help='Arguments used in the demo execution'
    )
    result = fields.Text(
        string='Result',
        help='Execution result'
    )
    is_success = fields.Boolean(
        string='Success',
        help='Whether the execution was successful'
    )