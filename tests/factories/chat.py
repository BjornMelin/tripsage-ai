"""Factories for chat-related domain models."""

from __future__ import annotations

from datetime import UTC, datetime

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.models.schemas_common.chat import ChatMessage


@register_fixture
class ChatMessageFactory(ModelFactory[ChatMessage]):
    """Factory for :class:`ChatMessage` instances with deterministic metadata."""

    __model__ = ChatMessage
    __use_defaults__ = True
    __random_seed__ = 2025

    @classmethod
    def timestamp(cls) -> datetime | None:  # type: ignore[override]
        """Provide a stable timestamp for generated chat messages."""
        return datetime(2024, 1, 1, tzinfo=UTC)
