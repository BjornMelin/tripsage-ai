"""
Memory tools Pydantic models using modern 2.0 patterns.

This module defines all Pydantic models for memory operations with:
- Modern Annotated field types for better validation
- ConfigDict for proper model configuration
- Constrained types for reusability
- Comprehensive field validation
- JSON schema generation support
"""

from datetime import datetime
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# === CONSTRAINED TYPES FOR REUSABILITY ===

# Core identifier types
UserId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=255,
        description="User identifier",
        examples=["user_123", "uuid-abc-123"],
    ),
]

SessionId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=255,
        description="Session identifier",
        examples=["session_456", "chat_session_abc"],
    ),
]

# Search and query types
SearchQuery = Annotated[
    str,
    Field(
        min_length=1,
        max_length=500,
        description="Search query text",
        examples=["Paris hotels", "luxury travel preferences"],
    ),
]

ResultLimit = Annotated[
    int,
    Field(gt=0, le=100, description="Maximum number of results", examples=[5, 10, 20]),
]

MemoryCategory = Annotated[
    str,
    Field(
        min_length=1,
        max_length=50,
        description="Memory category",
        examples=["travel", "preferences", "destinations", "bookings"],
    ),
]

# Travel-specific constrained types
BudgetRange = Annotated[
    str,
    Field(
        pattern=r"^(low|medium|high|budget|luxury|\$[\d,]+-\$[\d,]+)$",
        description="Budget range - predefined values or dollar amounts",
        examples=["low", "high", "luxury", "$1,000-$5,000"],
    ),
]

TravelStyle = Annotated[
    str,
    Field(
        pattern=r"^(luxury|budget|adventure|cultural|business|family|solo|romantic)$",
        description="Travel style preference",
        examples=["luxury", "adventure", "family"],
    ),
]

# Content types
SummaryText = Annotated[str, Field(min_length=10, max_length=2000, description="Session summary text")]

InsightText = Annotated[
    str,
    Field(min_length=1, max_length=200, description="Individual insight or decision text"),
]

ContentText = Annotated[str, Field(min_length=1, description="Message content text")]

DestinationName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=100,
        description="Travel destination name",
        examples=["Paris", "Tokyo", "New York City"],
    ),
]

ActivityName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=100,
        description="Activity or interest name",
        examples=["hiking", "museums", "fine dining"],
    ),
]

# === CORE MEMORY MODELS ===


class ConversationMessage(BaseModel):
    """
    Message model for conversation memory using modern Pydantic 2.0 patterns.

    Features:
    - Literal role types for type safety
    - Automatic whitespace stripping
    - Optional timestamp with defaults
    - Validation on assignment
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=False,
        extra="forbid",
    )

    role: Literal["user", "assistant", "system"] = Field(
        description="Message role - must be user, assistant, or system"
    )
    content: ContentText = Field(description="Message content")
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp, auto-generated if not provided")


class UserPreferences(BaseModel):
    """
    User travel preferences model using modern Pydantic 2.0 patterns.

    Features:
    - Constrained types for validation
    - Field aliases for API compatibility
    - Extra field prevention
    - Rich field examples for documentation
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    user_id: UserId

    budget_range: Optional[BudgetRange] = Field(
        default=None,
        alias="budget",
        description="Preferred budget range (low/medium/high or dollar amounts)",
    )

    accommodation_type: Optional[str] = Field(
        default=None,
        alias="accommodation",
        description="Preferred accommodation type",
        examples=["hotel", "hostel", "airbnb", "resort", "apartment"],
    )

    travel_style: Optional[TravelStyle] = Field(default=None, description="Travel style preference")

    destinations: Optional[List[DestinationName]] = Field(default=None, description="Preferred travel destinations")

    activities: Optional[List[ActivityName]] = Field(default=None, description="Preferred activities and interests")

    dietary_restrictions: Optional[List[Annotated[str, Field(min_length=1)]]] = Field(
        default=None,
        description="Dietary restrictions and requirements",
        examples=[["vegetarian", "gluten-free"], ["kosher"], ["vegan"]],
    )

    accessibility_needs: Optional[List[Annotated[str, Field(min_length=1)]]] = Field(
        default=None,
        description="Accessibility requirements",
        examples=[
            ["wheelchair accessible"],
            ["hearing assistance"],
            ["visual assistance"],
        ],
    )


class MemorySearchQuery(BaseModel):
    """
    Memory search query model using modern Pydantic 2.0 patterns.

    Features:
    - Constrained search parameters
    - Semantic search optimization
    - Category filtering support
    - Result limit validation
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: SearchQuery
    user_id: UserId
    limit: ResultLimit = Field(default=5)
    category_filter: Optional[MemoryCategory] = Field(
        default=None,
        description=("Filter memories by category (e.g., 'travel', 'preferences', 'destinations')"),
    )


class TravelMemoryQuery(BaseModel):
    """
    Travel-specific memory search query model.

    Features:
    - Travel domain optimization
    - API alias support for convenience
    - Same validation as MemorySearchQuery
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: SearchQuery
    user_id: UserId
    limit: ResultLimit = Field(default=5)
    category: Optional[MemoryCategory] = Field(
        default=None,
        alias="category_filter",
        description="Memory category filter for travel-specific searches",
    )


class SessionSummary(BaseModel):
    """
    Session summary model for memory storage using modern Pydantic 2.0 patterns.

    Features:
    - Validated summary content
    - Structured insights and decisions
    - Session metadata tracking
    - Content length validation
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    user_id: UserId
    session_id: SessionId
    summary: SummaryText

    key_insights: Optional[List[InsightText]] = Field(
        default=None,
        description="Key insights extracted from the session",
        examples=[
            ["User prefers luxury hotels", "Budget is flexible for special occasions"],
            [
                "Looking for family-friendly destinations",
                "Needs wheelchair accessibility",
            ],
        ],
    )

    decisions_made: Optional[List[InsightText]] = Field(
        default=None,
        description="Important decisions made during the session",
        examples=[
            ["Decided on Paris for honeymoon", "Will book in June"],
            ["Chose all-inclusive resort option", "Confirmed dates for March"],
        ],
    )
