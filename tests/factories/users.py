"""Factories for user domain models."""

from __future__ import annotations

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.models.db.user import User


@register_fixture
class UserFactory(ModelFactory[User]):
    """Polyfactory factory for :class:`User` with stable defaults."""

    __model__ = User
    __use_defaults__ = True
    __random_seed__ = 2025
