"""
TripSage agents module.

This module provides factory functions for creating various specialized agents
for the TripSage application.
"""

from typing import Optional

from tripsage.agents.base import BaseAgent
from tripsage_core.config.base_app_settings import get_settings

settings = get_settings()


def create_agent(
    agent_type: str,
    name: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs,
) -> BaseAgent:
    """Create an agent of the specified type.

    Args:
        agent_type: Type of agent to create
        name: Optional custom name for the agent
        model: Optional model name to use
        temperature: Optional temperature for model sampling
        **kwargs: Additional agent-specific parameters

    Returns:
        The created agent instance

    Raises:
        ValueError: If the agent type is not recognized
    """
    # Default to settings if not provided
    model = model or settings.agent.model_name
    temperature = temperature or settings.agent.temperature

    # Create the appropriate agent type
    if agent_type == "base":
        return BaseAgent(
            name=name or "TripSage Assistant",
            model=model,
            temperature=temperature,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


__all__ = [
    "BaseAgent",
    "create_agent",
]
