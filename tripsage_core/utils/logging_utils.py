"""Logging utilities for TripSage Core.

This module provides standardized logging setup for the TripSage application.
It configures loggers with appropriate handlers and formatters, and provides
a function to get a configured logger for a module.
"""

import logging
import sys
from collections.abc import MutableMapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from tripsage_core.config import get_settings


# Cache of loggers to avoid creating multiple loggers for the same module
_loggers: dict[str, logging.Logger] = {}


class ContextAdapter(logging.LoggerAdapter[logging.Logger]):
    """Adapter that adds context information to log records."""

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Process the log record by adding context information.

        Args:
            msg: The log message
            kwargs: Keyword arguments for the logger

        Returns:
            Tuple of (modified message, modified kwargs)
        """
        # Extract extra context if provided
        context: dict[str, Any] = {}
        if self.extra and isinstance(self.extra, dict):
            context_value = self.extra.get("context")
            if isinstance(context_value, dict):
                context = cast(dict[str, Any], context_value)

        # Add context to extra if provided
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Update kwargs extra with context
        extra_dict = cast(dict[str, Any], kwargs["extra"])
        extra_dict.update(_redact_sensitive(context))

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
    level: int | None = None,
    log_to_file: bool = True,
    log_dir: str = "logs",
    context: dict[str, Any] | None = None,
) -> ContextAdapter:
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

    # Avoid clearing handlers to respect global configuration
    if not logger.handlers:
        # Create console handler once
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    # Ensure console handler level aligns
    for h in logger.handlers:
        h.setLevel(level)

    # Add file handler if requested and not in testing
    settings = get_settings()
    if log_to_file and not settings.is_testing:
        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Create a log file with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d")
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
    name: str, level: int | None = None, context: dict[str, Any] | None = None
) -> logging.Logger | ContextAdapter:
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


def configure_root_logger(level: int | None = None) -> None:
    """Configure the root logger.

    Args:
        level: The log level to use (defaults to settings)
    """
    if level is None:
        level = _get_log_level()

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


# Utility function for structured logging
def log_exception(
    logger: logging.Logger,
    exception: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """Log an exception with context.

    Args:
        logger: The logger instance
        exception: The exception to log
        context: Optional context information
    """
    extra = {"exception_type": type(exception).__name__}
    if context:
        extra.update(_redact_sensitive(context))

    logger.exception("Exception occurred", extra=extra)


def _redact_sensitive(data: dict[str, Any] | None) -> dict[str, Any]:
    """Redact sensitive fields like 'api_key' in nested structures.

    Args:
        data: Arbitrary context dict.

    Returns:
        A shallow-copied dict with sensitive values redacted.
    """

    def _sanitize(value: Any) -> Any:
        """Sanitize a value."""
        if isinstance(value, dict):
            d: dict[str, Any] = cast(dict[str, Any], value)
            return {str(k): _sanitize(v) for k, v in d.items()}
        if isinstance(value, list):
            lst: list[Any] = cast(list[Any], value)
            return [_sanitize(v) for v in lst]
        return value

    redacted_keys: set[str] = {"api_key", "apikey", "authorization"}
    out: dict[str, Any] = {}
    src: dict[str, Any] = data or {}
    for k, v in src.items():
        k_str: str = str(k)
        if k_str.lower() in redacted_keys:
            out[k_str] = "[REDACTED]"
        else:
            out[k_str] = _sanitize(v)
    return out
