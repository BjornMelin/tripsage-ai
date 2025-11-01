"""Unit tests for BYOK validation helper (no network)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from tripsage.api.routers import keys as keys_router


validate_api_key = cast(Any, keys_router)._validate_api_key


@pytest.mark.asyncio
async def test_validate_openai_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI key validation returns True when models.list succeeds."""

    class _Client:
        """Client class for OpenAI client."""

        class _Models:
            """Models class for OpenAI client."""

            @staticmethod
            def list() -> dict[str, Any]:
                """List method for Models class."""
                return {"object": "list", "data": []}

        models = _Models()

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize method for Client class."""

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        __import__("types").SimpleNamespace(OpenAI=_Client),
    )
    ok, reason = await validate_api_key("openai", "sk-test")
    assert ok is True and reason is None


@pytest.mark.asyncio
async def test_validate_openrouter_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenRouter key validation returns True and uses base_url."""

    class _Client:
        """Client class for OpenRouter client."""

        class _Models:
            """Models class for OpenRouter client."""

            @staticmethod
            def list() -> dict[str, Any]:
                """List method for Models class."""
                return {"object": "list", "data": []}

        models = _Models()

        def __init__(self, *, api_key: str, base_url: str) -> None:
            assert base_url.endswith("/api/v1")

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        __import__("types").SimpleNamespace(OpenAI=_Client),
    )
    ok, reason = await validate_api_key("openrouter", "sk-or")
    assert ok is True and reason is None


@pytest.mark.asyncio
async def test_validate_anthropic_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anthropic key validation returns True when models.list succeeds."""

    class _Client:
        """Client class for Anthropic client."""

        class _Models:
            """Models class for Anthropic client."""

            @staticmethod
            def list() -> dict[str, Any]:
                """List method for Models class."""
                return {"object": "list", "data": []}

        models = _Models()

        def __init__(self, *, api_key: str) -> None:
            """Initialize method for Client class."""

    monkeypatch.setitem(
        __import__("sys").modules,
        "anthropic",
        __import__("types").SimpleNamespace(Anthropic=_Client),
    )
    ok, reason = await validate_api_key("anthropic", "sk-ant")
    assert ok is True and reason is None


@pytest.mark.asyncio
async def test_validate_unsupported() -> None:
    """Unsupported service returns False with reason."""
    ok, reason = await validate_api_key("other", "x")
    assert ok is False and reason == "unsupported_service"
