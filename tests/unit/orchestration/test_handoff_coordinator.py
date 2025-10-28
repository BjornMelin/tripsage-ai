"""Tests for Handoff Coordinator conditions and behavior."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from tripsage.orchestration.handoff_coordinator import AgentHandoffCoordinator
from tripsage.orchestration.state import TravelPlanningState


def test_error_count_operator_map_fail_closed(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Invalid thresholds in error_count must fail closed (return False)."""
    coord = AgentHandoffCoordinator()
    state = state_factory(error_count=2)

    assert (
        coord._evaluate_conditions(  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
            {"error_count": {">=": "not-an-int"}}, state
        )
        is False
    )


@pytest.mark.parametrize(
    "operator,threshold,count,expected",
    [(">=", 3, 2, False), (">=", 2, 2, True), ("<=", 2, 3, False), ("==", 1, 1, True)],
)
def test_error_count_operator_map(
    operator: str,
    threshold: int,
    count: int,
    expected: bool,
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Check >=, <=, == comparisons against current error count."""
    coord = AgentHandoffCoordinator()
    state = state_factory(error_count=count)

    ok = coord._evaluate_conditions(  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
        {"error_count": {operator: threshold}}, state
    )
    assert ok is expected


def test_keyword_condition_detects_recent_messages(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Keyword match should scan the last few messages."""
    messages = [
        {"role": "user", "content": "I need some advice"},
        {"role": "user", "content": "Looking for a hotel downtown"},
    ]
    state = state_factory(extra={"messages": messages})
    coord = AgentHandoffCoordinator()

    assert (
        coord._evaluate_conditions(  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
            {"keywords": ["hotel"]}, state
        )
        is True
    )


@given(
    operator=st.sampled_from([">=", "<=", "=="]),
    threshold=st.integers(min_value=0, max_value=5),
    count=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_error_count_property(
    operator: str,
    threshold: int,
    count: int,
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Property: error_count operator comparisons should match integer semantics."""
    coord = AgentHandoffCoordinator()
    state = state_factory(error_count=count)
    result = coord._evaluate_conditions(  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
        {"error_count": {operator: threshold}}, state
    )
    if operator == ">=":
        assert result is (count >= threshold)
    elif operator == "<=":
        assert result is (count <= threshold)
    else:
        assert result is (count == threshold)
