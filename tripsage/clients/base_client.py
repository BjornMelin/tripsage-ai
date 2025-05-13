"""
Base MCP client implementation for TripSage.

This module provides the base client class for connecting to MCP servers
and standardizes error handling and request/response processing.
"""

from typing import Any, Dict, List, Optional

import httpx

from tripsage.utils.error_handling import MCPError, log_exception
from tripsage.utils.logging import get_module_logger
from tripsage.utils.settings import get_settings

logger = get_module_logger(__name__)
settings = get_settings()


class BaseMCPClient:
    """Base class for all MCP clients in TripSage.

    This class provides common functionality for MCP clients, including:
    - Connection management
    - Request processing and error handling
    - Tool discovery and invocation
    - Metadata handling
    """

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        server_name: str = "mcp-server",
    ):
        """Initialize the MCP client.

        Args:
            endpoint: MCP server endpoint URL
            api_key: Optional API key for authentication
            server_name: Human-readable name for the MCP server
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.server_name = server_name
        self.tools_cache: Dict[str, Dict[str, Any]] = {}
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the client connection and retrieve available tools."""
        if self.client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Create HTTP client with persistent connection
            self.client = httpx.AsyncClient(
                base_url=self.endpoint,
                headers=headers,
                timeout=httpx.Timeout(30.0),  # 30 second timeout
            )

            # Cache available tools
            try:
                await self.refresh_tools_cache()
                tool_count = len(self.tools_cache)
                logger.info(
                    f"Initialized {self.server_name} MCP client with {tool_count} tools"
                )
            except Exception as e:
                logger.error(f"Error initializing MCP client: {str(e)}")
                log_exception(e)

    async def close(self) -> None:
        """Close the client connection."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug(f"Closed {self.server_name} MCP client connection")

    async def refresh_tools_cache(self) -> None:
        """Refresh the cache of available tools."""
        tools = await self._fetch_available_tools()
        self.tools_cache = {tool["name"]: tool for tool in tools}

    async def _fetch_available_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from the MCP server."""
        try:
            if not self.client:
                await self.initialize()

            response = await self.client.get("/tools")
            response.raise_for_status()

            return response.json().get("tools", [])
        except Exception as e:
            logger.error(f"Error fetching available tools: {str(e)}")
            log_exception(e)
            return []

    async def list_tools(self) -> List[str]:
        """List available tools from the MCP server.

        Returns:
            List of tool names
        """
        if not self.tools_cache:
            await self.refresh_tools_cache()

        return list(self.tools_cache.keys())

    def list_tools_sync(self) -> List[str]:
        """Synchronous version of list_tools for compatibility with agents.

        Returns:
            List of tool names
        """
        if not self.tools_cache:
            return []

        return list(self.tools_cache.keys())

    async def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata dictionary or None if not found
        """
        if not self.tools_cache:
            await self.refresh_tools_cache()

        return self.tools_cache.get(tool_name)

    def get_tool_metadata_sync(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of get_tool_metadata for compatibility with agents.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata dictionary or None if not found
        """
        return self.tools_cache.get(tool_name)

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            params: Parameters to pass to the tool

        Returns:
            Tool response dictionary

        Raises:
            MCPError: If the tool call fails
        """
        try:
            if not self.client:
                await self.initialize()

            # Verify tool exists
            if tool_name not in self.tools_cache:
                tools = await self.list_tools()
                if tool_name not in tools:
                    raise MCPError(
                        f"Tool {tool_name} not found on {self.server_name}",
                        server=self.server_name,
                        tool=tool_name,
                        category="not_found",
                    )

            # Make the request
            url = f"/tools/{tool_name}"
            response = await self.client.post(
                url,
                json={"params": params},
                timeout=httpx.Timeout(60.0),  # Longer timeout for tool calls
            )

            if response.status_code != 200:
                error_message = "Unknown error"
                try:
                    error_json = response.json()
                    error_message = error_json.get("error", "Unknown error")
                except Exception:
                    error_message = response.text or "Unknown error"

                raise MCPError(
                    f"Error calling tool {tool_name}: {error_message}",
                    server=self.server_name,
                    tool=tool_name,
                    params=params,
                    category="tool_error",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            error_message = f"HTTP error calling tool {tool_name}: {str(e)}"
            logger.error(error_message)
            raise MCPError(
                error_message,
                server=self.server_name,
                tool=tool_name,
                params=params,
                category="http_error",
            ) from e

        except MCPError:
            # Re-raise existing MCPError
            raise

        except Exception as e:
            error_message = f"Error calling tool {tool_name}: {str(e)}"
            logger.error(error_message)
            log_exception(e)
            raise MCPError(
                error_message,
                server=self.server_name,
                tool=tool_name,
                params=params,
                category="general_error",
            ) from e
