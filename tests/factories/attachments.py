"""Factories for attachment domain models."""

from __future__ import annotations

from datetime import UTC, datetime

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.models.attachments import AttachmentResponse


@register_fixture
class AttachmentResponseFactory(ModelFactory[AttachmentResponse]):
    """Factory for :class:`AttachmentResponse` with deterministic timestamps."""

    __model__ = AttachmentResponse
    __use_defaults__ = True
    __random_seed__ = 2025

    @classmethod
    def created_at(cls) -> datetime:  # type: ignore[override]
        """Provide a stable creation timestamp for attachments."""
        return datetime(2024, 1, 1, tzinfo=UTC)

    @classmethod
    def updated_at(cls) -> datetime:  # type: ignore[override]
        """Provide a stable update timestamp for attachments."""
        return datetime(2024, 1, 2, tzinfo=UTC)
