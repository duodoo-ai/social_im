from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, List, Optional
import json
import logging

_logger = logging.getLogger(__name__)


class AIWorkflow(models.Model):
    _name = 'oudu.bot.workflow'
    _description = 'AI Workflow Automation'
    _order = 'sequence, name'

    # Basic Information
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(
        string='Workflow Name',
        required=True,
        help="Display name for the workflow"
    )
    code = fields.Char(
        string='Workflow Code',
        required=True,
        help="Internal code for system reference"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of the workflow"
    )

    # Agent Configuration
    agent_id = fields.Many2one(
        'oudu.bot.agent',
        string='AI Agent',
        required=True,
        domain="[('is_active', '=', True)]",
        help="AI agent that executes this workflow"
    )

    # Workflow Definition
    workflow_steps = fields.Json(
        string='Workflow Steps',
        default=lambda: [],
        help="JSON definition of workflow steps and logic"
    )
    input_schema = fields.Json(
        string='Input Schema',
        help="JSON schema for workflow input validation"
    )
    output_schema = fields.Json(
        string='Output Schema',
        help="JSON schema for workflow output"
    )

    # Execution Configuration
    max_execution_time = fields.Integer(
        string='Max Execution Time (seconds)',
        default=300,
        help="Maximum allowed execution time"
    )
    retry_count = fields.Integer(
        string='Retry Count',
        default=3,
        help="Number of retry attempts on failure"
    )
    concurrent_executions = fields.Integer(
        string='Concurrent Executions',
        default=5,
        help="Maximum concurrent workflow executions"
    )

    # Status and Monitoring
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="Enable or disable this workflow"
    )
    last_execution = fields.Datetime(
        string='Last Execution',
        help="When this workflow was last executed"
    )
    execution_count = fields.Integer(
        string='Execution Count',
        default=0,
        help="Number of times this workflow has been executed"
    )
    success_count = fields.Integer(
        string='Success Count',
        default=0,
        help="Number of successful executions"
    )
    failure_count = fields.Integer(
        string='Failure Count',
        default=0,
        help="Number of failed executions"
    )

    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Workflow name must be unique!'),
        ('code_unique', 'unique(code)', 'Workflow code must be unique!'),
    ]

    @api.constrains('max_execution_time')
    def _check_max_execution_time(self) -> None:
        """Validate maximum execution time."""
        for record in self:
            if record.max_execution_time < 1 or record.max_execution_time > 3600:
                raise ValidationError("Max execution time must be between 1 and 3600 seconds")

    def execute_workflow(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the workflow with given input data.

        Args:
            input_data (Dict[str, Any]): Input data for the workflow
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Workflow execution result

        Raises:
            UserError: If workflow execution fails
        """
        context = context or {}

        try:
            # Validate input data
            self._validate_input(input_data)

            # Initialize execution context
            execution_context = {
                'input_data': input_data,
                'workflow_data': {},
                'step_results': {},
                'current_step': 0,
                'context': context
            }

            # Execute workflow steps
            steps = self.workflow_steps or []
            for step_index, step in enumerate(steps):
                execution_context['current_step'] = step_index
                step_result = self._execute_step(step, execution_context)
                execution_context['step_results'][str(step_index)] = step_result

                # Check for early termination
                if step_result.get('terminate_workflow'):
                    break

            # Prepare final result
            result = self._prepare_result(execution_context)

            # Update execution statistics
            self._update_execution_stats(True)

            return result

        except Exception as e:
            # Update failure statistics
            self._update_execution_stats(False)
            _logger.error(f"Workflow execution failed: {str(e)}")
            raise UserError(f"Workflow execution failed: {str(e)}")

    def _validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate input data against schema.

        Args:
            input_data (Dict[str, Any]): Input data to validate

        Raises:
            ValidationError: If input data is invalid
        """
        if not self.input_schema:
            return

        # Basic schema validation (simplified)
        required_fields = self.input_schema.get('required', [])
        properties = self.input_schema.get('properties', {})

        # Check required fields
        for field in required_fields:
            if field not in input_data:
                raise ValidationError(f"Missing required field: {field}")

        # Check field types (basic validation)
        for field, value in input_data.items():
            if field in properties:
                field_schema = properties[field]
                expected_type = field_schema.get('type')

                if expected_type == 'string' and not isinstance(value, str):
                    raise ValidationError(f"Field {field} must be a string")
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    raise ValidationError(f"Field {field} must be a number")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    raise ValidationError(f"Field {field} must be a boolean")

    def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step.

        Args:
            step (Dict[str, Any]): Step definition
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Step execution result
        """
        step_type = step.get('type', 'llm_call')

        try:
            if step_type == 'llm_call':
                return self._execute_llm_step(step, context)
            elif step_type == 'tool_call':
                return self._execute_tool_step(step, context)
            elif step_type == 'condition':
                return self._execute_condition_step(step, context)
            elif step_type == 'data_transformation':
                return self._execute_data_transformation_step(step, context)
            elif step_type == 'api_call':
                return self._execute_api_step(step, context)
            else:
                raise UserError(f"Unknown step type: {step_type}")

        except Exception as e:
            _logger.error(f"Step execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'step_type': step_type
            }

    def _execute_llm_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM call step.

        Args:
            step (Dict[str, Any]): Step definition
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Step result
        """
        # Prepare prompt from template
        prompt_template = step.get('prompt_template', '')
        user_input = self._render_template(prompt_template, context)

        # Execute agent
        result = self.agent_id.execute(user_input, context)

        # Extract and store relevant data
        extracted_data = self._extract_data_from_llm_response(result, step)
        context['workflow_data'].update(extracted_data)

        return {
            'success': True,
            'type': 'llm_call',
            'result': result,
            'extracted_data': extracted_data
        }

    def _execute_tool_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool call step.

        Args:
            step (Dict[str, Any]): Step definition
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Step result
        """
        tool_name = step.get('tool_name')
        tool_arguments = step.get('arguments', {})

        # Render template in arguments
        rendered_arguments = {}
        for key, value in tool_arguments.items():
            if isinstance(value, str):
                rendered_arguments[key] = self._render_template(value, context)
            else:
                rendered_arguments[key] = value

        # Find and execute tool
        tool = self.env['oudu.bot.tool'].search([
            ('function_name', '=', tool_name),
            ('is_active', '=', True)
        ], limit=1)

        if not tool:
            raise UserError(f"Tool not found: {tool_name}")

        tool_result = tool.execute_tool(rendered_arguments, context)

        # Store tool result
        output_key = step.get('output_key')
        if output_key:
            context['workflow_data'][output_key] = tool_result

        return {
            'success': True,
            'type': 'tool_call',
            'tool_name': tool_name,
            'result': tool_result
        }

    def _execute_condition_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute condition step.

        Args:
            step (Dict[str, Any]): Step definition
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Step result
        """
        condition = step.get('condition', '')
        true_branch = step.get('true_branch', [])
        false_branch = step.get('false_branch', [])

        # Evaluate condition (simplified - in practice use a proper expression evaluator)
        condition_result = self._evaluate_condition(condition, context)

        # Store condition result
        context['workflow_data']['_condition_result'] = condition_result

        # Determine next steps
        next_steps = true_branch if condition_result else false_branch

        return {
            'success': True,
            'type': 'condition',
            'condition': condition,
            'result': condition_result,
            'next_steps': next_steps,
            'terminate_workflow': step.get('terminate_workflow', False)
        }

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate condition expression.

        Args:
            condition (str): Condition expression
            context (Dict[str, Any]): Execution context

        Returns:
            bool: Evaluation result
        """
        # Simplified condition evaluation
        # In practice, use a proper expression evaluator with security considerations
        try:
            # Replace variable references with actual values
            evaluated_condition = condition
            for key, value in context['workflow_data'].items():
                if isinstance(value, (str, int, float, bool)):
                    evaluated_condition = evaluated_condition.replace(f'{{{{{key}}}}}', str(value))

            # Simple boolean evaluation (extend as needed)
            if evaluated_condition.lower() in ('true', '1', 'yes'):
                return True
            elif evaluated_condition.lower() in ('false', '0', 'no'):
                return False

            # Default to False for safety
            return False

        except Exception as e:
            _logger.error(f"Condition evaluation failed: {str(e)}")
            return False

    def _execute_data_transformation_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation step.

        Args:
            step (Dict[str, Any]): Step definition
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Step result
        """
        transformation = step.get('transformation', {})
        input_data = transformation.get('input', {})
        output_mapping = transformation.get('output_mapping', {})

        transformed_data = {}

        for output_key, input_expr in output_mapping.items():
            # Apply transformation (simplified)
            transformed_value = self._apply_transformation(input_expr, input_data, context)
            transformed_data[output_key] = transformed_value

        # Store transformed data
        context['workflow_data'].update(transformed_data)

        return {
            'success': True,
            'type': 'data_transformation',
            'transformed_data': transformed_data
        }

    def _apply_transformation(self, expression: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Apply data transformation.

        Args:
            expression (str): Transformation expression
            input_data (Dict[str, Any]): Input data
            context (Dict[str, Any]): Execution context

        Returns:
            Any: Transformed value
        """
        # Simplified transformation (extend as needed)
        try:
            # Handle variable references
            if expression.startswith('${') and expression.endswith('}'):
                var_path = expression[2:-1].split('.')
                current_data = {**input_data, **context['workflow_data']}

                for key in var_path:
                    if isinstance(current_data, dict) and key in current_data:
                        current_data = current_data[key]
                    else:
                        return None

                return current_data

            # Handle string concatenation
            elif '+' in expression:
                parts = expression.split('+')
                return ''.join(str(self._apply_transformation(part.strip(), input_data, context)) for part in parts)

            # Return as-is for other cases
            else:
                return expression

        except Exception as e:
            _logger.error(f"Transformation failed: {str(e)}")
            return None

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with context data.

        Args:
            template (str): Template string
            context (Dict[str, Any]): Context data

        Returns:
            str: Rendered template
        """
        try:
            rendered = template
            data = {**context['input_data'], **context['workflow_data']}

            for key, value in data.items():
                if isinstance(value, (str, int, float)):
                    placeholder = f'{{{{{key}}}}}'
                    rendered = rendered.replace(placeholder, str(value))

            return rendered

        except Exception as e:
            _logger.error(f"Template rendering failed: {str(e)}")
            return template

    def _extract_data_from_llm_response(self, result: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from LLM response.

        Args:
            result (Dict[str, Any]): LLM response
            step (Dict[str, Any]): Step definition

        Returns:
            Dict[str, Any]: Extracted data
        """
        extraction_rules = step.get('data_extraction', {})
        extracted_data = {}

        # Extract from content
        content = result.get('content', '')
        if extraction_rules.get('extract_json') and content:
            try:
                # Try to parse JSON from content
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_data = json.loads(json_match.group())
                    extracted_data.update(json_data)
            except:
                pass

        # Extract from tool calls
        tool_calls = result.get('tool_calls', [])
        for tool_call in tool_calls:
            if tool_call.get('success'):
                tool_result = tool_call.get('result', {})
                if isinstance(tool_result, dict):
                    extracted_data.update(tool_result)

        return extracted_data

    def _prepare_result(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare final workflow result.

        Args:
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Final result
        """
        output_mapping = self.output_schema or {}
        final_result = {}

        for output_key, source_key in output_mapping.items():
            if source_key in context['workflow_data']:
                final_result[output_key] = context['workflow_data'][source_key]

        return {
            'success': True,
            'workflow_data': context['workflow_data'],
            'step_results': context['step_results'],
            'output': final_result,
            'execution_context': {
                'steps_executed': len(context['step_results']),
                'total_steps': len(self.workflow_steps or [])
            }
        }

    def _update_execution_stats(self, success: bool) -> None:
        """Update execution statistics.

        Args:
            success (bool): Whether execution was successful
        """
        update_vals = {
            'last_execution': fields.Datetime.now(),
            'execution_count': self.execution_count + 1
        }

        if success:
            update_vals['success_count'] = self.success_count + 1
        else:
            update_vals['failure_count'] = self.failure_count + 1

        self.write(update_vals)

    @api.model
    def execute_workflow_by_code(self, workflow_code: str, input_data: Dict[str, Any],
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Public method to execute workflow by code.

        Args:
            workflow_code (str): Workflow code
            input_data (Dict[str, Any]): Input data
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Workflow execution result

        Example:
            result = self.env['oudu.bot.workflow'].execute_workflow_by_code(
                'customer_onboarding',
                {'customer_name': 'John Doe', 'email': 'john@example.com'},
                {'company_id': 1}
            )
        """
        workflow = self.search([('code', '=', workflow_code), ('is_active', '=', True)], limit=1)
        if not workflow:
            raise UserError(f"Workflow with code '{workflow_code}' not found or inactive")

        return workflow.execute_workflow(input_data, context)