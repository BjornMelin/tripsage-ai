"""
TripSage agents module.

This module provides factory functions for creating various specialized agents
for the TripSage application.
"""

from typing import Optional

from tripsage.agents.accommodation import AccommodationAgent
from tripsage.agents.base import BaseAgent
from tripsage.agents.destination_research import DestinationResearchAgent
from tripsage.agents.flight import FlightAgent
from tripsage.agents.planning import TravelPlanningAgent
from tripsage.agents.travel import TravelAgent
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
    if agent_type == "travel":
        return TravelAgent(
            name=name or "TripSage Travel Assistant",
            model=model,
            temperature=temperature,
        )
    elif agent_type == "flight":
        return FlightAgent(
            name=name or "TripSage Flight Assistant",
            model=model,
            temperature=temperature,
        )
    elif agent_type == "accommodation":
        return AccommodationAgent(
            name=name or "TripSage Accommodation Assistant",
            model=model,
            temperature=temperature,
        )
    elif agent_type == "planning":
        return TravelPlanningAgent(
            name=name or "TripSage Travel Planning Assistant",
            model=model,
            temperature=temperature,
        )
    elif agent_type == "destination_research":
        return DestinationResearchAgent(
            name=name or "TripSage Destination Research Assistant",
            model=model,
            temperature=temperature,
        )
    elif agent_type == "base":
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
    "TravelAgent",
    "FlightAgent",
    "AccommodationAgent",
    "TravelPlanningAgent",
    "DestinationResearchAgent",
    "create_agent",
]
