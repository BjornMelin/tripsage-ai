"""Unit tests for minimal provider helpers (mocked)."""

from __future__ import annotations

from typing import Any, ClassVar, cast

import pytest

from tripsage_core.services.external_apis.llm_providers import (
    call_anthropic,
    call_openai,
    call_openrouter,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService


class FakeDB:
    """Minimal async stub returning service keys."""

    async def fetch_user_service_api_key(
        self, user_id: str, service: str
    ) -> str | None:
        """Return a fake key by provider name."""
        return {
            "openai": "sk-openai",
            "openrouter": "sk-openrouter",
            "anthropic": "sk-anthropic",
        }.get(service)


FAKE_DB: DatabaseService = cast(DatabaseService, FakeDB())


@pytest.mark.asyncio
async def test_call_openai_uses_openai_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify OpenAI client is called and result is returned."""
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
                """Completions class for OpenAI client."""

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
    out = await call_openai(
        db=FAKE_DB,
        user_id="u",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == "ok"
    assert captured["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_call_openrouter_sets_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify base_url is set for OpenRouter via OpenAI SDK."""
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
                """Completions class for OpenRouter client."""

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
    out = await call_openrouter(
        db=FAKE_DB,
        user_id="u",
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == "ok"
    assert created["base_url"].endswith("/api/v1")


@pytest.mark.asyncio
async def test_call_anthropic_uses_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Anthropic SDK messages.create is used and joined text is returned."""
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
    out = await call_anthropic(
        db=FAKE_DB,
        user_id="u",
        model="claude-sonnet",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == "hello"
    assert called["model"] == "claude-sonnet"
