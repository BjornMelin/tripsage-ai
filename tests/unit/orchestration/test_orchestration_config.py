"""Tests for LangGraph orchestration configuration utilities.

Covers environment loading, app-settings fallback, and validation errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest
from pytest import approx  # type: ignore[reportUnknownVariableType]

from tripsage.orchestration.config import (
    CheckpointStorage,
    LangGraphConfig,
    get_default_config,
)


def test_from_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_environment returns documented defaults when no vars are set."""
    # Clear relevant env vars
    keys = [
        "LANGGRAPH_DEFAULT_MODEL",
        "LANGGRAPH_TEMPERATURE",
        "LANGGRAPH_MAX_TOKENS",
        "LANGGRAPH_ROUTER_MODEL",
        "LANGGRAPH_ROUTER_TEMPERATURE",
        "LANGGRAPH_CHECKPOINT_STORAGE",
        "LANGGRAPH_FEATURES",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)

    cfg = LangGraphConfig.from_environment()
    assert cfg.default_model == "gpt-5"
    assert cfg.router_model == "gpt-5-mini"
    assert cfg.checkpoint_storage is CheckpointStorage.MEMORY
    assert cfg.temperature == approx(0.7)
    assert cfg.max_tokens == 4096


def test_from_environment_custom_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_environment should parse custom environment variables correctly."""
    monkeypatch.setenv("LANGGRAPH_DEFAULT_MODEL", "gpt-X")
    monkeypatch.setenv("LANGGRAPH_TEMPERATURE", "0.9")
    monkeypatch.setenv("LANGGRAPH_MAX_TOKENS", "2048")
    monkeypatch.setenv("LANGGRAPH_ROUTER_MODEL", "gpt-Y")
    monkeypatch.setenv("LANGGRAPH_ROUTER_TEMPERATURE", "0.2")
    monkeypatch.setenv("LANGGRAPH_CHECKPOINT_STORAGE", "postgres")
    monkeypatch.setenv(
        "LANGGRAPH_FEATURES",
        "conversation_memory,advanced_routing,memory_updates,error_recovery,langsmith",
    )

    cfg = LangGraphConfig.from_environment()
    assert cfg.default_model == "gpt-X"
    assert cfg.router_model == "gpt-Y"
    assert cfg.temperature == approx(0.9)
    assert cfg.max_tokens == 2048
    assert cfg.checkpoint_storage is CheckpointStorage.POSTGRES
    assert cfg.enable_langsmith is True
    assert cfg.enable_advanced_routing is True
    assert cfg.enable_memory_updates is True
    assert cfg.enable_error_recovery is True


def test_get_default_config_fallback_to_app_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_default_config should fall back to app settings on env parse error."""
    # Trigger ValueError on environment parsing
    monkeypatch.setenv("LANGGRAPH_TEMPERATURE", "not-a-number")

    @dataclass
    class _OpenAIKey:
        """OpenAI key."""

        def get_secret_value(self) -> str:
            """Get secret value."""
            return "sk-test"

    @dataclass
    class _Settings:
        """Settings."""

        openai_model: str = "model-from-settings"
        openai_api_key: Any = None
        database_url: str | None = None

    settings = _Settings()
    settings.openai_api_key = _OpenAIKey()

    with patch("tripsage.orchestration.config.get_settings", return_value=settings):
        cfg = get_default_config()
    # Ensure app-settings fallback used

    assert cfg.default_model == "model-from-settings"
    assert cfg.checkpoint_storage is CheckpointStorage.MEMORY


@pytest.mark.parametrize(
    "field, value, error_substr",
    [
        ("temperature", -0.1, "Temperature"),
        ("max_tokens", 0, "Max tokens"),
        ("max_retries", -1, "Max retries"),
        ("retry_delay", -0.1, "Retry delay"),
        ("escalation_threshold", 0, "Escalation threshold"),
        ("timeout_seconds", 0, "Timeout"),
        ("max_concurrent_tools", 0, "Max concurrent tools"),
        ("session_timeout_hours", 0, "Session timeout"),
        ("max_message_history", 0, "Max message history"),
    ],
)
def test_validate_raises_on_invalid(field: str, value: Any, error_substr: str) -> None:
    """validate() should raise ValueError on invalid field ranges."""
    cfg = LangGraphConfig()
    setattr(cfg, field, value)
    with pytest.raises(ValueError, match=error_substr):
        cfg.validate()


def test_from_app_settings_postgres_and_to_dict() -> None:
    """from_app_settings should infer postgres storage and to_dict returns keys."""

    @dataclass
    class _OpenAIKey:
        """OpenAI key."""

        def get_secret_value(self) -> str:
            """Get secret value."""
            return "sk-test"

    @dataclass
    class _Settings:
        """Settings."""

        openai_model: str = "model-from-settings"
        openai_api_key: Any = None
        database_url: str | None = "postgres://user:pw@host/db"

    settings = _Settings()
    settings.openai_api_key = _OpenAIKey()

    with patch("tripsage.orchestration.config.get_settings", return_value=settings):
        cfg = LangGraphConfig.from_app_settings()

    assert cfg.checkpoint_storage is CheckpointStorage.POSTGRES
    d = cfg.to_dict()
    for key in [
        "default_model",
        "temperature",
        "router_model",
        "checkpoint_storage",
        "max_retries",
        "enable_advanced_routing",
    ]:
        assert key in d

    # Valid config should not raise
    cfg.validate()
