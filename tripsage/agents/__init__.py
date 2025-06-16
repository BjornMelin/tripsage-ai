"""
TripSage agents module.

This module provides factory functions for creating various specialized agents
for the TripSage application.
"""

from typing import Optional

from tripsage.agents.base import BaseAgent
from tripsage.agents.chat import ChatAgent
from tripsage_core.config import get_settings

settings = get_settings()


def create_agent(
    agent_type: str,
    service_registry=None,
    name: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs,
) -> BaseAgent:
    """Create an agent of the specified type.

    Args:
        agent_type: Type of agent to create
        service_registry: Service registry instance (required for modern agents)
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
            service_registry=service_registry,
            **kwargs,
        )
    elif agent_type == "chat":
        if not service_registry:
            raise ValueError("service_registry is required for chat agent")
        return ChatAgent(service_registry)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


__all__ = [
    "BaseAgent",
    "ChatAgent",
    "create_agent",
]
