"""Typing protocols for FastAPI dependency injection.

These Protocols provide static method visibility for DI-injected services in
routers while allowing concrete service implementations to be returned at
runtime. This improves Pyright type checking without changing runtime wiring.
"""

from __future__ import annotations

from typing import Any, Protocol


class ChatServiceProto(Protocol):
    """Protocol for chat service methods used by routers."""

    async def chat_completion(self, user_id: str, request: Any) -> dict[str, Any]:
        """Generate a chat completion for the user and request."""
        ...

    async def create_session(self, user_id: str, session_data: Any) -> Any:
        """Create a new chat session for the user."""
        ...

    async def get_user_sessions(
        self, user_id: str, limit: int = 10, include_ended: bool = False
    ) -> list[Any]:
        """List chat sessions for the user."""
        ...

    async def get_session(self, session_id: str, user_id: str) -> Any | None:
        """Get a chat session for the user."""
        ...

    async def get_messages(
        self, session_id: str, user_id: str, limit: int | None = None, offset: int = 0
    ) -> list[Any]:
        """List messages in a chat session."""
        ...

    async def add_message(
        self, session_id: str, user_id: str, message_data: Any
    ) -> Any:
        """Create a message in a chat session."""
        ...

    async def end_session(self, session_id: str, user_id: str) -> bool:
        """End a chat session."""
        ...
