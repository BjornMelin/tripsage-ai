"""Integration tests for chat endpoints."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tripsage.api.core.dependencies import get_chat_service, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.chat import ChatRequest, ChatResponse


class ChatServiceStub:
    """Stubbed chat service returning deterministic completions."""

    async def chat_completion(self, user_id: str, request: ChatRequest) -> ChatResponse:
        """Return a canned chat completion for assertions."""
        return ChatResponse(
            session_id=uuid4(),
            content=f"Hello {user_id}!",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )


def _principal_stub() -> Principal:
    return Principal(
        id="user-789",
        type="user",
        email="traveler@example.com",
        auth_method="jwt",
        scopes=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_chat_completion_returns_response(
    app: FastAPI, async_client: AsyncClient
) -> None:
    """POST /chat should invoke the chat service and return its payload."""

    async def _principal_override() -> Principal:
        return _principal_stub()

    async def _chat_service_override() -> ChatServiceStub:
        return ChatServiceStub()

    app.dependency_overrides[require_principal] = _principal_override
    app.dependency_overrides[get_chat_service] = _chat_service_override

    payload: dict[str, Any] = {
        "messages": [
            {
                "role": "user",
                "content": "Plan my Kyoto trip",
                "tool_calls": None,
                "timestamp": None,
                "metadata": {},
            }
        ],
        "stream": False,
        "save_history": False,
    }

    try:
        response = await async_client.post("/api/chat/", json=payload)
    finally:
        app.dependency_overrides.pop(require_principal, None)
        app.dependency_overrides.pop(get_chat_service, None)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["content"].startswith("Hello user-789")
    assert data["usage"]["prompt_tokens"] == 10
