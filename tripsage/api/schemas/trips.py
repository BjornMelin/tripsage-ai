"""Trip API schemas (feature-first helper DTOs)."""

from __future__ import annotations

from pydantic import BaseModel


class TripSearchParams(BaseModel):
    """Query parameters for trip search endpoints."""

    q: str | None = None
    status: str | None = None
    skip: int = 0
    limit: int = 10
