"""Integration tests for chat streaming SSE endpoint with provider-mocked streaming.

Validates SSE contract: started → delta* → final → [DONE] without network calls.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient, Response


class _Delta:
    """Mock delta object for OpenAI streaming response."""

    def __init__(self, content: str | None) -> None:
        """Initialize delta with content.

        Args:
            content: The text content of the delta.
        """
        self.content = content


class _Choice:
    """Mock choice object containing a delta for OpenAI streaming response."""

    def __init__(self, content: str | None) -> None:
        """Initialize choice with delta content.

        Args:
            content: The text content to wrap in a delta.
        """
        self.delta = _Delta(content)


class _Chunk:
    """Mock chunk object for OpenAI streaming response."""

    def __init__(self, content: str | None) -> None:
        """Initialize chunk with a single choice containing the content.

        Args:
            content: The text content for the chunk's choice.
        """
        self.choices = [_Choice(content)]


class _FakeChat:
    """Mock OpenAI chat completions client for testing streaming."""

    def __init__(self, responses: list[str]) -> None:
        """Initialize fake chat client with response parts.

        Args:
            responses: List of string parts to yield as streaming chunks.
        """
        self._responses = responses

    @property
    def completions(self) -> _FakeChat:  # type: ignore[override]
        """Return self to mimic OpenAI client structure."""
        return self

    def create(self, **_: Any):
        """Create streaming chat completion, yielding chunks for each response part.

        Yields:
            _Chunk: Streaming chunks containing response content.
        """
        for part in self._responses:
            yield _Chunk(part)


class _FakeOpenAI:
    """Mock OpenAI client for testing chat streaming without network calls."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize fake OpenAI client with default chat responses.

        Args:
            *args: Unused positional arguments.
            **kwargs: Keyword arguments, extracts base_url if provided.
        """
        self.base_url = kwargs.get("base_url")
        self.chat = _FakeChat(["Hello, ", "world!"])


class _StubChatService:
    """Minimal chat service stub that mimics streaming completions."""

    def __init__(self, db: Any, responses: Sequence[str]) -> None:
        self._db = db
        self._responses = list(responses)

    async def stream_chat_completion(self, user_id: str, request: Any):
        # Resolve API keys to determine provider selection similar to real service.
        import openai as _openai  # type: ignore[import-not-found]

        base_url: str | None = None
        openai_key: str | None = None
        if hasattr(self._db, "fetch_user_service_api_key"):
            openai_key = await self._db.fetch_user_service_api_key(  # type: ignore[misc]
                user_id, "openai"
            )
        if not openai_key and hasattr(self._db, "fetch_user_service_api_key"):
            openrouter_key = await self._db.fetch_user_service_api_key(  # type: ignore[misc]
                user_id, "openrouter"
            )
            if openrouter_key:
                base_url = "https://openrouter.ai/api/v1"

        _openai.OpenAI(base_url=base_url)

        for part in self._responses:
            yield {"type": "delta", "content": part}
        yield {"type": "final", "content": "".join(self._responses)}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_streaming_sse_contract(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test SSE contract for chat streaming with mocked OpenAI responses.

    Verifies that streaming endpoint emits events in correct sequence:
    started → deltas → final → [DONE].

    Args:
        app: FastAPI application instance.
        async_client_factory: Factory for creating async HTTP clients.
        principal: Mock user principal for authentication.
        monkeypatch: Pytest fixture for patching imports and objects.
    """
    from tripsage.api.core import dependencies as dep

    # Principal override
    async def _provide_principal_dep() -> Any:
        """Return the mock principal for dependency injection."""
        return principal

    app.dependency_overrides[dep._require_principal_dependency] = (  # type: ignore[attr-defined]
        _provide_principal_dep
    )  # type: ignore[assignment]

    class _DB:
        """Mock database service that returns test API keys."""

        async def fetch_user_service_api_key(
            self, user_id: str, service: str
        ) -> str | None:
            assert service in {"openai", "openrouter"}
            return "sk-test" if service == "openai" else None

    db_service = _DB()
    app.dependency_overrides[dep.get_db] = lambda: db_service  # type: ignore[assignment]
    app.dependency_overrides[dep.get_chat_service] = lambda: _StubChatService(  # type: ignore[assignment]
        db_service,
        ["Hello, ", "world!"],
    )

    # Patch OpenAI client used in the router (imported dynamically)
    import openai as _openai  # type: ignore[import-not-found]

    monkeypatch.setattr(_openai, "OpenAI", _FakeOpenAI, raising=False)

    client = async_client_factory(app)
    response: Response = await client.post(
        "/api/chat/stream",
        json={
            "messages": [{"role": "user", "content": "Say hi"}],
            "stream": True,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/event-stream")

    # Parse SSE events
    lines: list[str] = [
        line for line in response.text.splitlines() if line.startswith("data:")
    ]
    # Expect: started, delta, delta, final, [DONE]
    assert lines[0].startswith("data: ")
    started = json.loads(lines[0].split("data: ", 1)[1])
    assert started["type"] == "started"
    delta1 = json.loads(lines[1].split("data: ", 1)[1])
    delta2 = json.loads(lines[2].split("data: ", 1)[1])
    assert delta1["type"] == "delta" and delta1["content"] == "Hello, "
    assert delta2["type"] == "delta" and delta2["content"] == "world!"
    final = json.loads(lines[3].split("data: ", 1)[1])
    assert final["type"] == "final" and final["content"] == "Hello, world!"
    assert lines[4] == "data: [DONE]"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_streaming_openrouter_branch(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test OpenRouter fallback when user lacks OpenAI API key.

    Verifies that streaming uses OpenRouter base URL when only OpenRouter
    key is available in database.

    Args:
        app: FastAPI application instance.
        async_client_factory: Factory for creating async HTTP clients.
        principal: Mock user principal for authentication.
        monkeypatch: Pytest fixture for patching imports and objects.
    """
    from tripsage.api.core import dependencies as dep

    # Principal override
    async def _provide_principal_dep() -> Any:
        """Return the mock principal for dependency injection."""
        return principal

    app.dependency_overrides[dep._require_principal_dependency] = (  # type: ignore[attr-defined]
        _provide_principal_dep
    )  # type: ignore[assignment]

    class _DB:
        """Mock database service that returns only OpenRouter API key."""

        async def fetch_user_service_api_key(
            self, user_id: str, service: str
        ) -> str | None:
            if service == "openai":
                return None
            if service == "openrouter":
                return "or-test"
            return None

    db_service = _DB()
    app.dependency_overrides[dep.get_db] = lambda: db_service  # type: ignore[assignment]
    app.dependency_overrides[dep.get_chat_service] = lambda: _StubChatService(  # type: ignore[assignment]
        db_service,
        ["Hello, ", "world!"],
    )

    # Capture constructed OpenAI client to assert base_url
    constructed: dict[str, Any] = {}

    class _CapturingOpenAI(_FakeOpenAI):
        """Mock OpenAI client that captures constructor arguments for testing."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Initialize and capture base_url for assertion.

            Args:
                *args: Positional arguments passed to parent.
                **kwargs: Keyword arguments, base_url is captured for testing.
            """
            super().__init__(*args, **kwargs)
            constructed["base_url"] = kwargs.get("base_url")

    import openai as _openai  # type: ignore[import-not-found]

    monkeypatch.setattr(_openai, "OpenAI", _CapturingOpenAI, raising=False)

    client = async_client_factory(app)
    response: Response = await client.post(
        "/api/chat/stream",
        json={
            "messages": [{"role": "user", "content": "Say hi"}],
            "stream": True,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert constructed.get("base_url") == "https://openrouter.ai/api/v1"
