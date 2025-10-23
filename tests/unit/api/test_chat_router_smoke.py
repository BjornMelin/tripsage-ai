"""Smoke tests for the chat router endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.core.dependencies import require_principal
from tripsage.api.routers import chat as chat_router
from tripsage.api.schemas.chat import ChatRequest


class _P:
    """Mock principal object for testing authentication dependencies.

    Provides a mock implementation of a user principal with default test values
    for use in dependency injection during testing.
    """

    def __init__(self, user_id: str = "user-1"):
        self.id = user_id
        self.user_id = user_id
        self.type = "user"
        self.auth_method = "api_key"
        self.metadata = {}


class _ChatSvc:
    """Mock chat service for testing chat router endpoints.

    Provides stub implementations of chat service methods that return mock data
    for use in smoke tests of the chat API endpoints.
    """

    async def chat_completion(self, user_id: str, request: ChatRequest):
        """Mock implementation of chat completion."""
        return {
            "content": "hi",
            "session_id": None,
            "model": "mock",
            "usage": {},
            "finish_reason": "stop",
        }

    async def create_session(self, user_id: str, session_data):
        """Mock implementation of session creation."""
        return {"id": "s1"}

    async def list_sessions(self, user_id: str):
        """Mock implementation of session listing."""
        return []

    async def get_session(self, user_id: str, session_id: str):
        """Mock implementation of session retrieval."""

    async def get_messages(
        self, user_id: str, session_id: str, limit: int | None = None
    ):
        """Mock implementation of message retrieval."""
        return []

    async def create_message(self, user_id: str, session_id: str, message_request):
        """Mock implementation of message creation."""
        return {"id": "m1"}


def _app() -> FastAPI:
    """Create a FastAPI application with the chat router and mock dependencies.

    Returns:
        FastAPI: Configured FastAPI application instance with chat router and
            overridden dependencies for testing (mock principal and chat service).
    """
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    # pylint: disable=unnecessary-lambda
    app.dependency_overrides[require_principal] = lambda: _P()  # type: ignore[assignment]
    app.dependency_overrides[chat_router.ChatServiceDep] = lambda: _ChatSvc()  # type: ignore[assignment]
    return app


def test_chat_completion_smoke():
    """Test the chat completion endpoint returns a successful response with content.

    Verifies that the POST /api/chat/ endpoint responds with status 200 and includes
    a 'content' field in the JSON response when provided with basic chat request data.
    """
    client = TestClient(_app())
    resp = client.post(
        "/api/chat/", json={"messages": [], "stream": False, "save_history": False}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "content" in body
