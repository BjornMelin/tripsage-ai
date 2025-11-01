"""Unit tests for the Trip domain model."""

from __future__ import annotations

import math
from datetime import date, timedelta
from uuid import uuid4

import pytest

from tripsage_core.models.schemas_common.enums import TripStatus, TripVisibility
from tripsage_core.models.trip import Budget, BudgetBreakdown, Trip


def _build_budget(total: float, spent: float) -> Budget:
    """Build a budget breakdown for testing."""
    return Budget(
        total=total,
        spent=spent,
        breakdown=BudgetBreakdown(
            accommodation=total * 0.3,
            transportation=total * 0.3,
            food=total * 0.2,
            activities=total * 0.1,
            miscellaneous=total * 0.1,
        ),
    )


def test_trip_budget_metrics_computed_correctly() -> None:
    """Ensure budget-derived metrics match expected values."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 3)
    trip = Trip(
        id=uuid4(),
        user_id=uuid4(),
        title="Kyoto Getaway",
        description="Culture and food",
        start_date=start,
        end_date=end,
        destination="Kyoto",
        budget_breakdown=_build_budget(900.0, 450.0),
        travelers=2,
        tags=["  culture", "culture", "FOOD"],
    )

    assert trip.duration_days == 3
    assert math.isclose(trip.budget_per_day, 300.0, rel_tol=1e-9)
    assert math.isclose(trip.budget_per_person, 450.0, rel_tol=1e-9)
    assert math.isclose(trip.budget_utilization, 50.0, rel_tol=1e-9)
    assert math.isclose(trip.remaining_budget, 450.0, rel_tol=1e-9)
    assert sorted(trip.tags) == ["FOOD", "culture"]


def test_trip_date_validation_prevents_invalid_ranges() -> None:
    """Verify validation rejects end dates before start dates."""
    start = date(2025, 1, 10)
    end = date(2025, 1, 8)

    with pytest.raises(ValueError):
        Trip(
            id=uuid4(),
            user_id=uuid4(),
            title="Invalid",
            description="Invalid range",
            start_date=start,
            end_date=end,
            destination="Nowhere",
            budget_breakdown=_build_budget(100.0, 0.0),
        )


def test_can_modify_and_visibility_properties() -> None:
    """Validate modifiability and visibility flags respond to state."""
    future_start = date.today() + timedelta(days=5)
    future_end = future_start + timedelta(days=2)
    trip = Trip(
        id=uuid4(),
        user_id=uuid4(),
        title="Future Trip",
        description="Upcoming adventure",
        start_date=future_start,
        end_date=future_end,
        destination="Lisbon",
        budget_breakdown=_build_budget(600.0, 100.0),
        visibility=TripVisibility.SHARED,
    )

    assert trip.can_modify() is True
    assert trip.is_shared is True

    trip.status = TripStatus.COMPLETED
    assert trip.can_modify() is False
    assert trip.is_completed is True


def test_status_transitions_and_tag_management() -> None:
    """Check status transitions and tag helpers operate correctly."""
    start = date.today() + timedelta(days=10)
    trip = Trip(
        id=uuid4(),
        user_id=uuid4(),
        title="Planning",
        description="Pre-trip planning",
        start_date=start,
        end_date=start + timedelta(days=3),
        destination="Berlin",
        budget_breakdown=_build_budget(800.0, 0.0),
    )

    assert trip.update_status(TripStatus.BOOKED) is True
    assert trip.update_status(TripStatus.COMPLETED) is True
    assert trip.update_status(TripStatus.PLANNING) is False

    assert trip.add_tag(" art ") is True
    assert trip.add_tag("art") is False
    assert trip.remove_tag("art") is True
    assert trip.remove_tag("art") is False
