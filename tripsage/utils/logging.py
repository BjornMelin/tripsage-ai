"""
Logging utilities for TripSage.

This module provides standardized logging setup for the TripSage application.
It configures loggers with appropriate handlers and formatters, and provides
a function to get a configured logger for a module.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Define log levels
DEFAULT_LOG_LEVEL = logging.INFO

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


def configure_logging(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_dir: str = "logs",
    context: Optional[Dict[str, Any]] = None,
) -> logging.LoggerAdapter:
    """Configure and return a logger with standardized settings.

    Args:
        name: The name of the logger, typically __name__
        level: The logging level to set
        log_to_file: Whether to log to a file in addition to console
        log_dir: Directory to store log files
        context: Optional context information to include in logs

    Returns:
        A configured logger adapter instance
    """
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

    # Add file handler if requested
    if log_to_file:
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Create a log file with timestamp
        timestamp = datetime.now(datetime.UTC).strftime("%Y%m%d")
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
    from tripsage.utils.logging import get_logger
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
    if context:
        # Always create a new adapter when context is provided
        logger = logging.getLogger(name)
        if level is not None:
            logger.setLevel(level)
        elif logger.level == logging.NOTSET:
            logger.setLevel(DEFAULT_LOG_LEVEL)

        return ContextAdapter(logger, {"context": context})

    # Use cached logger if no context
    if name not in _loggers:
        logger = logging.getLogger(name)

        if level is not None:
            logger.setLevel(level)
        elif logger.level == logging.NOTSET:
            logger.setLevel(DEFAULT_LOG_LEVEL)

        _loggers[name] = logger

    return _loggers[name]


def configure_root_logger(level: int = DEFAULT_LOG_LEVEL) -> None:
    """Configure the root logger.

    Args:
        level: The log level to use
    """
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
