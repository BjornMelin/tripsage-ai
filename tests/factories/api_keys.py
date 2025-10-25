"""Factories for API key domain models."""

from __future__ import annotations

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.services.business.api_key_service import ApiKeyResponse


@register_fixture
class ApiKeyFactory(ModelFactory[ApiKeyResponse]):
    """Polyfactory factory for :class:`ApiKeyResponse`.

    Ensures deterministic generation by relying on model defaults and a fixed seed.
    """

    __model__ = ApiKeyResponse
    __use_defaults__ = True
    __random_seed__ = 2025
