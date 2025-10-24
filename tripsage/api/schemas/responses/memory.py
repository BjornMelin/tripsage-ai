"""Memory API response schemas.

Defines Pydantic response models used by the memory router.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tripsage_core.services.business.memory_service import MemorySearchResult


class MemorySearchResponse(BaseModel):
    """Response wrapper for memory search results.

    Attributes:
        results: List of search results.
        query: Original query string.
        total: Total results returned.
    """

    results: list[MemorySearchResult] = Field(description="Search results")
    query: str = Field(description="Original query string")
    total: int = Field(description="Total results returned")
