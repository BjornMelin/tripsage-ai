"""
Handoff helper functions for TripSage agents.

This module provides helper functions to facilitate handoffs between
different agent types in TripSage, leveraging OpenAI Agents SDK patterns.
"""

from typing import Any, Callable, Dict, Optional, Type

try:
    from agents import Agent, handoff
    from agents.extensions import handoff_filters
    from agents.handoffs import Handoff
except ImportError:
    from unittest.mock import MagicMock

    Agent = MagicMock
    handoff = MagicMock
    handoff_filters = MagicMock()
    Handoff = MagicMock
from pydantic import BaseModel

from tripsage.utils.error_handling import TripSageError
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class HandoffError(TripSageError):
    """Error raised when a handoff fails."""

    pass


def create_travel_handoff(
    target_agent: Agent,
    tool_name: str,
    description: str,
    input_model: Optional[Type[BaseModel]] = None,
    preserve_context: bool = True,
    announcement_callback: Optional[Callable] = None,
) -> Handoff:
    """Create a handoff for a travel-specific agent.

    Args:
        target_agent: The agent to hand off to
        tool_name: Name for the handoff tool
        description: Description of what this handoff does
        input_model: Optional Pydantic model for structured handoff inputs
        preserve_context: Whether to preserve user messages in context
        announcement_callback: Optional callback for user-friendly announcements

    Returns:
        A handoff object that can be registered with an agent
    """
    # Select appropriate input filter based on context preservation setting
    if preserve_context:
        input_filter = handoff_filters.preserve_user_messages
    else:
        input_filter = None  # Use default behavior

    # Create handoff with OpenAI Agents SDK patterns
    return handoff(
        agent=target_agent,
        tool_name_override=tool_name,
        tool_description_override=description,
        input_type=input_model,
        input_filter=input_filter,
        on_handoff=announcement_callback,
    )


def register_travel_handoffs(
    agent: Agent, handoff_configs: Dict[str, Dict[str, Any]]
) -> int:
    """Register travel-specific handoffs with an agent.

    Args:
        agent: Agent to register handoffs with
        handoff_configs: Dictionary mapping tool names to configurations with keys:
            - "agent": Target agent
            - "description": Handoff description
            - "input_model": Optional Pydantic model for structured inputs
            - "preserve_context": Whether to preserve context (defaults to True)
            - "announcement_callback": Optional callback for user announcements

    Returns:
        Number of handoffs registered
    """
    handoffs = []

    for tool_name, config in handoff_configs.items():
        target_agent = config.get("agent")
        description = config.get("description", f"Transfer to {target_agent.name}")
        input_model = config.get("input_model")
        preserve_context = config.get("preserve_context", True)
        announcement_callback = config.get("announcement_callback")

        handoff_obj = create_travel_handoff(
            target_agent=target_agent,
            tool_name=tool_name,
            description=description,
            input_model=input_model,
            preserve_context=preserve_context,
            announcement_callback=announcement_callback,
        )

        handoffs.append(handoff_obj)
        logger.info(f"Created handoff to {target_agent.name} via {tool_name}")

    # Update agent's handoffs attribute
    if hasattr(agent, "agent"):
        # Access underlying OpenAI Agent
        agent.agent.handoffs.extend(handoffs)
    else:
        # Direct access if needed
        agent.handoffs.extend(handoffs)

    logger.info(f"Registered {len(handoffs)} handoffs with {agent.name}")
    return len(handoffs)


def create_user_announcement(
    source_agent_name: str,
    target_agent_name: str,
    reason: Optional[str] = None,
) -> str:
    """Create a user-friendly handoff announcement.

    Args:
        source_agent_name: Name of the source agent
        target_agent_name: Name of the target agent
        reason: Optional reason for the handoff

    Returns:
        Formatted announcement message
    """
    # Format names for display
    _source_name = source_agent_name.replace("Agent", "").strip()
    target_name = target_agent_name.replace("Agent", "").strip()

    # Base announcement
    announcement = (
        f"👋 I'm connecting you with our {target_name} Specialist to "
        f"better assist with your request."
    )

    # Add reason if provided
    if reason:
        announcement += f"\n\n{reason}"

    return announcement
