"""Integration tests for chat session API (final-only alignment)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal


class TestChatSessionAPI:
    """Integration tests covering session lifecycle via HTTP routes only."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def principal(self):
        return Principal(
            id="42",
            type="user",
            email="user@example.com",
            auth_method="jwt",
        )

    @pytest.mark.asyncio
    async def test_create_list_get_delete_session(self, client, principal):
        chat_service = AsyncMock()
        chat_service.create_session = AsyncMock(
            return_value={"id": str(uuid4()), "title": "New"}
        )
        chat_service.get_user_sessions = AsyncMock(
            return_value=[{"id": str(uuid4()), "title": "New"}]
        )
        chat_service.get_session = AsyncMock(
            return_value={"id": str(uuid4()), "title": "New"}
        )
        chat_service.end_session = AsyncMock(return_value=True)

        from tripsage.api.core.dependencies import get_chat_service, require_principal

        app.dependency_overrides[require_principal] = lambda: principal
        app.dependency_overrides[get_chat_service] = lambda: chat_service
        r = client.post(
            "/api/chat/sessions",
            json={"title": "New"},
            headers={"Authorization": "Bearer t"},
        )
        assert r.status_code == 201

        r = client.get("/api/chat/sessions", headers={"Authorization": "Bearer t"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        sid = uuid4()
        r = client.get(
            f"/api/chat/sessions/{sid}", headers={"Authorization": "Bearer t"}
        )
        assert r.status_code == 200

        r = client.delete(
            f"/api/chat/sessions/{sid}", headers={"Authorization": "Bearer t"}
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_create_and_list_messages(self, client, principal):
        chat_service = AsyncMock()
        chat_service.add_message = AsyncMock(
            return_value={"id": str(uuid4()), "role": "user", "content": "Hello"}
        )
        chat_service.get_messages = AsyncMock(
            return_value=[{"id": str(uuid4()), "role": "user", "content": "Hello"}]
        )

        from tripsage.api.core.dependencies import get_chat_service, require_principal

        app.dependency_overrides[require_principal] = lambda: principal
        app.dependency_overrides[get_chat_service] = lambda: chat_service
        sid = uuid4()
        r = client.post(
            f"/api/chat/sessions/{sid}/messages",
            json={"content": "Hello", "role": "user"},
            headers={"Authorization": "Bearer t"},
        )
        assert r.status_code == 200
        assert r.json()["content"] == "Hello"

        r = client.get(
            f"/api/chat/sessions/{sid}/messages", headers={"Authorization": "Bearer t"}
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_message_error(self, client, principal):
        chat_service = AsyncMock()
        chat_service.add_message = AsyncMock(side_effect=Exception("boom"))

        from tripsage.api.core.dependencies import get_chat_service, require_principal

        app.dependency_overrides[require_principal] = lambda: principal
        app.dependency_overrides[get_chat_service] = lambda: chat_service
        sid = uuid4()
        r = client.post(
            f"/api/chat/sessions/{sid}/messages",
            json={"content": "Hello", "role": "user"},
            headers={"Authorization": "Bearer t"},
        )
        assert r.status_code == 500
