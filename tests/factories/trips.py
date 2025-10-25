"""Factories for trip domain models."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from tripsage_core.models.trip import Trip


@register_fixture
class TripFactory(ModelFactory[Trip]):
    """Polyfactory factory for :class:`Trip`."""

    __model__ = Trip

    @classmethod
    def start_date(cls) -> date:  # type: ignore[override]
        """Get a random start date for a trip."""
        today = datetime.now(UTC).date()
        return today + timedelta(days=7)

    @classmethod
    def end_date(cls) -> date:  # type: ignore[override]
        """Get a random end date for a trip."""
        today = datetime.now(UTC).date()
        return today + timedelta(days=10)
