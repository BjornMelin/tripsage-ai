"""
Base MCP Client implementation for TripSage.

This module provides the base class for all MCP clients in the TripSage system,
with common functionality for tool calling and error handling.
"""

import enum
import json
from typing import Any, Dict, Generic, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..cache.redis_cache import redis_cache
from ..utils.error_handling import MCPError
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Type definitions for better type checking
P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


class ErrorCategory(enum.Enum):
    """Standardized error categories for MCP clients."""
    
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    NOT_FOUND = "not_found"
    CLIENT = "client"
    UNKNOWN = "unknown"


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
    
    @staticmethod
    def _categorize_error(error: Exception, status_code: Optional[int] = None) -> ErrorCategory:
        """Categorize an error based on type and status code.
        
        Args:
            error: The exception that occurred
            status_code: HTTP status code if available
            
        Returns:
            ErrorCategory enum value
        """
        error_message = str(error).lower()
        
        # Check error type first
        if isinstance(error, ValidationError):
            return ErrorCategory.VALIDATION
        elif isinstance(error, httpx.TimeoutException):
            return ErrorCategory.TIMEOUT
        elif isinstance(error, httpx.ConnectError):
            return ErrorCategory.NETWORK
        elif isinstance(error, httpx.HTTPStatusError):
            # Use status code from the HTTPStatusError
            status_code = error.response.status_code
        
        # Check status code if available
        if status_code is not None:
            if status_code == 400:
                return ErrorCategory.VALIDATION
            elif status_code == 401:
                return ErrorCategory.AUTHENTICATION
            elif status_code == 403:
                return ErrorCategory.AUTHORIZATION
            elif status_code == 404:
                return ErrorCategory.NOT_FOUND
            elif status_code == 429:
                return ErrorCategory.RATE_LIMIT
            elif 500 <= status_code < 600:
                return ErrorCategory.SERVER
            
        # Check error message for keywords
        if any(keyword in error_message for keyword in 
               ["timeout", "timed out", "deadline exceeded"]):
            return ErrorCategory.TIMEOUT
        elif any(keyword in error_message for keyword in 
                 ["network", "connection", "connect", "dns", "socket"]):
            return ErrorCategory.NETWORK
        elif any(keyword in error_message for keyword in 
                 ["auth", "token", "credential", "password", "login"]):
            return ErrorCategory.AUTHENTICATION
        elif any(keyword in error_message for keyword in 
                 ["permission", "access", "forbidden", "denied"]):
            return ErrorCategory.AUTHORIZATION
        elif any(keyword in error_message for keyword in 
                 ["rate limit", "too many requests", "throttle"]):
            return ErrorCategory.RATE_LIMIT
        elif any(keyword in error_message for keyword in 
                 ["not found", "missing", "does not exist"]):
            return ErrorCategory.NOT_FOUND
        elif any(keyword in error_message for keyword in 
                 ["server", "internal", "service"]):
            return ErrorCategory.SERVER
        elif any(keyword in error_message for keyword in 
                 ["invalid", "schema", "format", "validate"]):
            return ErrorCategory.VALIDATION
        elif any(keyword in error_message for keyword in 
                 ["config", "endpoint", "parameter", "setting"]):
            return ErrorCategory.CONFIGURATION
            
        # Default to client error if none of the above
        return ErrorCategory.CLIENT

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
            error_category = self._categorize_error(e)
            logger.error(
                "%s error calling %s tool: %s", 
                error_category.value, 
                tool_name, 
                str(e)
            )
            raise MCPError(
                message=f"{error_category.value.capitalize()} error: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
                category=error_category.value,
            ) from e
        except httpx.HTTPStatusError as e:
            error_category = self._categorize_error(e, e.response.status_code)
            logger.error(
                "%s error calling %s tool: %s - %s",
                error_category.value,
                tool_name,
                e.response.status_code,
                e.response.text,
            )
            raise MCPError(
                message=f"{error_category.value.capitalize()} error ({e.response.status_code}): {e.response.text}",
                server=self.server_name,
                tool=tool_name,
                params=params,
                category=error_category.value,
                status_code=e.response.status_code,
            ) from e
        except Exception as e:
            error_category = self._categorize_error(e)
            logger.error(
                "%s error calling %s tool: %s", 
                error_category.value, 
                tool_name, 
                str(e)
            )
            raise MCPError(
                message=f"{error_category.value.capitalize()} error: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
                category=error_category.value,
            ) from e

    async def _call_validate_tool(
        self,
        tool_name: str,
        params_model: Type[P],
        response_model: Type[R],
        raw_params: Dict[str, Any],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Validate parameters, call a tool, and validate the response.

        Args:
            tool_name: Name of the tool to call
            params_model: Pydantic model type for validating parameters
            response_model: Pydantic model type for validating the response
            raw_params: Dictionary of raw parameters for the tool
            skip_cache: Whether to skip the cache
            cache_key: Optional cache key
            cache_ttl: Optional cache TTL

        Returns:
            Validated response

        Raises:
            MCPError: If parameter validation fails, the request fails,
                      or response validation fails.
        """
        validated_params = None
        params_dict = None
        
        try:
            # 1. Validate parameters first
            try:
                validated_params = params_model.model_validate(raw_params)
                params_dict = validated_params.model_dump(exclude_none=True)
            except ValidationError as e:
                logger.error(f"Parameter validation failed for {tool_name}: {str(e)}")
                raise MCPError(
                    message=f"Invalid parameters for {tool_name}: {str(e)}",
                    server=self.server_name,
                    tool=tool_name,
                    params=raw_params,
                    category=ErrorCategory.VALIDATION.value,
                ) from e

            # 2. Call the tool using validated params dictionary
            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # 3. Parse response if it's a string
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError as e:
                    raise MCPError(
                        message=f"Invalid JSON response from {tool_name}: {str(e)}",
                        server=self.server_name,
                        tool=tool_name,
                        params=params_dict,
                        category=ErrorCategory.VALIDATION.value,
                    ) from e

            # 4. Validate response
            try:
                # Attempt strict validation
                validated_response = response_model.model_validate(response)
                return validated_response
            except ValidationError:
                # Try non-strict validation as fallback
                try:
                    validated_response = response_model.model_validate(
                        response, strict=False
                    )
                    logger.warning(
                        f"Non-strict validation used for {tool_name} response"
                    )
                    return validated_response
                except ValidationError as e:
                    logger.error(f"Validation error in {tool_name} response: {str(e)}")
                    raise MCPError(
                        message=f"Invalid response from {tool_name}: {str(e)}",
                        server=self.server_name,
                        tool=tool_name,
                        params=params_dict,
                        category=ErrorCategory.VALIDATION.value,
                    ) from e

        except MCPError:
            # Re-raise MCPError without modification
            raise
        except Exception as e:
            # Handle any other unexpected errors
            error_category = self._categorize_error(e)
            logger.error(f"Error calling {tool_name}: {str(e)}")
            
            # Handle both Pydantic v1 and v2
            params_serialized = raw_params
            if validated_params is not None:
                params_serialized = (
                    validated_params.model_dump()
                    if hasattr(validated_params, "model_dump")
                    else validated_params.dict()
                    if hasattr(validated_params, "dict")
                    else validated_params
                )

            raise MCPError(
                message=f"Failed to call {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params_serialized,
                category=error_category.value,
            ) from e
