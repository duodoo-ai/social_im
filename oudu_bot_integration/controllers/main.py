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
        """Test connection to AI provider."""
        try:
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

    @http.route('/oudu_bot/generate_text', type='json', auth='user', methods=['POST'])
    def generate_text(self, provider_code: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using AI provider."""
        try:
            result = request.env['oudu.bot.provider'].call_ai_provider(provider_code, prompt, **kwargs)

            return {
                'success': True,
                'result': result
            }

        except Exception as e:
            _logger.error(f"Text generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/execute_tool', type='json', auth='user', methods=['POST'])
    def execute_tool(self, tool_code: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool."""
        try:
            result = request.env['oudu.bot.tool'].call_tool(tool_code, arguments or {})

            return {
                'success': True,
                'result': result
            }

        except Exception as e:
            _logger.error(f"Tool execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/get_providers', type='json', auth='user', methods=['POST'])
    def get_providers(self) -> Dict[str, Any]:
        """Get list of available providers."""
        try:
            providers = request.env['oudu.bot.provider'].search([('is_active', '=', True)])
            provider_list = []
            for provider in providers:
                provider_list.append({
                    'id': provider.id,
                    'name': provider.name,
                    'code': provider.code,
                    'provider_type': provider.provider_type,
                    'default_model': provider.default_model
                })

            return {
                'success': True,
                'providers': provider_list
            }

        except Exception as e:
            _logger.error(f"Failed to get providers: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/oudu_bot/get_tools', type='json', auth='user', methods=['POST'])
    def get_tools(self) -> Dict[str, Any]:
        """Get list of available tools."""
        try:
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
        """Health check endpoint."""
        try:
            # Check database connection
            request.env.cr.execute("SELECT 1")

            # Check active providers
            active_providers = request.env['oudu.bot.provider'].search_count([
                ('is_active', '=', True)
            ])

            return {
                'success': True,
                'status': 'healthy',
                'database': 'connected',
                'active_providers': active_providers,
                'timestamp': fields.Datetime.now().isoformat()
            }

        except Exception as e:
            _logger.error(f"Health check failed: {str(e)}")
            return {
                'success': False,
                'status': 'unhealthy',
                'error': str(e)
            }