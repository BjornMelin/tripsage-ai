"""
Base MCP Client implementation for TripSage.

This module provides the base class for all MCP clients in the TripSage system,
with common functionality for tool calling and error handling.
"""

import json
from typing import Any, Dict, Generic, Optional, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..cache.redis_cache import redis_cache
from ..utils.error_handling import MCPError
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)

P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


class BaseMCPClient(Generic[P, R]):
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
        self.server_name = (
            "MCP"  # Default server name, should be overridden by subclasses
        )

        logger.debug("Initialized MCP client for %s", endpoint)

    def _get_headers(self) -> Dict[str, str]:
        """Get the HTTP headers for MCP API requests.

        Returns:
            Dictionary containing HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> Any:
        """Call an MCP tool with parameters.

        Args:
            tool_name: The name of the tool to call
            params: Parameters to pass to the tool
            skip_cache: Whether to skip the cache and force a fresh request
            cache_key: Optional custom cache key
            cache_ttl: Optional cache TTL that overrides the default

        Returns:
            Response data from the MCP server

        Raises:
            MCPError: If the tool call fails
        """
        url = f"{self.endpoint}/tools/{tool_name}"
        headers = self._get_headers()

        # Generate cache key if needed
        if cache_key is None and self.use_cache and not skip_cache:
            cache_key = (
                f"{self.server_name}:{tool_name}:{json.dumps(params, sort_keys=True)}"
            )

        # Check cache if enabled
        if self.use_cache and not skip_cache:
            cached_result = await redis_cache.get(cache_key)
            if cached_result:
                logger.debug("Cache hit for %s tool call", tool_name)
                return cached_result

        # Make the API request
        try:
            logger.debug("Calling %s tool with params: %s", tool_name, params)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=params, headers=headers)
                response.raise_for_status()
                result = response.json()

            # Cache the result if needed
            if self.use_cache and not skip_cache:
                ttl = cache_ttl or self.cache_ttl
                await redis_cache.set(cache_key, result, ttl)

            return result
        except httpx.RequestError as e:
            logger.error("Request error calling %s tool: %s", tool_name, str(e))
            raise MCPError(
                message=f"Request error: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error calling %s tool: %s - %s",
                tool_name,
                e.response.status_code,
                e.response.text,
            )
            raise MCPError(
                message=f"HTTP error {e.response.status_code}: {e.response.text}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e
        except Exception as e:
            logger.error("Error calling %s tool: %s", tool_name, str(e))
            raise MCPError(
                message=f"Error: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: P,
        response_model: type[R],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Call a tool and validate both parameters and response.

        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool call (Pydantic model)
            response_model: Pydantic model for validating the response
            skip_cache: Whether to skip the cache
            cache_key: Optional cache key
            cache_ttl: Optional cache TTL

        Returns:
            Validated response

        Raises:
            MCPError: If the request fails
        """
        try:
            # Convert parameters to dict
            params_dict = (
                params.model_dump(by_alias=True)
                if hasattr(params, "model_dump")
                else params.dict(by_alias=True)
            )

            # Call the tool
            response = await self.call_tool(
                tool_name,
                {"params": params_dict},
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            try:
                # Attempt strict validation
                if hasattr(response_model, "model_validate"):
                    # Pydantic v2
                    validated_response = response_model.model_validate(response)
                else:
                    # Pydantic v1
                    validated_response = response_model.parse_obj(response)
            except ValidationError:
                # Fallback to non-strict validation if strict fails
                try:
                    if hasattr(response_model, "model_validate"):
                        # Pydantic v2
                        validated_response = response_model.model_validate(
                            response, strict=False
                        )
                    else:
                        # Pydantic v1
                        validated_response = response_model.parse_obj(response)

                    logger.warning(
                        f"Non-strict validation used for {tool_name} response"
                    )
                except ValidationError as e:
                    logger.error(f"Validation error in {tool_name} response: {str(e)}")
                    raise MCPError(
                        message=f"Invalid response from {tool_name}: {str(e)}",
                        server=self.server_name,
                        tool=tool_name,
                        params=params_dict,
                    ) from e

            return validated_response
        except Exception as e:
            if not isinstance(e, MCPError):
                logger.error(f"Error calling {tool_name}: {str(e)}")

                # Handle both Pydantic v1 and v2
                params_serialized = (
                    params.model_dump()
                    if hasattr(params, "model_dump")
                    else params.dict()
                    if hasattr(params, "dict")
                    else params
                )

                raise MCPError(
                    message=f"Failed to call {tool_name}: {str(e)}",
                    server=self.server_name,
                    tool=tool_name,
                    params=params_serialized,
                ) from e
            raise
