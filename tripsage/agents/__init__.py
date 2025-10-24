"""TripSage agents module.

This module provides factory helpers for creating TripSage agents backed by the
FastAPI ``app.state`` service singletons.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import Request

from tripsage.agents.base import BaseAgent
from tripsage.agents.chat import ChatAgent
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage_core.config import get_settings


settings = get_settings()


def create_agent(
    request: Request,
    agent_type: str,
    name: str | None = None,
    **kwargs: Any,
) -> BaseAgent:
    """Create an agent of the specified type using app.state singletons.

    Args:
        request: Incoming FastAPI request exposing ``app.state``.
        agent_type: Agent identifier (``base`` or ``chat`` are supported).
        name: Optional custom agent name.
        **kwargs: Additional keyword arguments passed to the agent constructor.

    Returns:
        The instantiated agent.

    Raises:
        ValueError: If required services are missing or the agent type is unknown.
    """
    services = cast(
        AppServiceContainer,
        getattr(request.app.state, "services", None),
    )
    orchestrator = cast(
        TripSageOrchestrator,
        getattr(request.app.state, "orchestrator", None),
    )

    if services is None or orchestrator is None:
        raise ValueError(
            "Application services are not initialised; ensure initialise_app_state "
            "runs during FastAPI startup."
        )

    if agent_type == "base":
        return BaseAgent(
            name=name or "TripSage Assistant",
            services=services,
            orchestrator=orchestrator,
            **kwargs,
        )
    if agent_type == "chat":
        return ChatAgent(
            services=services,
            orchestrator=orchestrator,
        )

    raise ValueError(f"Unknown agent type: {agent_type}")


__all__ = [
    "BaseAgent",
    "ChatAgent",
    "create_agent",
]
