"""API routers for the TripSage API.

This package contains FastAPI router modules organized by domain.
"""

from importlib import import_module
from typing import TYPE_CHECKING


__all__ = [
    "attachments",
    "auth",
    "config",
    "dashboard",
    "destinations",
    "health",
    "itineraries",
    "memory",
    "search",
    "trips",
    "users",
]

if TYPE_CHECKING:
    from . import (
        attachments,
        auth,
        config,
        dashboard,
        destinations,
        health,
        itineraries,
        memory,
        search,
        trips,
        users,
    )

for _module_name in __all__:
    globals()[_module_name] = import_module(f".{_module_name}", __name__)
