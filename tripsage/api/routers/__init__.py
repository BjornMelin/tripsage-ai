"""API routers for the TripSage API.

This package contains FastAPI router modules organized by domain.
"""

from importlib import import_module
from typing import TYPE_CHECKING


__all__ = [
    "accommodations",
    "activities",
    "attachments",
    "auth",
    "chat",
    "config",
    "dashboard",
    "destinations",
    "flights",
    "health",
    "itineraries",
    "memory",
    "search",
    "trips",
    "users",
]

if TYPE_CHECKING:
    from . import (
        accommodations,
        activities,
        attachments,
        auth,
        chat,
        config,
        dashboard,
        destinations,
        flights,
        health,
        itineraries,
        memory,
        search,
        trips,
        users,
    )

for _module_name in __all__:
    globals()[_module_name] = import_module(f".{_module_name}", __name__)
