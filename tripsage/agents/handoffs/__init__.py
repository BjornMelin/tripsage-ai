"""
TripSage Agent handoff modules.

This package contains specialized agent handoffs that can be
delegated to by the main TravelPlanningAgent, using the OpenAI Agents SDK.
"""

from tripsage.agents.handoffs.helper import (
    HandoffError,
    create_travel_handoff,
    create_user_announcement,
    register_travel_handoffs,
)

__all__ = [
    "HandoffError",
    "create_travel_handoff",
    "register_travel_handoffs",
    "create_user_announcement",
]
