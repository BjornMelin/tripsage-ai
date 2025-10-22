"""State schema definitions for TripSage LangGraph orchestration.

This module defines the unified state schema used across all agent nodes
in the LangGraph-based orchestration system, enhanced for clarity and maintainability.
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from langgraph.graph import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class UserPreferences(BaseModel):
    """User travel preferences and constraints."""

    model_config = ConfigDict(extra="forbid")

    budget_total: float | None = None
    budget_currency: str = "USD"
    preferred_airlines: list[str] = Field(default_factory=list)
    seat_class: Literal["economy", "business", "first"] | None = None
    accommodation_type: Literal["hotel", "rental", "hostel", "resort"] | None = None
    meal_preferences: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)
    travel_style: Literal["budget", "comfort", "luxury"] | None = None


class TravelDates(BaseModel):
    """Travel date information."""

    model_config = ConfigDict(extra="forbid")

    departure_date: str | None = None  # YYYY-MM-DD format
    return_date: str | None = None  # YYYY-MM-DD format
    flexible_dates: bool = False
    date_range_days: int | None = None  # Flexibility range in days


class DestinationInfo(BaseModel):
    """Destination information and context."""

    model_config = ConfigDict(extra="forbid")

    origin: str | None = None
    destination: str | None = None
    intermediate_stops: list[str] = Field(default_factory=list)
    trip_type: Literal["one_way", "round_trip", "multi_city"] | None = None
    purpose: (
        Literal["business", "leisure", "family", "honeymoon", "adventure"] | None
    ) = None


class SearchResult(BaseModel):
    """Generic search result structure."""

    model_config = ConfigDict(extra="forbid")

    search_id: str
    timestamp: str
    agent: str
    parameters: dict[str, Any]
    results: list[dict[str, Any]]
    result_count: int
    status: Literal["success", "error", "partial"]
    error_message: str | None = None


class BookingProgress(BaseModel):
    """Booking progress tracking."""

    model_config = ConfigDict(extra="forbid")

    flight_booking: dict[str, Any] | None = None
    accommodation_booking: dict[str, Any] | None = None
    activity_bookings: list[dict[str, Any]] = Field(default_factory=list)
    total_cost: float | None = None
    currency: str = "USD"
    status: Literal["planning", "comparing", "booking", "confirmed", "cancelled"] = (
        "planning"
    )


class HandoffContext(BaseModel):
    """Agent handoff context information."""

    model_config = ConfigDict(extra="forbid")

    from_agent: str
    to_agent: str
    routing_confidence: float
    routing_reasoning: str
    timestamp: str
    message_analyzed: str
    additional_context: dict[str, Any] = Field(default_factory=dict)


class ErrorInfo(BaseModel):
    """Error tracking information."""

    model_config = ConfigDict(extra="forbid")

    error_count: int = 0
    last_error: str | None = None
    retry_attempts: dict[str, int] = Field(default_factory=dict)
    error_history: list[dict[str, Any]] = Field(default_factory=list)


class ToolCallInfo(BaseModel):
    """Tool call tracking information."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    timestamp: str
    parameters: dict[str, Any]
    result: dict[str, Any] | None = None
    status: Literal["pending", "success", "error"] = "pending"
    error_message: str | None = None
    execution_time_ms: float | None = None


class TravelPlanningState(TypedDict):
    """Unified state schema for all travel planning workflows.

    This state is passed between all agent nodes and contains all the context
    needed for travel planning conversations and operations. Includes
    structured data models for better type safety and clarity.

    State Design Principles:
    - Comprehensive: Contains all necessary information for agent decisions
    - Type-safe: Uses structured models for complex data
    - Traceable: Tracks agent history and tool usage
    - Resilient: Includes error handling and recovery information
    - Scalable: Can be extended without breaking existing agents
    """

    # Core conversation data - handled by LangGraph add_messages
    messages: Annotated[list[dict[str, Any]], add_messages]
    user_id: str
    session_id: str

    # Structured user context (using Pydantic models for validation)
    user_preferences: dict[str, Any] | None  # Serialized UserPreferences
    travel_dates: dict[str, Any] | None  # Serialized TravelDates
    destination_info: dict[str, Any] | None  # Serialized DestinationInfo

    # Search results with structured tracking
    flight_searches: list[dict[str, Any]]  # List of SearchResult dicts
    accommodation_searches: list[dict[str, Any]]  # List of SearchResult dicts
    activity_searches: list[dict[str, Any]]  # List of SearchResult dicts
    budget_analyses: list[dict[str, Any]]  # Budget analysis records
    destination_research: list[dict[str, Any]]  # Destination research outputs
    itineraries: list[dict[str, Any]]  # Planned itineraries

    # Booking progress tracking
    booking_progress: dict[str, Any] | None  # Serialized BookingProgress

    # Agent orchestration and routing
    current_agent: str | None
    agent_history: list[str]
    handoff_context: dict[str, Any] | None  # Serialized HandoffContext

    # Error handling and resilience improvements
    error_info: dict[str, Any]  # Serialized ErrorInfo

    # Tool execution tracking with detailed information
    active_tool_calls: list[dict[str, Any]]  # List of ToolCallInfo dicts
    completed_tool_calls: list[dict[str, Any]]  # List of ToolCallInfo dicts

    # Memory and context enhancement
    conversation_summary: str | None  # LLM-generated summary for long conversations
    extracted_entities: dict[str, Any]  # Named entities extracted from conversation
    user_intent: str | None  # Current identified user intent
    confidence_score: float | None  # Confidence in current routing/intent

    # Session lifecycle management
    created_at: str | None
    updated_at: str | None
    last_activity: str | None
    is_active: bool


def create_initial_state(
    user_id: str, message: str, session_id: str | None = None
) -> TravelPlanningState:
    """Create an initial state for a new conversation.

    Args:
        user_id: Unique identifier for the user
        message: Initial user message
        session_id: Optional session ID (generated if not provided)

    Returns:
        Initial TravelPlanningState with default values and enhanced structure
    """
    now = datetime.now(UTC).isoformat()

    return TravelPlanningState(
        # Core conversation data
        messages=[{"role": "user", "content": message, "timestamp": now}],
        user_id=user_id,
        session_id=session_id
        or f"session_{user_id}_{int(datetime.now(UTC).timestamp())}",
        # Structured user context (initialized as None, populated during conversation)
        user_preferences=None,
        travel_dates=None,
        destination_info=None,
        # Search state (empty lists, populated by agent actions)
        flight_searches=[],
        accommodation_searches=[],
        activity_searches=[],
        budget_analyses=[],
        destination_research=[],
        itineraries=[],
        booking_progress=None,
        # Agent coordination (starts with router)
        current_agent=None,
        agent_history=[],
        handoff_context=None,
        # Error handling using structured ErrorInfo
        error_info=ErrorInfo().model_dump(),
        # Tool call tracking (empty initially)
        active_tool_calls=[],
        completed_tool_calls=[],
        # Memory and context enhancement
        conversation_summary=None,
        extracted_entities={},
        user_intent=None,
        confidence_score=None,
        # Session lifecycle management
        created_at=now,
        updated_at=now,
        last_activity=now,
        is_active=True,
    )


def update_state_timestamp(state: TravelPlanningState) -> TravelPlanningState:
    """Update the state's timestamp to current time.

    Args:
        state: Current state to update

    Returns:
        State with updated timestamp
    """
    state["updated_at"] = datetime.now(UTC).isoformat()
    return state
