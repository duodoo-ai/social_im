from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, Callable, Optional
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
            ('function', 'Function'),
            ('api', 'API Call'),
            ('odoo_method', 'Odoo Method'),
            ('python', 'Python Code'),
            ('webhook', 'Webhook')
        ],
        string='Tool Type',
        required=True,
        default='function',
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
    webhook_url = fields.Char(
        string='Webhook URL',
        help="Webhook endpoint URL (for webhook type)"
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

    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tool name must be unique!'),
        ('code_unique', 'unique(code)', 'Tool code must be unique!'),
    ]

    @api.constrains('tool_type')
    def _check_tool_implementation(self) -> None:
        """Validate tool implementation based on type."""
        for record in self:
            if record.tool_type == 'python' and not record.python_code:
                raise ValidationError("Python code is required for python tool type")
            elif record.tool_type == 'api' and not record.api_endpoint:
                raise ValidationError("API endpoint is required for api tool type")
            elif record.tool_type == 'odoo_method' and (not record.odoo_model or not record.odoo_method):
                raise ValidationError("Odoo model and method are required for odoo_method tool type")
            elif record.tool_type == 'webhook' and not record.webhook_url:
                raise ValidationError("Webhook URL is required for webhook tool type")

    def get_tool_schema(self) -> Dict[str, Any]:
        """Get tool schema for AI function calling.

        Returns:
            Dict[str, Any]: Tool schema compatible with AI function calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.function_name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute_tool(self, arguments=None, context=None):
        """Execute the tool with given arguments.

        Args:
            arguments (Dict[str, Any]): Tool arguments
            context (Dict[str, Any]): Execution context

        Returns:
            Any: Tool execution result

        Raises:
            UserError: If tool execution fails
        """
        # 处理参数为空的情况
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
            elif self.tool_type == 'webhook':
                return self._execute_webhook(arguments, context)
            else:
                raise UserError(f"Unsupported tool type: {self.tool_type}")

        except Exception as e:
            _logger.error(f"Tool execution failed: {str(e)}")
            raise UserError(f"Tool execution failed: {str(e)}")

    def action_execute_tool(self):
        """Action method for executing tool from UI button."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': f'Execute Tool: {self.name}',
            'res_model': 'oudu.bot.tool.execute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_tool_id': self.id,
            }
        }

    def execute_demo_tool(self):
        """Execute tool with demo arguments for testing."""
        self.ensure_one()

        # 根据工具类型提供默认参数
        demo_arguments = {}

        if self.tool_type == 'python':
            if self.function_name == 'calculate':
                demo_arguments = {'expression': '2 + 2 * 3'}
        elif self.tool_type == 'api':
            if self.function_name == 'get_weather':
                demo_arguments = {'city': 'Beijing'}
        elif self.tool_type == 'odoo_method':
            # 对于Odoo方法，使用安全的demo参数
            demo_arguments = {'search_term': 'demo', 'limit': 5}

        try:
            result = self.execute_tool(demo_arguments, {})

            # 显示结果通知
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Tool Execution: {self.name}',
                    'message': f'Execution successful! Result: {str(result)}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Tool Execution Failed: {self.name}',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def _check_permissions(self, context: Dict[str, Any]) -> bool:
        """Check if current user has permission to use this tool.

        Args:
            context (Dict[str, Any]): Execution context

        Returns:
            bool: True if user has permission
        """
        if not self.require_authentication:
            return True

        user = self.env.user
        if not self.allowed_groups:
            return True

        return bool(user.groups_id & self.allowed_groups)

    def _validate_arguments(self, arguments):
        """Validate arguments against parameter schema.

        Args:
            arguments (Dict[str, Any]): Arguments to validate

        Raises:
            ValidationError: If arguments are invalid
        """
        # 确保参数是字典
        if arguments is None:
            arguments = {}
        elif isinstance(arguments, str):
            # 如果参数是字符串，尝试解析为JSON
            try:
                arguments = json.loads(arguments)
            except:
                raise ValidationError(f"Invalid arguments format. Expected JSON, got: {arguments}")

        schema = self.parameters or {}

        # 如果schema是字符串，尝试解析
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except:
                schema = {}

        required_params = schema.get('required', [])

        # 检查必需参数
        for param in required_params:
            if param not in arguments:
                raise ValidationError(f"Missing required parameter: {param}")

        # 检查参数类型（基本验证）
        properties = schema.get('properties', {})
        for param, value in arguments.items():
            if param in properties:
                param_schema = properties[param]
                expected_type = param_schema.get('type')

                if expected_type == 'string' and not isinstance(value, str):
                    raise ValidationError(f"Parameter {param} must be a string")
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    raise ValidationError(f"Parameter {param} must be a number")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    raise ValidationError(f"Parameter {param} must be a boolean")
                elif expected_type == 'array' and not isinstance(value, list):
                    raise ValidationError(f"Parameter {param} must be an array")
                elif expected_type == 'object' and not isinstance(value, dict):
                    raise ValidationError(f"Parameter {param} must be an object")

    def _execute_python_code(self, arguments=None, context=None):
        """Execute Python code tool.

        Args:
            arguments (Dict[str, Any]): Tool arguments
            context (Dict[str, Any]): Execution context

        Returns:
            Any: Execution result
        """
        # 确保参数是字典
        if arguments is None:
            arguments = {}
        elif isinstance(arguments, str):
            # 如果参数是字符串，尝试解析为JSON
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
            # 在受控环境中执行代码
            exec(self.python_code or '', globals(), local_vars)
            return local_vars.get('result')
        except Exception as e:
            raise UserError(f"Python code execution failed: {str(e)}")

    def _execute_odoo_method(self, arguments=None, context=None):
        """Execute Odoo method tool.

        Args:
            arguments (Dict[str, Any]): Tool arguments
            context (Dict[str, Any]): Execution context

        Returns:
            Any: Method execution result
        """
        if not self.odoo_model or not self.odoo_method:
            raise UserError("Odoo model and method must be specified")

        try:
            # 确保参数是字典
            if arguments is None:
                arguments = {}
            elif isinstance(arguments, str):
                # 如果参数是字符串，尝试解析为JSON
                try:
                    arguments = json.loads(arguments)
                except:
                    raise UserError(f"Invalid arguments format. Expected JSON, got: {arguments}")

            model = self.env[self.odoo_model]
            method = getattr(model, self.odoo_method, None)

            if not method:
                raise UserError(f"Method {self.odoo_method} not found in model {self.odoo_model}")

            # 添加上下文到参数中
            if hasattr(method, '__code__') and 'context' in method.__code__.co_varnames:
                arguments['context'] = context or {}

            return method(**arguments)

        except Exception as e:
            raise UserError(f"Odoo method execution failed: {str(e)}")

    def _execute_api_call(self, arguments=None, context=None):
        """Execute API call tool.

        Args:
            arguments (Dict[str, Any]): Tool arguments
            context (Dict[str, Any]): Execution context

        Returns:
            Any: API response
        """
        try:
            import requests

            # 确保参数是字典
            if arguments is None:
                arguments = {}
            elif isinstance(arguments, str):
                # 如果参数是字符串，尝试解析为JSON
                try:
                    arguments = json.loads(arguments)
                except:
                    raise UserError(f"Invalid arguments format. Expected JSON, got: {arguments}")

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-AI-Tool/1.0'
            }

            # 从上下文添加认证信息
            if context and context.get('api_key'):
                headers['Authorization'] = f"Bearer {context['api_key']}"

            response = requests.request(
                method=self.api_method or 'GET',
                url=self.api_endpoint,
                headers=headers,
                json=arguments,
                timeout=30
            )

            response.raise_for_status()

            # 尝试解析JSON响应，如果失败返回文本
            try:
                return response.json()
            except:
                return response.text

        except Exception as e:
            raise UserError(f"API call failed: {str(e)}")

    def _execute_webhook(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute webhook tool.

        Args:
            arguments (Dict[str, Any]): Tool arguments
            context (Dict[str, Any]): Execution context

        Returns:
            Any: Webhook response
        """
        # Similar to API call but with webhook-specific logic
        return self._execute_api_call(arguments, context)