"""Shared fixtures for orchestration unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr


@pytest.fixture(autouse=True)
def mock_orchestration_settings(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Provide deterministic settings for orchestration nodes."""

    def agent_config_factory(agent: str, **overrides: Any) -> dict[str, Any]:
        base_config: dict[str, Any] = {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "top_p": 0.9,
            "api_key": SecretStr("test-key"),
            "max_tokens": 512,
        }
        if agent == "itinerary_agent":
            base_config["max_tokens"] = 768
        base_config.update(overrides)
        return base_config

    settings = MagicMock()
    settings.get_agent_config.side_effect = agent_config_factory
    settings.openai_api_key = SecretStr("test-key")
    settings.openai_model = "gpt-4o-mini"
    settings.model_temperature = 0.1
    settings.airbnb = SimpleNamespace(enabled=True)

    def _get_settings() -> MagicMock:
        return settings

    targets = [
        "tripsage_core.config.get_settings",
        "tripsage.orchestration.nodes.flight_agent.get_settings",
        "tripsage.orchestration.nodes.accommodation_agent.get_settings",
        "tripsage.orchestration.nodes.budget_agent.get_settings",
        "tripsage.orchestration.nodes.destination_research_agent.get_settings",
        "tripsage.orchestration.nodes.itinerary_agent.get_settings",
    ]
    for target in targets:
        monkeypatch.setattr(target, _get_settings)

    return settings
