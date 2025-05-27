"""
State schema definitions for TripSage LangGraph orchestration.

This module defines the unified state schema used across all agent nodes
in the LangGraph-based orchestration system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict


class TravelPlanningState(TypedDict):
    """
    Unified state schema for all travel planning workflows.

    This state is passed between all agent nodes and contains all the context
    needed for travel planning conversations and operations.
    """

    # Core conversation data
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_id: str
    session_id: str

    # User context and preferences
    user_preferences: Optional[Dict[str, Any]]
    budget_constraints: Optional[Dict[str, Any]]
    travel_dates: Optional[Dict[str, Any]]
    destination_info: Optional[Dict[str, Any]]

    # Search and booking state
    flight_searches: List[Dict[str, Any]]
    accommodation_searches: List[Dict[str, Any]]
    activity_searches: List[Dict[str, Any]]
    booking_progress: Optional[Dict[str, Any]]

    # Agent coordination
    current_agent: Optional[str]
    agent_history: List[str]
    handoff_context: Optional[Dict[str, Any]]

    # Error handling and resilience
    error_count: int
    last_error: Optional[str]
    retry_attempts: Dict[str, int]

    # Tool call tracking
    active_tool_calls: List[Dict[str, Any]]
    completed_tool_calls: List[Dict[str, Any]]

    # Session metadata
    created_at: Optional[str]
    updated_at: Optional[str]


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
        Initial TravelPlanningState with default values
    """
    now = datetime.utcnow().isoformat()

    return TravelPlanningState(
        # Core conversation data
        messages=[{"role": "user", "content": message}],
        user_id=user_id,
        session_id=session_id
        or f"session_{user_id}_{int(datetime.utcnow().timestamp())}",
        # User context (initialized as None, populated during conversation)
        user_preferences=None,
        budget_constraints=None,
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
        # Error handling (clean slate)
        error_count=0,
        last_error=None,
        retry_attempts={},
        # Tool call tracking (empty initially)
        active_tool_calls=[],
        completed_tool_calls=[],
        # Session metadata
        created_at=now,
        updated_at=now,
    )


def update_state_timestamp(state: TravelPlanningState) -> TravelPlanningState:
    """
    Update the state's timestamp to current time.

    Args:
        state: Current state to update

    Returns:
        State with updated timestamp
    """
    state["updated_at"] = datetime.utcnow().isoformat()
    return state
