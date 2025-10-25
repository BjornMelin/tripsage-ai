"""Factories for trip domain models."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.models.trip import Trip


@register_fixture
class TripFactory(ModelFactory[Trip]):
    """Polyfactory factory for :class:`Trip` with deterministic date ranges."""

    __model__ = Trip
    __use_defaults__ = True
    __random_seed__ = 2025

    @classmethod
    def start_date(cls) -> date:  # type: ignore[override]
        """Generate a deterministic trip start date."""
        today = datetime.now(UTC).date()
        return today + timedelta(days=7)

    @classmethod
    def end_date(cls) -> date:  # type: ignore[override]
        """Generate a deterministic trip end date."""
        today = datetime.now(UTC).date()
        return today + timedelta(days=10)
