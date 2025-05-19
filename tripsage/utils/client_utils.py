"""
Client utilities for TripSage.

This module provides utility functions and classes for working with external MCPs,
including error handling, request formatting, and response parsing.
"""

import enum
import json
from typing import Any, Dict, Optional, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .error_handling import MCPError
from .logging import get_logger

logger = get_logger(__name__)

# Type definitions for better type checking
T = TypeVar("T", bound=BaseModel)


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


def categorize_error(
    error: Exception, status_code: Optional[int] = None
) -> ErrorCategory:
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
    if any(
        keyword in error_message
        for keyword in ["timeout", "timed out", "deadline exceeded"]
    ):
        return ErrorCategory.TIMEOUT
    elif any(
        keyword in error_message
        for keyword in ["network", "connection", "connect", "dns", "socket"]
    ):
        return ErrorCategory.NETWORK
    elif any(
        keyword in error_message
        for keyword in ["auth", "token", "credential", "password", "login"]
    ):
        return ErrorCategory.AUTHENTICATION
    elif any(
        keyword in error_message
        for keyword in ["permission", "access", "forbidden", "denied"]
    ):
        return ErrorCategory.AUTHORIZATION
    elif any(
        keyword in error_message
        for keyword in ["rate limit", "too many requests", "throttle"]
    ):
        return ErrorCategory.RATE_LIMIT
    elif any(
        keyword in error_message
        for keyword in ["not found", "missing", "does not exist"]
    ):
        return ErrorCategory.NOT_FOUND
    elif any(keyword in error_message for keyword in ["server", "internal", "service"]):
        return ErrorCategory.SERVER
    elif any(
        keyword in error_message
        for keyword in ["invalid", "schema", "format", "validate"]
    ):
        return ErrorCategory.VALIDATION
    elif any(
        keyword in error_message
        for keyword in ["config", "endpoint", "parameter", "setting"]
    ):
        return ErrorCategory.CONFIGURATION

    # Default to client error if none of the above
    return ErrorCategory.CLIENT


async def make_mcp_request(
    endpoint: str,
    tool_name: str,
    params: Dict[str, Any],
    timeout: float = 60.0,
    api_key: Optional[str] = None,
    server_name: str = "External MCP",
) -> Dict[str, Any]:
    """Make a request to an MCP server.

    Args:
        endpoint: MCP server endpoint URL
        tool_name: The name of the tool to call
        params: Parameters to pass to the tool
        timeout: Request timeout in seconds
        api_key: API key for authentication (if required)
        server_name: Server name for error reporting

    Returns:
        Response data from the MCP server

    Raises:
        MCPError: If the tool call fails
    """
    url = f"{endpoint}/tools/{tool_name}"

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Make the API request
    try:
        logger.debug("Calling %s tool with params: %s", tool_name, params)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=params, headers=headers)
            response.raise_for_status()
            result = response.json()
        return result

    except httpx.RequestError as e:
        error_category = categorize_error(e)
        logger.error(
            "%s error calling %s tool: %s", error_category.value, tool_name, str(e)
        )
        raise MCPError(
            message=f"{error_category.value.capitalize()} error: {str(e)}",
            server=server_name,
            tool=tool_name,
            params=params,
            category=error_category.value,
        ) from e
    except httpx.HTTPStatusError as e:
        error_category = categorize_error(e, e.response.status_code)
        logger.error(
            "%s error calling %s tool: %s - %s",
            error_category.value,
            tool_name,
            e.response.status_code,
            e.response.text,
        )
        raise MCPError(
            message=(
                f"{error_category.value.capitalize()} error "
                f"({e.response.status_code}): {e.response.text}"
            ),
            server=server_name,
            tool=tool_name,
            params=params,
            category=error_category.value,
            status_code=e.response.status_code,
        ) from e
    except Exception as e:
        error_category = categorize_error(e)
        logger.error(
            "%s error calling %s tool: %s", error_category.value, tool_name, str(e)
        )
        raise MCPError(
            message=f"{error_category.value.capitalize()} error: {str(e)}",
            server=server_name,
            tool=tool_name,
            params=params,
            category=error_category.value,
        ) from e


async def validate_and_call_mcp_tool(
    endpoint: str,
    tool_name: str,
    params: Dict[str, Any],
    response_model: type[T],
    timeout: float = 60.0,
    api_key: Optional[str] = None,
    server_name: str = "External MCP",
) -> T:
    """Make a request to an MCP server with model validation.

    Args:
        endpoint: MCP server endpoint URL
        tool_name: The name of the tool to call
        params: Parameters to pass to the tool
        response_model: Pydantic model to validate response
        timeout: Request timeout in seconds
        api_key: API key for authentication (if required)
        server_name: Server name for error reporting

    Returns:
        Validated response model instance

    Raises:
        MCPError: If the tool call fails or validation fails
    """
    try:
        # Call the MCP tool
        response = await make_mcp_request(
            endpoint=endpoint,
            tool_name=tool_name,
            params=params,
            timeout=timeout,
            api_key=api_key,
            server_name=server_name,
        )

        # Parse response if it's a string
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError as e:
                raise MCPError(
                    message=f"Invalid JSON response from {tool_name}: {str(e)}",
                    server=server_name,
                    tool=tool_name,
                    params=params,
                    category=ErrorCategory.VALIDATION.value,
                ) from e

        # Validate response
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
                logger.warning(f"Non-strict validation used for {tool_name} response")
                return validated_response
            except ValidationError as e:
                logger.error(f"Validation error in {tool_name} response: {str(e)}")
                raise MCPError(
                    message=f"Invalid response from {tool_name}: {str(e)}",
                    server=server_name,
                    tool=tool_name,
                    params=params,
                    category=ErrorCategory.VALIDATION.value,
                ) from e

    except MCPError:
        # Re-raise MCPError without modification
        raise
    except Exception as e:
        # Handle any other unexpected errors
        error_category = categorize_error(e)
        logger.error(f"Error calling {tool_name}: {str(e)}")

        raise MCPError(
            message=f"Failed to call {tool_name}: {str(e)}",
            server=server_name,
            tool=tool_name,
            params=params,
            category=error_category.value,
        ) from e
