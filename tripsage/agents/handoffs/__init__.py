"""
TripSage Agent handoff modules.

This package contains specialized agent handoffs that can be
delegated to by the main TravelPlanningAgent, using the OpenAI Agents SDK.
"""

from tripsage.agents.handoffs.helper import (
    HandoffError,
    create_handoff_tool,
    create_delegation_tool,
    create_user_announcement,
    register_handoff_tools,
    register_delegation_tools,
)

__all__ = [
    "HandoffError",
    "create_handoff_tool",
    "create_delegation_tool",
    "create_user_announcement",
    "register_handoff_tools",
    "register_delegation_tools",
]
