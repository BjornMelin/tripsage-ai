"""
Base MCP Client implementation for TripSage.

This module provides the base class for all MCP clients in the TripSage system,
with common functionality for tool calling and error handling.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type, Union

import httpx

from ..cache.redis_cache import redis_cache
from ..utils.error_handling import APIError, MCPError, log_exception
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)


class BaseMCPClient:
    """Base class for all MCP clients in TripSage."""

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ):
        """Initialize the MCP client.

        Args:
            endpoint: MCP server endpoint URL
            api_key: API key for authentication (if required)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds (None means default TTL)
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl

        logger.debug("Initialized MCP client for %s", endpoint)

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests.

        Returns:
            HTTP headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the MCP server.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (will be appended to endpoint)
            data: Request body data
            params: Query parameters

        Returns:
            Response data as a dictionary

        Raises:
            MCPError: If the request fails
        """
        url = f"{self.endpoint.rstrip('/')}/{path.lstrip('/')}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(
                        url, headers=headers, params=params, timeout=self.timeout
                    )
                elif method == "POST":
                    response = await client.post(
                        url,
                        headers=headers,
                        json=data,
                        params=params,
                        timeout=self.timeout,
                    )
                elif method == "PUT":
                    response = await client.put(
                        url,
                        headers=headers,
                        json=data,
                        params=params,
                        timeout=self.timeout,
                    )
                elif method == "DELETE":
                    response = await client.delete(
                        url, headers=headers, params=params, timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            # Try to parse error response
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                if isinstance(error_data, dict) and "detail" in error_data:
                    error_detail = error_data["detail"]
                elif isinstance(error_data, dict) and "message" in error_data:
                    error_detail = error_data["message"]
            except Exception:
                error_detail = e.response.text or str(e)

            raise MCPError(
                message=f"MCP request failed: {error_detail}",
                server=self.endpoint,
                tool=path,
                params={"method": method, "params": params},
            )

        except httpx.RequestError as e:
            raise MCPError(
                message=f"MCP request error: {str(e)}",
                server=self.endpoint,
                tool=path,
                params={"method": method, "params": params},
            )

        except Exception as e:
            raise MCPError(
                message=f"Unexpected error in MCP request: {str(e)}",
                server=self.endpoint,
                tool=path,
                params={"method": method, "params": params},
            )

    @redis_cache.cached("mcp_tools", 3600)  # Cache tool list for 1 hour
    async def list_tools(self, skip_cache: bool = False) -> List[Dict[str, str]]:
        """List all available tools.

        Args:
            skip_cache: Whether to skip the cache

        Returns:
            List of tool metadata
        """
        response = await self._make_request("GET", "/tools")
        return response.get("tools", [])

    @redis_cache.cached("mcp_tool_metadata", 3600)  # Cache tool metadata for 1 hour
    async def get_tool_metadata(
        self, tool_name: str, skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get metadata for a specific tool.

        Args:
            tool_name: Tool name
            skip_cache: Whether to skip the cache

        Returns:
            Tool metadata
        """
        return await self._make_request("GET", f"/tools/{tool_name}")

    async def call_tool(
        self, tool_name: str, params: Dict[str, Any], skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Tool name
            params: Tool parameters
            skip_cache: Whether to skip the cache

        Returns:
            Tool execution result
        """
        cache_key = f"mcp_tool_{tool_name}"

        # Check if we should use the cache
        if self.use_cache and not skip_cache:
            # Generate a cache key based on tool name and parameters
            cache_key = redis_cache.cache_key(cache_key, **params)
            cached_result = await redis_cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit for tool %s", tool_name)
                return cached_result

        # Call the tool
        logger.debug("Calling tool %s with params %s", tool_name, params)
        result = await self._make_request(
            "POST", f"/api/v1/tools/{tool_name}/call", data={"params": params}
        )

        # Cache the result if appropriate
        if self.use_cache and not skip_cache:
            await redis_cache.set(cache_key, result, self.cache_ttl)

        return result
