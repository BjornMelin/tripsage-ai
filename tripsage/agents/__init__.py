"""TripSage agents module.

This module provides factory functions for creating various specialized agents
for the TripSage application.
"""

from __future__ import annotations

from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from tripsage.agents.base import BaseAgent
from tripsage.agents.chat import ChatAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.config import get_settings


settings = get_settings()


def create_agent(
    agent_type: str,
    service_registry: ServiceRegistry | None = None,
    name: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    **kwargs: dict[str, Any],
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
    model = model or settings.openai_model
    temperature = temperature or settings.model_temperature

    # Create the appropriate agent type
    if not service_registry:
        raise ValueError("service_registry is required")

    if agent_type == "base":
        instructions: str | None = cast(str | None, kwargs.pop("instructions", None))
        summary_interval: int = cast(int, kwargs.pop("summary_interval", 10))
        llm: BaseChatModel | None = cast(BaseChatModel | None, kwargs.pop("llm", None))

        if llm is None:
            api_key_raw = settings.openai_api_key
            secret_key = api_key_raw  # Already SecretStr from settings
            llm = ChatOpenAI(model=model, temperature=temperature, api_key=secret_key)

        if kwargs:
            raise ValueError(
                f"Unsupported keyword arguments for BaseAgent: {list(kwargs)}"
            )

        return BaseAgent(
            name=name or "TripSage Assistant",
            service_registry=service_registry,
            instructions=instructions,
            llm=llm,
            summary_interval=summary_interval,
        )

    if agent_type == "chat":
        if kwargs:
            raise ValueError(f"ChatAgent does not support extra kwargs: {list(kwargs)}")
        return ChatAgent(service_registry)

    raise ValueError(f"Unknown agent type: {agent_type}")


__all__ = [
    "BaseAgent",
    "ChatAgent",
    "create_agent",
]
