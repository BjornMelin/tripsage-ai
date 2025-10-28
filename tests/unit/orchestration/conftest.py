"""Shared orchestration test fixtures.

Provides a lightweight state factory and LLM mock aliases for unit tests.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

import pytest

from tripsage.orchestration.state import TravelPlanningState, create_initial_state


@pytest.fixture
def state_factory() -> Callable[..., TravelPlanningState]:
    """Factory to create TravelPlanningState variants easily.

    Usage:
        state = state_factory(
            user_id="u1",
            message="hi",
            current_agent="router",
            error_count=2,
        )
    """

    def _make(
        user_id: str = "user-1",
        message: str = "hello",
        current_agent: str | None = None,
        error_count: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> TravelPlanningState:
        """Make state."""
        st = create_initial_state(user_id=user_id, message=message)
        if current_agent is not None:
            st["current_agent"] = current_agent
        if error_count is not None:
            st["error_info"]["error_count"] = int(error_count)
            st["error_info"]["error_history"] = [{}] * int(error_count)
        if extra:
            for k, v in extra.items():
                st[k] = v  # type: ignore[reportGeneralTypeIssues]
        return st

    return _make


@pytest.fixture
def cleanup_env() -> Generator[None]:
    """No-op fixture placeholder for future environment cleanup if needed."""
    yield
