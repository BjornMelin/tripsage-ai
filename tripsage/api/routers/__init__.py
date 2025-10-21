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
    "dashboard_realtime",
    "destinations",
    "flights",
    "health",
    "itineraries",
    "keys",
    "memory",
    "search",
    "trips",
    "users",
    "websocket",
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
        dashboard_realtime,
        destinations,
        flights,
        health,
        itineraries,
        keys,
        memory,
        search,
        trips,
        users,
        websocket,
    )

for _module_name in __all__:
    globals()[_module_name] = import_module(f".{_module_name}", __name__)
