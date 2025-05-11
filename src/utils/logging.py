"""
Logging utility for TripSage.

This module provides a standardized logging setup for the TripSage application.
It configures loggers with appropriate handlers and formatters, and provides
a function to get a configured logger for a module.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Define log levels
DEFAULT_LOG_LEVEL = logging.INFO


def configure_logging(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_dir: str = "logs",
) -> logging.Logger:
    """Configure and return a logger with standardized settings.

    Args:
        name: The name of the logger, typically __name__
        level: The logging level to set
        log_to_file: Whether to log to a file in addition to console
        log_dir: Directory to store log files

    Returns:
        A configured logger instance
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
        log_filename = (
            f"{name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        log_path = Path(log_dir) / log_filename

        file_handler = logging.FileHandler(log_path)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_module_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    This is a convenience function that should be used in each module:

    ```python
    from utils.logging import get_module_logger
    logger = get_module_logger(__name__)
    ```

    Args:
        name: The name of the module, typically __name__

    Returns:
        A configured logger instance
    """
    return configure_logging(name)
