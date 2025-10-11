from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from typing import Dict, Any, List, Optional, Tuple
import json
import logging

_logger = logging.getLogger(__name__)


class AIAgent(models.Model):
    _name = 'oudu.bot.agent'
    _description = 'AI Agent Configuration'
    _order = 'sequence, name'

    # Sequence and Identification
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(
        string='Agent Name',
        required=True,
        help="Display name for the AI agent"
    )
    code = fields.Char(
        string='Agent Code',
        required=True,
        help="Internal code for system reference"
    )

    # Provider Configuration
    provider_id = fields.Many2one(
        'oudu.bot.provider',
        string='AI Provider',
        required=True,
        domain="[('is_active', '=', True)]",
        help="AI service provider for this agent"
    )
    model_name = fields.Char(
        string='Model Name',
        required=True,
        default='deepseek-chat',
        help="Specific model to use from the provider"
    )

    # Prompt Configuration
    system_prompt = fields.Text(
        string='System Prompt',
        help="System-level instructions for the AI agent"
    )
    prompt_template = fields.Text(
        string='Prompt Template',
        help="Template for generating prompts with variables"
    )

    # Capabilities Configuration
    tools_ids = fields.Many2many(
        'oudu.bot.tool',
        string='Available Tools',
        help="Tools that this agent can use"
    )
    knowledge_base_ids = fields.Many2many(
        'knowledge.article',
        string='Knowledge Article',
        help="Knowledge Article for information retrieval"
    )

    # Model Parameters
    temperature = fields.Float(
        string='Temperature',
        default=0.7,
        help="Controls randomness (0 = deterministic, 2 = creative)"
    )
    max_tokens = fields.Integer(
        string='Max Tokens',
        default=2000,
        help="Maximum tokens in response"
    )
    top_p = fields.Float(
        string='Top P',
        default=0.9,
        help="Nucleus sampling parameter"
    )

    # Feature Flags
    enable_tool_calling = fields.Boolean(
        string='Enable Tool Calling',
        default=True,
        help="Allow agent to call external tools"
    )
    enable_knowledge_retrieval = fields.Boolean(
        string='Enable Knowledge Retrieval',
        default=True,
        help="Allow agent to search knowledge bases"
    )
    enable_reasoning = fields.Boolean(
        string='Enable Reasoning',
        default=True,
        help="Enable complex reasoning capabilities"
    )
    allow_auto_execution = fields.Boolean(
        string='Allow Auto Execution',
        default=False,
        help="Allow automatic execution of tool calls"
    )

    # Workflow Integration - 修复这个字段
    workflow_ids = fields.One2many(
        'oudu.bot.workflow',
        'agent_id',
        string='Workflows',
        help="Workflows associated with this agent"
    )

    # Status and Monitoring
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="Enable or disable this agent"
    )
    last_execution = fields.Datetime(
        string='Last Execution',
        help="When this agent was last executed"
    )
    execution_count = fields.Integer(
        string='Execution Count',
        default=0,
        help="Number of times this agent has been executed"
    )

    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Agent name must be unique!'),
        ('code_unique', 'unique(code)', 'Agent code must be unique!'),
    ]

    @api.constrains('temperature')
    def _check_temperature(self) -> None:
        """Validate temperature range."""
        for record in self:
            if record.temperature < 0 or record.temperature > 2:
                raise ValidationError("Temperature must be between 0 and 2")

    # 添加一个计算字段来避免 web_read 问题
    workflow_count = fields.Integer(
        string='Workflow Count',
        compute='_compute_workflow_count',
        store=False
    )

    @api.depends('workflow_ids')
    def _compute_workflow_count(self):
        """计算关联的工作流数量"""
        for record in self:
            record.workflow_count = len(record.workflow_ids)

    def _build_messages(self, user_input: str, context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """Build conversation messages for AI request.

        Args:
            user_input (str): User's input message
            context (Dict[str, Any]): Additional context information

        Returns:
            List[Dict[str, str]]: Formatted messages for AI API
        """
        context = context or {}
        messages: List[Dict[str, str]] = []

        # System prompt
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # Add context information
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            messages.append({
                "role": "system",
                "content": f"Context Information:\n{context_str}"
            })

        # Add knowledge base information if enabled
        if self.enable_knowledge_retrieval and self.knowledge_base_ids:
            knowledge_context = self._get_knowledge_context(user_input)
            if knowledge_context:
                messages.append({
                    "role": "system",
                    "content": f"Relevant Knowledge:\n{knowledge_context}"
                })

        # User input
        messages.append({
            "role": "user",
            "content": user_input
        })

        return messages

    def _get_knowledge_context(self, query: str) -> Optional[str]:
        """Retrieve relevant knowledge from knowledge bases.

        Args:
            query (str): Search query

        Returns:
            Optional[str]: Relevant knowledge content
        """
        try:
            # This is a simplified implementation
            # In practice, you would use more sophisticated search
            knowledge_contents = []

            for knowledge_base in self.knowledge_base_ids:
                # Search in knowledge base articles
                articles = self.env['knowledge.article'].search([
                    ('root_article_id', '=', knowledge_base.id),
                    ('body', 'ilike', query)
                ], limit=3)

                for article in articles:
                    knowledge_contents.append(f"Title: {article.name}\nContent: {article.body}")

            return "\n\n".join(knowledge_contents) if knowledge_contents else None

        except Exception as e:
            _logger.error(f"Knowledge retrieval failed: {str(e)}")
            return None

    def execute(self, user_input: str, context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Execute the AI agent with user input.

        Args:
            user_input (str): User's input message
            context (Dict[str, Any]): Additional context
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: Execution result
        """
        try:
            context = context or {}

            # Build messages
            messages: List[Dict[str, str]] = self._build_messages(user_input, context)

            # Prepare API parameters
            api_kwargs = {
                'model': self.model_name,
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'temperature': kwargs.get('temperature', self.temperature),
                'top_p': kwargs.get('top_p', self.top_p),
            }

            # Add tools if enabled
            if self.enable_tool_calling and self.tools_ids:
                api_kwargs['tools'] = [
                    tool.get_tool_schema() for tool in self.tools_ids
                ]
                api_kwargs['tool_choice'] = 'auto'

            # Make API call
            response: Dict[str, Any] = self.provider_id.get_chat_completion(messages, **api_kwargs)

            # Process response
            result: Dict[str, Any] = self._process_response(response, context)

            # Update execution statistics
            self.write({
                'last_execution': fields.Datetime.now(),
                'execution_count': self.execution_count + 1
            })

            return result

        except Exception as e:
            _logger.error(f"AI agent execution failed: {str(e)}")
            raise UserError(f"AI agent execution failed: {str(e)}")

    def _process_response(self, response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI response and handle tool calls.

        Args:
            response (Dict[str, Any]): Raw API response
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Processed result
        """
        if not response.get('choices'):
            raise UserError("No response received from AI provider")

        message = response['choices'][0]['message']
        result: Dict[str, Any] = {
            'content': message.get('content', ''),
            'raw_response': response,
            'tool_calls': []
        }

        # Handle tool calls
        if message.get('tool_calls'):
            tool_results = []
            for tool_call in message['tool_calls']:
                tool_result = self._execute_tool_call(tool_call, context)
                tool_results.append(tool_result)

            result['tool_calls'] = tool_results

        return result

    def _execute_tool_call(self, tool_call: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call from AI response.

        Args:
            tool_call (Dict[str, Any]): Tool call specification
            context (Dict[str, Any]): Execution context

        Returns:
            Dict[str, Any]: Tool execution result
        """
        try:
            tool_name = tool_call['function']['name']
            arguments = json.loads(tool_call['function']['arguments'])

            # Find the tool
            tool = self.tools_ids.filtered(lambda t: t.function_name == tool_name)
            if not tool:
                raise UserError(f"Tool not found: {tool_name}")

            # Execute tool
            tool_result = tool.execute_tool(arguments, context)

            return {
                'tool_name': tool_name,
                'arguments': arguments,
                'result': tool_result,
                'success': True
            }

        except Exception as e:
            _logger.error(f"Tool execution failed: {str(e)}")
            return {
                'tool_name': tool_name,
                'arguments': arguments,
                'result': str(e),
                'success': False
            }

    @api.model
    def call_ai_agent(self, agent_code: str, user_input: str, context: Dict[str, Any] = None, **kwargs) -> Dict[
        str, Any]:
        """Public method to call AI agent from other models.

        Args:
            agent_code (str): Code of the agent to call
            user_input (str): Input message for the agent
            context (Dict[str, Any]): Additional context
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: Agent execution result

        Example:
            result = self.env['oudu.bot.agent'].call_ai_agent(
                'sales_assistant',
                'Help me create a sales order',
                {'partner_id': 1, 'order_type': 'sale'}
            )
        """
        agent = self.search([('code', '=', agent_code), ('is_active', '=', True)], limit=1)
        if not agent:
            raise UserError(f"AI Agent with code '{agent_code}' not found or inactive")

        return agent.execute(user_input, context, **kwargs)

    def action_view_workflows(self):
        """View workflows associated with this agent."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Workflows - {self.name}',
            'res_model': 'oudu.bot.workflow',
            'view_mode': 'list,form',
            'domain': [('agent_id', '=', self.id)],
            'context': {'default_agent_id': self.id}
        }