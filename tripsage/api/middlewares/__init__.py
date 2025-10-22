"""Middleware components for the TripSage API.

This package contains middleware components for request processing,
including authentication, logging, and rate limiting.
"""

from .authentication import AuthenticationMiddleware, Principal
from .logging import LoggingMiddleware


__all__ = [
    "AuthenticationMiddleware",
    "LoggingMiddleware",
    "Principal",
]
