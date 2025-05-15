"""
Neo4j Memory MCP Wrapper implementation.

This wrapper provides a standardized interface for the Neo4j Memory MCP client,
mapping user-friendly method names to actual Neo4j Memory MCP client methods.
"""

from typing import Dict, List

from src.mcp.memory.client import MemoryMCPClient
from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class Neo4jMemoryMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Neo4j Memory MCP client."""

    def __init__(self, client: MemoryMCPClient = None, mcp_name: str = "neo4j_memory"):
        """
        Initialize the Neo4j Memory MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            config = mcp_settings.neo4j_memory
            if config.enabled:
                # Construct the endpoint URL from config values
                scheme = config.scheme
                host = config.host
                port = config.port
                endpoint = f"{scheme}://{host}:{port}"

                client = MemoryMCPClient(
                    endpoint=endpoint,
                    api_key=config.password.get_secret_value()
                    if config.password
                    else None,
                    timeout=config.timeout,
                    use_cache=config.retry_attempts > 0,
                )
            else:
                raise ValueError("Neo4j Memory MCP is not enabled in configuration")
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Entity operations
            "add_node": "create_entities",
            "create_node": "create_entities",
            "create_entities": "create_entities",
            # Relationship operations
            "add_relationship": "create_relations",
            "create_relationship": "create_relations",
            "create_relations": "create_relations",
            # Query operations
            "get_node": "open_nodes",
            "open_nodes": "open_nodes",
            "search_nodes": "search_nodes",
            "query_graph": "search_nodes",
            # Graph operations
            "read_graph": "read_graph",
            "get_graph": "read_graph",
            "get_memory_summary": "read_graph",
            # Observation operations
            "add_observations": "add_observations",
            # Delete operations
            "delete_entities": "delete_entities",
            "delete_nodes": "delete_entities",
            "delete_relations": "delete_relations",
            "delete_relationships": "delete_relations",
            "delete_observations": "delete_observations",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
