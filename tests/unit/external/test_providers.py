"""Unit tests for provider adapters (mocked, no network)."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from tripsage_core.services.external_apis.providers.anthropic_adapter import (
    AnthropicAdapter,
)
from tripsage_core.services.external_apis.providers.openai_adapter import (
    OpenAIAdapter,
)
from tripsage_core.services.external_apis.providers.openrouter_adapter import (
    OpenRouterAdapter,
)


@pytest.mark.asyncio
async def test_openai_adapter_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify OpenAI adapter calls SDK and returns content."""
    captured: dict[str, Any] = {}

    class _Resp:
        """Response class for OpenAI client."""

        class _Choice:
            """Choice class for OpenAI client."""

            class _Msg:
                """Message class for OpenAI client."""

                content = "ok"

            message = _Msg()

        choices: ClassVar[list[_Choice]] = [_Choice()]

    class _Client:
        """Client class for OpenAI client."""

        class _Chat:
            """Chat class for OpenAI client."""

            class _Comps:
                @staticmethod
                def create(**kwargs: Any) -> _Resp:
                    """Create method for Completions class."""
                    captured.update(kwargs)
                    return _Resp()

            completions = _Comps()

        chat = _Chat()

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize method for Client class."""

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        __import__("types").SimpleNamespace(OpenAI=_Client),
    )

    adapter = OpenAIAdapter("sk-openai")
    out = adapter.complete([{"role": "user", "content": "hi"}], model="gpt-4o-mini")
    assert out == "ok"
    assert captured["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_openrouter_adapter_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify OpenRouter adapter uses base_url and headers pass through."""
    created: dict[str, Any] = {}

    class _Resp:
        """Response class for OpenRouter client."""

        class _Choice:
            """Choice class for OpenRouter client."""

            class _Msg:
                """Message class for OpenRouter client."""

                content = "ok"

            message = _Msg()

        choices: ClassVar[list[_Choice]] = [_Choice()]

    class _Client:
        """Client class for OpenRouter client."""

        def __init__(self, *, api_key: str, base_url: str) -> None:
            """Initialize method for Client class."""
            created["api_key"] = api_key
            created["base_url"] = base_url

        class _Chat:
            """Chat class for OpenRouter client."""

            class _Comps:
                @staticmethod
                def create(**kwargs: Any) -> _Resp:
                    """Create method for Completions class."""
                    return _Resp()

            completions = _Comps()

        chat = _Chat()

    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        __import__("types").SimpleNamespace(OpenAI=_Client),
    )

    adapter = OpenRouterAdapter("sk-openrouter")
    out = adapter.complete([{"role": "user", "content": "hi"}], model="openai/gpt-4o")
    assert out == "ok"
    assert created["base_url"].endswith("/api/v1")


@pytest.mark.asyncio
async def test_anthropic_adapter_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Anthropic adapter messages.create is used and content joined."""
    called: dict[str, Any] = {}

    class _Msg:
        """Message class for Anthropic client."""

        content: ClassVar[list[Any]] = [
            __import__("types").SimpleNamespace(text="hello")
        ]

    class _Client:
        """Client class for Anthropic client."""

        class _Msgs:
            """Messages class for Anthropic client."""

            @staticmethod
            def create(**kwargs: Any) -> _Msg:
                """Create method for Messages class."""
                called.update(kwargs)
                return _Msg()

        messages = _Msgs()

        def __init__(self, *, api_key: str) -> None:
            """Initialize method for Client class."""
            called["api_key"] = api_key

    monkeypatch.setitem(
        __import__("sys").modules,
        "anthropic",
        __import__("types").SimpleNamespace(Anthropic=_Client),
    )

    adapter = AnthropicAdapter("sk-anthropic")
    out = adapter.complete([{"role": "user", "content": "hi"}], model="claude-sonnet")
    assert out == "hello"
    assert called["model"] == "claude-sonnet"
