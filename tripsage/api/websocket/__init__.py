"""WebSocket infrastructure utilities for the TripSage API.

This package contains the cohesive, final-only implementation of the
TripSage WebSocket router. Responsibilities are split across focused
modules for clarity:

- ``protocol`` defines typed outbound events.
- ``context`` declares lightweight connection context helpers.
- ``lifecycle`` contains handshake/origin/authentication flows.
- ``handlers`` implements message dispatch and domain actions.
- ``router`` exposes the FastAPI ``APIRouter``.

Modules exporting values intended for external use must be referenced from
this package's public namespace to preserve stable import paths.
"""

from __future__ import annotations

from tripsage.api.websocket.router import router


__all__ = ["router"]
