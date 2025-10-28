"""BudgetAgent tests: tool binding and compare logic guards."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.budget_agent import BudgetAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Make services stub."""
    container = AppServiceContainer()
    container.configuration_service = MagicMock()
    container.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    return container


@pytest.mark.asyncio
async def test_compare_costs_guard_on_empty_options() -> None:
    """_compare_costs returns safe payload when options list is empty."""
    services = _make_services()
    node = BudgetAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    # Empty options should not raise; returns message in result
    result = await node._compare_costs(  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
        {"category": "flights", "options": []}, create_initial_state("u1", "")
    )
    assert result.get("options_count") == 0

@pytest.mark.asyncio
@given(
    options=st.lists(
        st.dictionaries(
            keys=st.sampled_from(["cost", "rating", "value_score"]),
            values=st.one_of(
                st.floats(allow_nan=False, allow_infinity=False, width=32),
                st.integers(min_value=0, max_value=1000),
            ),
            max_size=4,
        ),
        min_size=0,
        max_size=6,
    )
)
@settings(max_examples=10, deadline=250, suppress_health_check=[HealthCheck.too_slow])
async def test_compare_costs_property(options: list[dict[str, object]]) -> None:
    """Property: _compare_costs should not raise and returns coherent shape."""
    services = _make_services()
    node = BudgetAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    result = await node._compare_costs(  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
        {"category": "test", "options": options}, create_initial_state("u1", "")
    )
    if not options:
        assert result.get("options_count") == 0
    else:
        assert isinstance(result.get("analyzed_options"), list)
