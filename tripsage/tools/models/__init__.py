"""Memory tools models using modern Pydantic 2.0 patterns.

This module contains all the Pydantic models used by memory tools,
following best practices for maintainability and reusability.
"""

from .memory_models import (
    BudgetRange,
    ConversationMessage,
    MemoryCategory,
    MemorySearchQuery,
    ResultLimit,
    SearchQuery,
    SessionId,
    SessionSummary,
    SummaryText,
    TravelMemoryQuery,
    TravelStyle,
    # Type aliases for reuse
    UserId,
    UserPreferences,
)


__all__ = [
    "BudgetRange",
    "ConversationMessage",
    "MemoryCategory",
    "MemorySearchQuery",
    "ResultLimit",
    "SearchQuery",
    "SessionId",
    "SessionSummary",
    "SummaryText",
    "TravelMemoryQuery",
    "TravelStyle",
    "UserId",
    "UserPreferences",
]
