"""
Memory MCP server.

This module is a placeholder for the official Neo4j Memory MCP server.
The actual MCP server is now provided by the mcp-neo4j-memory package.
"""

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# The actual Memory MCP server is now provided by the mcp-neo4j-memory package.
# To run the server:
# python -m mcp_neo4j_memory --port 3008
#
# This file is kept as a placeholder for backward compatibility and documentation.

if __name__ == "__main__":
    logger.info(
        "The Memory MCP server is now provided by the mcp-neo4j-memory package. "
        "To run the server: python -m mcp_neo4j_memory --port 3008"
    )