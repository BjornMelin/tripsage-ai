"""BudgetAgent value scoring and comparison invariants (property-based)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.budget_agent import BudgetAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Make a service container."""
    container = AppServiceContainer()
    container.configuration_service = MagicMock()
    container.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-5-nano",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    return container


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.budget_agent")
@settings(max_examples=50, deadline=None)
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                "name": st.text(min_size=1, max_size=10),
                "cost": st.floats(
                    min_value=1.0,
                    max_value=2000.0,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                "rating": st.floats(
                    min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
                ),
                "features": st.lists(st.text(min_size=0, max_size=6), max_size=5),
            }
        ),
        min_size=1,
        max_size=10,
    ),
    st.floats(min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False),
)
async def test_compare_costs_orders_and_best_within_budget(
    options: list[dict[str, Any]], budget: float
) -> None:
    """_compare_costs should sort by value_score desc and pick first within budget."""
    node = BudgetAgentNode(_make_services())
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    stt = create_initial_state("u", "")
    out = await node._compare_costs(  # pyright: ignore[reportPrivateUsage]
        {"category": "test", "options": options, "budget": budget},
        stt,
    )
    analyzed = out.get("analyzed_options", [])
    # Sorted descending by value_score
    scores = [float(x.get("value_score", 0.0)) for x in analyzed]
    assert scores == sorted(scores, reverse=True)
    # Best within budget is first analyzed option satisfying the constraint
    first_within = next((x for x in analyzed if x.get("within_budget", True)), None)
    if first_within is None:
        assert out.get("best_value") is None or out.get("budget", 0) == 0
    else:
        assert out.get("best_value") == first_within


def test_value_score_monotonicity() -> None:
    """_calculate_value_score should reward higher rating, more features, lower cost."""
    node = BudgetAgentNode(_make_services())
    # Base case
    base = {"cost": 500, "rating": 3.0, "features": ["wifi"]}
    higher_rating = {"cost": 500, "rating": 4.0, "features": ["wifi"]}
    more_features = {"cost": 500, "rating": 3.0, "features": ["wifi", "pool"]}
    lower_cost = {"cost": 400, "rating": 3.0, "features": ["wifi"]}

    s_base = node._calculate_value_score(base, "")  # type: ignore[reportPrivateUsage]
    s_rating = node._calculate_value_score(higher_rating, "")  # type: ignore[reportPrivateUsage]
    s_features = node._calculate_value_score(more_features, "")  # type: ignore[reportPrivateUsage]
    s_lower_cost = node._calculate_value_score(lower_cost, "")  # type: ignore[reportPrivateUsage]

    assert s_rating > s_base
    assert s_features > s_base
    assert s_lower_cost > s_base
