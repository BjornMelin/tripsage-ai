"""
State schema definitions for TripSage LangGraph orchestration.

This module defines the unified state schema used across all agent nodes
in the LangGraph-based orchestration system, enhanced for clarity and maintainability.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict


class UserPreferences(BaseModel):
    """User travel preferences and constraints."""

    budget_total: Optional[float] = None
    budget_currency: str = "USD"
    preferred_airlines: List[str] = Field(default_factory=list)
    seat_class: Optional[Literal["economy", "business", "first"]] = None
    accommodation_type: Optional[Literal["hotel", "rental", "hostel", "resort"]] = None
    meal_preferences: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)
    travel_style: Optional[Literal["budget", "comfort", "luxury"]] = None


class TravelDates(BaseModel):
    """Travel date information."""

    departure_date: Optional[str] = None  # YYYY-MM-DD format
    return_date: Optional[str] = None  # YYYY-MM-DD format
    flexible_dates: bool = False
    date_range_days: Optional[int] = None  # Flexibility range in days


class DestinationInfo(BaseModel):
    """Destination information and context."""

    origin: Optional[str] = None
    destination: Optional[str] = None
    intermediate_stops: List[str] = Field(default_factory=list)
    trip_type: Optional[Literal["one_way", "round_trip", "multi_city"]] = None
    purpose: Optional[
        Literal["business", "leisure", "family", "honeymoon", "adventure"]
    ] = None


class SearchResult(BaseModel):
    """Generic search result structure."""

    search_id: str
    timestamp: str
    agent: str
    parameters: Dict[str, Any]
    results: List[Dict[str, Any]]
    result_count: int
    status: Literal["success", "error", "partial"]
    error_message: Optional[str] = None


class BookingProgress(BaseModel):
    """Booking progress tracking."""

    flight_booking: Optional[Dict[str, Any]] = None
    accommodation_booking: Optional[Dict[str, Any]] = None
    activity_bookings: List[Dict[str, Any]] = Field(default_factory=list)
    total_cost: Optional[float] = None
    currency: str = "USD"
    status: Literal["planning", "comparing", "booking", "confirmed", "cancelled"] = (
        "planning"
    )


class HandoffContext(BaseModel):
    """Agent handoff context information."""

    from_agent: str
    to_agent: str
    routing_confidence: float
    routing_reasoning: str
    timestamp: str
    message_analyzed: str
    additional_context: Dict[str, Any] = Field(default_factory=dict)


class ErrorInfo(BaseModel):
    """Error tracking information."""

    error_count: int = 0
    last_error: Optional[str] = None
    retry_attempts: Dict[str, int] = Field(default_factory=dict)
    error_history: List[Dict[str, Any]] = Field(default_factory=list)


class ToolCallInfo(BaseModel):
    """Tool call tracking information."""

    tool_name: str
    timestamp: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    status: Literal["pending", "success", "error"] = "pending"
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None


class TravelPlanningState(TypedDict):
    """
    Unified state schema for all travel planning workflows.

    This state is passed between all agent nodes and contains all the context
    needed for travel planning conversations and operations. Enhanced with
    structured data models for better type safety and clarity.

    State Design Principles:
    - Comprehensive: Contains all necessary information for agent decisions
    - Type-safe: Uses structured models for complex data
    - Traceable: Tracks agent history and tool usage
    - Resilient: Includes error handling and recovery information
    - Scalable: Can be extended without breaking existing agents
    """

    # Core conversation data - handled by LangGraph add_messages
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_id: str
    session_id: str

    # Structured user context (using Pydantic models for validation)
    user_preferences: Optional[Dict[str, Any]]  # Serialized UserPreferences
    travel_dates: Optional[Dict[str, Any]]  # Serialized TravelDates
    destination_info: Optional[Dict[str, Any]]  # Serialized DestinationInfo

    # Search results with structured tracking
    flight_searches: List[Dict[str, Any]]  # List of SearchResult dicts
    accommodation_searches: List[Dict[str, Any]]  # List of SearchResult dicts
    activity_searches: List[Dict[str, Any]]  # List of SearchResult dicts

    # Booking progress tracking
    booking_progress: Optional[Dict[str, Any]]  # Serialized BookingProgress

    # Agent orchestration and routing
    current_agent: Optional[str]
    agent_history: List[str]
    handoff_context: Optional[Dict[str, Any]]  # Serialized HandoffContext

    # Enhanced error handling and resilience
    error_info: Dict[str, Any]  # Serialized ErrorInfo

    # Tool execution tracking with detailed information
    active_tool_calls: List[Dict[str, Any]]  # List of ToolCallInfo dicts
    completed_tool_calls: List[Dict[str, Any]]  # List of ToolCallInfo dicts

    # Memory and context enhancement
    conversation_summary: Optional[str]  # LLM-generated summary for long conversations
    extracted_entities: Dict[str, Any]  # Named entities extracted from conversation
    user_intent: Optional[str]  # Current identified user intent
    confidence_score: Optional[float]  # Confidence in current routing/intent

    # Session lifecycle management
    created_at: Optional[str]
    updated_at: Optional[str]
    last_activity: Optional[str]
    is_active: bool


def create_initial_state(
    user_id: str, message: str, session_id: Optional[str] = None
) -> TravelPlanningState:
    """
    Create an initial state for a new conversation.

    Args:
        user_id: Unique identifier for the user
        message: Initial user message
        session_id: Optional session ID (generated if not provided)

    Returns:
        Initial TravelPlanningState with default values and enhanced structure
    """
    now = datetime.now(datetime.UTC).isoformat()

    return TravelPlanningState(
        # Core conversation data
        messages=[{"role": "user", "content": message, "timestamp": now}],
        user_id=user_id,
        session_id=session_id
        or f"session_{user_id}_{int(datetime.now(datetime.UTC).timestamp())}",
        # Structured user context (initialized as None, populated during conversation)
        user_preferences=None,
        travel_dates=None,
        destination_info=None,
        # Search state (empty lists, populated by agent actions)
        flight_searches=[],
        accommodation_searches=[],
        activity_searches=[],
        booking_progress=None,
        # Agent coordination (starts with router)
        current_agent=None,
        agent_history=[],
        handoff_context=None,
        # Enhanced error handling (using structured ErrorInfo)
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
    """
    Update the state's timestamp to current time.

    Args:
        state: Current state to update

    Returns:
        State with updated timestamp
    """
    state["updated_at"] = datetime.now(datetime.UTC).isoformat()
    return state
