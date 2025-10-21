"""Typing protocols for FastAPI dependency injection.

These Protocols provide static method visibility for DI-injected services in
routers while allowing concrete service implementations to be returned at
runtime. This improves Pyright type checking without changing runtime wiring.
"""

from __future__ import annotations

from typing import Any, Protocol


class ApiKeyServiceProto(Protocol):
    """Protocol for API key service methods used by routers."""

    async def list_user_keys(self, user_id: str) -> list[dict[str, Any]]:
        """Return API keys for a user."""
        ...

    async def validate_key(
        self, key: str, service: str, user_id: str | None = None
    ) -> Any:
        """Validate an API key for a service."""
        ...

    async def create_key(self, user_id: str, data: Any) -> dict[str, Any]:
        """Create an API key for a user."""
        ...

    async def get_key(self, key_id: str) -> dict[str, Any] | None:
        """Get an API key by identifier."""
        ...

    async def delete_key(self, key_id: str) -> None:
        """Delete an API key by identifier."""
        ...

    async def rotate_key(
        self, key_id: str, new_key: str, user_id: str
    ) -> dict[str, Any]:
        """Rotate an API key with a new secret."""
        ...


class ChatServiceProto(Protocol):
    """Protocol for chat service methods used by routers."""

    async def chat_completion(self, user_id: str, request: Any) -> dict[str, Any]:
        """Generate a chat completion for the user and request."""
        ...

    async def create_session(self, user_id: str, session_data: Any) -> Any:
        """Create a new chat session for the user."""
        ...

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List chat sessions for the user."""
        ...

    async def get_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        """Get a chat session for the user."""
        ...

    async def get_messages(
        self, user_id: str, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """List messages in a chat session."""
        ...

    async def create_message(
        self, user_id: str, session_id: str, message_request: Any
    ) -> dict[str, Any]:
        """Create a message in a chat session."""
        ...

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a chat session."""
        ...
