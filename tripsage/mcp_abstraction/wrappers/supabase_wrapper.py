"""
Supabase MCP Wrapper implementation.

This wrapper provides a standardized interface for the Supabase MCP client,
mapping user-friendly method names to actual Supabase MCP client methods.
"""

from typing import Dict, List

from src.mcp.supabase.client import SupabaseMCPClient
from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class SupabaseMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Supabase MCP client."""

    def __init__(self, client: SupabaseMCPClient = None, mcp_name: str = "supabase"):
        """
        Initialize the Supabase MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            config = mcp_settings.supabase
            if config.enabled:
                client = SupabaseMCPClient(
                    endpoint=str(config.url),
                    api_key=(
                        config.api_key.get_secret_value() if config.api_key else None
                    ),
                    timeout=config.timeout,
                    use_cache=config.retry_attempts > 0,
                )
            else:
                raise ValueError("Supabase MCP is not enabled in configuration")
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Organization management
            "list_organizations": "list_organizations",
            "get_organization": "get_organization",
            # Project management
            "list_projects": "list_projects",
            "get_project": "get_project",
            "create_project": "create_project",
            "pause_project": "pause_project",
            "restore_project": "restore_project",
            # Database operations
            "list_tables": "list_tables",
            "execute_sql": "execute_sql",
            "apply_migration": "apply_migration",
            # Data operations
            "select_data": "execute_sql",  # Use execute_sql with SELECT
            "insert_data": "execute_sql",  # Use execute_sql with INSERT
            "update_data": "execute_sql",  # Use execute_sql with UPDATE
            "delete_data": "execute_sql",  # Use execute_sql with DELETE
            # RPC and functions
            "call_rpc": "execute_sql",  # Supabase RPCs can be called via SQL
            "list_edge_functions": "list_edge_functions",
            "deploy_edge_function": "deploy_edge_function",
            # Extensions
            "list_extensions": "list_extensions",
            # Migrations
            "list_migrations": "list_migrations",
            # Logs
            "get_logs": "get_logs",
            # Project details
            "get_project_url": "get_project_url",
            "get_anon_key": "get_anon_key",
            "generate_typescript_types": "generate_typescript_types",
            # Branches
            "create_branch": "create_branch",
            "list_branches": "list_branches",
            "delete_branch": "delete_branch",
            "merge_branch": "merge_branch",
            "reset_branch": "reset_branch",
            "rebase_branch": "rebase_branch",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
