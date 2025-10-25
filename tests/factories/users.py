"""Factories for user domain models."""

from __future__ import annotations

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.models.db.user import User


@register_fixture
class UserFactory(ModelFactory[User]):
    """Polyfactory factory for :class:`User`."""

    __model__ = User
