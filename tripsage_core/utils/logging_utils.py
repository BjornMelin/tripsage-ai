"""
Logging utilities for TripSage Core.

This module provides standardized logging setup for the TripSage application.
It configures loggers with appropriate handlers and formatters, and provides
a function to get a configured logger for a module.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from tripsage_core.config import get_settings

# Cache of loggers to avoid creating multiple loggers for the same module
_loggers: Dict[str, logging.Logger] = {}


class ContextAdapter(logging.LoggerAdapter):
    """Adapter that adds context information to log records."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process the log record by adding context information.

        Args:
            msg: The log message
            kwargs: Keyword arguments for the logger

        Returns:
            Tuple of (modified message, modified kwargs)
        """
        # Extract extra context if provided
        context = self.extra.get("context", {})

        # Add context to extra if provided
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Update extra with context
        kwargs["extra"].update(context)

        return msg, kwargs


def _get_log_level() -> int:
    """Get the log level from settings."""
    settings = get_settings()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(settings.log_level.upper(), logging.INFO)


def configure_logging(
    name: str,
    level: Optional[int] = None,
    log_to_file: bool = True,
    log_dir: str = "logs",
    context: Optional[Dict[str, Any]] = None,
) -> logging.LoggerAdapter:
    """Configure and return a logger with standardized settings.

    Args:
        name: The name of the logger, typically __name__
        level: The logging level to set (defaults to settings)
        log_to_file: Whether to log to a file in addition to console
        log_dir: Directory to store log files
        context: Optional context information to include in logs

    Returns:
        A configured logger adapter instance
    """
    if level is None:
        level = _get_log_level()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Add file handler if requested and not in testing
    settings = get_settings()
    if log_to_file and not settings.is_testing:
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Create a log file with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        log_filename = f"{name.replace('.', '_')}_{timestamp}.log"
        log_path = Path(log_dir) / log_filename

        file_handler = logging.FileHandler(log_path)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Create and return a logger adapter with context
    return ContextAdapter(logger, {"context": context or {}})


def get_logger(
    name: str, level: Optional[int] = None, context: Optional[Dict[str, Any]] = None
) -> Union[logging.Logger, logging.LoggerAdapter]:
    """Get a logger for a module.

    This is a convenience function that should be used in each module:

    ```python
    from tripsage_core.utils.logging_utils import get_logger
    logger = get_logger(__name__)
    ```

    Or with context:

    ```python
    logger = get_logger(__name__, context={"service": "webcrawl"})
    ```

    Args:
        name: The name of the module, typically __name__
        level: Optional log level to set
        context: Optional context information to include in logs

    Returns:
        A configured logger or logger adapter instance
    """
    if level is None:
        level = _get_log_level()

    if context:
        # Always create a new adapter when context is provided
        logger = logging.getLogger(name)
        if logger.level == logging.NOTSET:
            logger.setLevel(level)

        return ContextAdapter(logger, {"context": context})

    # Use cached logger if no context
    if name not in _loggers:
        logger = logging.getLogger(name)

        if logger.level == logging.NOTSET:
            logger.setLevel(level)

        _loggers[name] = logger

    return _loggers[name]


def configure_root_logger(level: Optional[int] = None) -> None:
    """Configure the root logger.

    Args:
        level: The log level to use (defaults to settings)
    """
    if level is None:
        level = _get_log_level()

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure root logger
    root_logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)


# Utility function for structured logging
def log_exception(
    logger: logging.Logger,
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an exception with context.

    Args:
        logger: The logger instance
        exception: The exception to log
        context: Optional context information
    """
    extra = {"exception_type": type(exception).__name__}
    if context:
        extra.update(context)

    logger.error(
        f"Exception occurred: {str(exception)}",
        exc_info=True,
        extra=extra,
    )
