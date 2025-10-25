"""Factories for user domain models."""

from __future__ import annotations

from polyfactory.factories.pydantic_factory import ModelFactory

from tripsage_core.models.db.user import User


class UserFactory(ModelFactory[User]):
    """Polyfactory factory for :class:`User`."""

    __model__ = User
