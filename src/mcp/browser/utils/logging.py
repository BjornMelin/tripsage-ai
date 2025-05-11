"""Logging utilities for the Browser MCP server."""

import json
import logging
from typing import Any, Dict, Optional, Union

# Import from the main utils logging if available, otherwise create our own
try:
    from src.utils.logging import get_logger
except ImportError:
    # Set up logging if the main utility is not available
    def get_logger(name: str) -> logging.Logger:
        """Get a logger with the given name.

        Args:
            name: Logger name

        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)

        # Configure if not already configured
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger


def log_request(
    logger: logging.Logger, function_name: str, params: Dict[str, Any]
) -> None:
    """Log an MCP tool request.

    Args:
        logger: Logger to use
        function_name: Name of the MCP function being called
        params: Function parameters
    """
    # Create a sanitized copy of params for logging
    sanitized_params = _sanitize_params(params)

    logger.info(f"MCP Tool Request: {function_name} - {json.dumps(sanitized_params)}")


def log_response(
    logger: logging.Logger, function_name: str, response: Dict[str, Any]
) -> None:
    """Log an MCP tool response.

    Args:
        logger: Logger to use
        function_name: Name of the MCP function being called
        response: Function response
    """
    # Create a sanitized copy of response for logging
    sanitized_response = _sanitize_response(response)

    logger.info(
        f"MCP Tool Response: {function_name} - {json.dumps(sanitized_response)}"
    )


def log_error(
    logger: logging.Logger,
    function_name: str,
    error: Union[str, Exception],
    params: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an MCP tool error.

    Args:
        logger: Logger to use
        function_name: Name of the MCP function being called
        error: Error message or exception
        params: Function parameters
    """
    error_message = str(error)

    if params:
        sanitized_params = _sanitize_params(params)
        logger.error(
            f"MCP Tool Error: {function_name} - {error_message} - Params: {json.dumps(sanitized_params)}"
        )
    else:
        logger.error(f"MCP Tool Error: {function_name} - {error_message}")


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize request parameters for logging.

    Removes sensitive information like passwords and long values.

    Args:
        params: Original parameters

    Returns:
        Sanitized parameters
    """
    if not params:
        return {}

    sanitized = {}

    # List of parameter names that may contain sensitive information
    sensitive_keys = {
        "password",
        "token",
        "api_key",
        "secret",
        "auth",
        "credential",
        "confirmation_code",
        "last_name",
        "first_name",
    }

    # List of parameter types that should be truncated
    truncate_types = (str,)

    for key, value in params.items():
        # Handle sensitive fields
        if any(sensitive_word in key.lower() for sensitive_word in sensitive_keys):
            sanitized[key] = "***REDACTED***"

        # Handle nested dictionaries
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_params(value)

        # Handle lists
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                # List of dictionaries
                sanitized[key] = [
                    _sanitize_params(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Regular list
                sanitized[key] = value

        # Truncate long string values
        elif isinstance(value, truncate_types) and len(str(value)) > 100:
            sanitized[key] = str(value)[:100] + "..."

        # Keep other values as is
        else:
            sanitized[key] = value

    return sanitized


def _sanitize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize response data for logging.

    Removes binary data and truncates long values.

    Args:
        response: Original response

    Returns:
        Sanitized response
    """
    if not response:
        return {}

    sanitized = {}

    # Fields that may contain binary data
    binary_fields = {"screenshot", "image", "pdf", "binary"}

    # Fields that may contain sensitive information
    sensitive_keys = {
        "password",
        "token",
        "api_key",
        "secret",
        "auth",
        "credential",
        "confirmation_code",
    }

    for key, value in response.items():
        # Handle binary data
        if key in binary_fields and value:
            sanitized[key] = "<binary data>"

        # Handle sensitive fields
        elif any(sensitive_word in key.lower() for sensitive_word in sensitive_keys):
            sanitized[key] = "***REDACTED***"

        # Handle nested dictionaries
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_response(value)

        # Handle lists
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                # List of dictionaries
                sanitized[key] = [
                    _sanitize_response(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Regular list
                sanitized[key] = value

        # Truncate long string values
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = value[:100] + "..."

        # Keep other values as is
        else:
            sanitized[key] = value

    return sanitized
