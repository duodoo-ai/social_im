from odoo import http, fields
from odoo.http import request, Response
from typing import Dict, Any, Optional
import json
import logging

_logger = logging.getLogger(__name__)


class OduBotIntegrationController(http.Controller):
    """Main controller for OUDU Bot Integration"""

    @http.route('/oudu_bot/test_connection', type='json', auth='user', methods=['POST'])
    def test_connection(self, provider_id: int) -> Dict[str, Any]:
        """Test connection to AI provider.

        Args:
            provider_id (int): ID of the provider to test

        Returns:
            Dict[str, Any]: Test result
        """
        try:
            if not request.env.user.has_group('oudu_bot_integration.group_ai_user'):
                return {
                    'success': False,
                    'error': 'Insufficient permissions'
                }

            provider = request.env['oudu.bot.provider'].browse(provider_id)
            if not provider.exists():
                return {
                    'success': False,
                    'error': 'Provider not found'
                }

            result = provider.test_connection()
            return {
                'success': result,
                'message': 'Connection test successful' if result else 'Connection test failed'
            }

        except Exception as e:
            _logger.error(f"Connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/execute_agent', type='json', auth='user', methods=['POST'])
    def execute_agent(self, agent_code: str, user_input: str,
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an AI agent.

        Args:
            agent_code (str): Code of the agent to execute
            user_input (str): User input for the agent
            context (Optional[Dict[str, Any]]): Additional context

        Returns:
            Dict[str, Any]: Execution result
        """
        try:
            if not request.env.user.has_group('oudu_bot_integration.group_ai_user'):
                return {
                    'success': False,
                    'error': 'Insufficient permissions'
                }

            context = context or {}
            result = request.env['oudu.bot.agent'].call_ai_agent(agent_code, user_input, context)

            return {
                'success': True,
                'result': result
            }

        except Exception as e:
            _logger.error(f"Agent execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/execute_workflow', type='json', auth='user', methods=['POST'])
    def execute_workflow(self, workflow_code: str, input_data: Dict[str, Any],
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow_code (str): Code of the workflow to execute
            input_data (Dict[str, Any]): Input data for the workflow
            context (Optional[Dict[str, Any]]): Additional context

        Returns:
            Dict[str, Any]: Execution result
        """
        try:
            if not request.env.user.has_group('oudu_bot_integration.group_ai_user'):
                return {
                    'success': False,
                    'error': 'Insufficient permissions'
                }

            context = context or {}
            result = request.env['oudu.bot.workflow'].execute_workflow_by_code(
                workflow_code, input_data, context
            )

            return {
                'success': True,
                'result': result
            }

        except Exception as e:
            _logger.error(f"Workflow execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/get_agents', type='json', auth='user', methods=['POST'])
    def get_agents(self) -> Dict[str, Any]:
        """Get list of available agents.

        Returns:
            Dict[str, Any]: List of agents
        """
        try:
            if not request.env.user.has_group('oudu_bot_integration.group_ai_user'):
                return {
                    'success': False,
                    'error': 'Insufficient permissions'
                }

            agents = request.env['oudu.bot.agent'].search([('is_active', '=', True)])
            agent_list = []
            for agent in agents:
                agent_list.append({
                    'id': agent.id,
                    'name': agent.name,
                    'code': agent.code,
                    'description': agent.system_prompt[:100] + '...' if agent.system_prompt else '',
                    'provider': agent.provider_id.name
                })

            return {
                'success': True,
                'agents': agent_list
            }

        except Exception as e:
            _logger.error(f"Failed to get agents: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/get_tools', type='json', auth='user', methods=['POST'])
    def get_tools(self) -> Dict[str, Any]:
        """Get list of available tools.

        Returns:
            Dict[str, Any]: List of tools
        """
        try:
            if not request.env.user.has_group('oudu_bot_integration.group_ai_user'):
                return {
                    'success': False,
                    'error': 'Insufficient permissions'
                }

            tools = request.env['oudu.bot.tool'].search([('is_active', '=', True)])
            tool_list = []
            for tool in tools:
                tool_list.append({
                    'id': tool.id,
                    'name': tool.name,
                    'code': tool.code,
                    'description': tool.description,
                    'function_name': tool.function_name,
                    'tool_type': tool.tool_type
                })

            return {
                'success': True,
                'tools': tool_list
            }

        except Exception as e:
            _logger.error(f"Failed to get tools: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/health', type='json', auth='public', methods=['GET'])
    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint.

        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Check database connection
            request.env.cr.execute("SELECT 1")

            # Check active providers
            active_providers = request.env['oudu.bot.provider'].search_count([
                ('is_active', '=', True)
            ])

            # Check active agents
            active_agents = request.env['oudu.bot.agent'].search_count([
                ('is_active', '=', True)
            ])

            return {
                'success': True,
                'status': 'healthy',
                'database': 'connected',
                'active_providers': active_providers,
                'active_agents': active_agents,
                'timestamp': fields.Datetime.now().isoformat()
            }

        except Exception as e:
            _logger.error(f"Health check failed: {str(e)}")
            return {
                'success': False,
                'status': 'unhealthy',
                'error': str(e)
            }