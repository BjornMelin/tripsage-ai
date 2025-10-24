"""Trip API request schemas.

Defines query parameter bundlers and request models for trip endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel


class TripSearchParams(BaseModel):
    """Query parameters for trip search endpoints.

    Attributes:
        q: Optional free-text query.
        status: Optional filter by status.
        skip: Offset for pagination.
        limit: Page size for pagination.
    """

    q: str | None = None
    status: str | None = None
    skip: int = 0
    limit: int = 10
