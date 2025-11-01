"""BudgetAgent spending analysis tests covering variance formatting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.budget_agent import BudgetAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Make services stub."""
    c = AppServiceContainer()
    c.configuration_service = MagicMock()
    c.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    return c


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.budget_agent")
async def test_analyze_spending_with_budget_and_expenses() -> None:
    """_analyze_spending should compute variance analysis when data present."""
    node = BudgetAgentNode(_make_services())
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    st = create_initial_state("u", "")
    # Seed prior optimize and track results
    st["budget_analyses"].append(
        {
            "operation": "optimize",
            "analysis": {
                "allocations": {
                    "flights": 500.0,
                    "accommodation": 1000.0,
                    "activities": 300.0,
                }
            },
        }
    )
    st["budget_analyses"].append(
        {
            "operation": "track",
            "analysis": {
                "categories": {
                    "flights": 450.0,
                    "accommodation": 1100.0,
                    "activities": 250.0,
                }
            },
        }
    )

    res = await node._analyze_spending({"trip_id": "t1"}, st)  # type: ignore[reportPrivateUsage]
    assert res.get("variance_analysis")
    va = res["variance_analysis"]
    # flights under budget, accommodation over, activities under or equal
    assert va["flights"]["status"] in {"under", "on_track"}
    assert va["accommodation"]["status"] in {"over", "on_track"}
