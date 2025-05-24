"""
Supabase MCP Wrapper implementation.

This wrapper provides a standardized interface for the external Supabase MCP server,
mapping user-friendly method names to actual Supabase MCP tools. Unlike internal
clients, this wrapper works through the external MCP server protocol.
"""

from typing import Any, Dict, List

from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class ExternalMCPClient:
    """Mock client for external MCP servers that delegates to the external process."""

    def __init__(self, mcp_name: str, config: Any):
        self.mcp_name = mcp_name
        self.config = config
        self.enabled = config.enabled if config else False
        logger.info(f"Initialized external MCP client for {mcp_name}")

    def __getattr__(self, name: str):
        """
        Handle any method call by returning a coroutine that raises NotImplementedError.

        This is a placeholder for external MCP server communication.
        In a complete implementation, this would communicate with the
        external server process.
        """

        async def external_call(*args, **kwargs):
            raise NotImplementedError(
                f"External MCP server communication not yet implemented for "
                f"{self.mcp_name}.{name}. This requires setting up the MCP protocol "
                f"communication with the external server process."
            )

        return external_call


class SupabaseMCPWrapper(BaseMCPWrapper):
    """Wrapper for the external Supabase MCP server."""

    def __init__(self, client: Any = None, mcp_name: str = "supabase"):
        """
        Initialize the Supabase MCP wrapper.

        For external MCP servers, we don't create a real client connection.
        Instead, we create a mock client that holds configuration.

        Args:
            client: Optional pre-initialized client (ignored for external servers)
            mcp_name: Name identifier for this MCP service
        """
        # Get configuration for validation and metadata
        config = mcp_settings.supabase

        if not config.enabled:
            raise ValueError("Supabase MCP is not enabled in configuration")

        if not config.access_token:
            raise ValueError("Supabase MCP requires an access token to be configured")

        # Create a mock client for external servers
        mock_client = ExternalMCPClient(mcp_name, config)
        super().__init__(mock_client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to external Supabase MCP tool names

        Based on the Supabase MCP server documentation, these are the available tools.
        The map goes from user-friendly names to actual MCP tool names.

        Returns:
            Dictionary mapping standard names to actual MCP tool names
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
            # Cost management
            "get_cost": "get_cost",
            "confirm_cost": "confirm_cost",
            # Database operations
            "list_tables": "list_tables",
            "execute_sql": "execute_sql",
            "apply_migration": "apply_migration",
            "list_migrations": "list_migrations",
            # Extensions
            "list_extensions": "list_extensions",
            # Edge Functions
            "list_edge_functions": "list_edge_functions",
            "deploy_edge_function": "deploy_edge_function",
            # Logs
            "get_logs": "get_logs",
            # Project configuration
            "get_project_url": "get_project_url",
            "get_anon_key": "get_anon_key",
            "generate_typescript_types": "generate_typescript_types",
            # Database branching (experimental)
            "create_branch": "create_branch",
            "list_branches": "list_branches",
            "delete_branch": "delete_branch",
            "merge_branch": "merge_branch",
            "reset_branch": "reset_branch",
            "rebase_branch": "rebase_branch",
            # Convenience aliases for common operations
            "select_data": "execute_sql",  # Use execute_sql with SELECT
            "insert_data": "execute_sql",  # Use execute_sql with INSERT
            "update_data": "execute_sql",  # Use execute_sql with UPDATE
            "delete_data": "execute_sql",  # Use execute_sql with DELETE
            "run_sql": "execute_sql",  # Alternative name for execute_sql
            "query": "execute_sql",  # Alternative name for execute_sql
            # Project operations
            "start_project": "restore_project",  # Alternative name
            "stop_project": "pause_project",  # Alternative name
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names for Supabase MCP.

        Returns:
            List of available method names that can be used with this wrapper
        """
        return list(self._method_map.keys())
