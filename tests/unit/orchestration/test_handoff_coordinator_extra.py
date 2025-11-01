"""Extra tests for handoff coordinator: precedence and error_count map."""

from __future__ import annotations

from tripsage.orchestration.handoff_coordinator import (
    AgentHandoffCoordinator,
    HandoffRule,
    HandoffTrigger,
)
from tripsage.orchestration.state import create_initial_state


def test_first_matching_rule_wins() -> None:
    """Coordinator selects the first matching rule (insertion order)."""
    coord = AgentHandoffCoordinator()
    coord.handoff_rules.clear()

    rule_low = HandoffRule(
        from_agent="general_agent",
        to_agent="flight_agent",
        trigger=HandoffTrigger.USER_REQUEST,
        conditions={"keywords": ["flight"]},
        priority=5,
    )
    rule_high = HandoffRule(
        from_agent="general_agent",
        to_agent="accommodation_agent",
        trigger=HandoffTrigger.USER_REQUEST,
        conditions={"keywords": ["flight"]},
        priority=10,
    )
    coord.handoff_rules.extend([rule_low, rule_high])

    st = create_initial_state("u", "book a flight")
    tup = coord.determine_next_agent("general_agent", st, HandoffTrigger.USER_REQUEST)
    assert tup is not None
    next_agent, _ctx = tup
    # The first rule in the list should be chosen
    assert next_agent == "flight_agent"


def test_error_count_parsing_and_eval() -> None:
    """Dict operator thresholds should be respected for error_count condition."""
    coord = AgentHandoffCoordinator()
    coord.handoff_rules.clear()
    coord.handoff_rules.append(
        HandoffRule(
            from_agent="router",
            to_agent="error_recovery",
            trigger=HandoffTrigger.TASK_COMPLETION,
            conditions={"error_count": {">=": 2}},
            priority=9,
        )
    )
    st = create_initial_state("u", "hi")
    st["error_info"]["error_history"] = [{"e": 1}]
    assert (
        coord.determine_next_agent("router", st, HandoffTrigger.TASK_COMPLETION) is None
    )
    st["error_info"]["error_history"] = [{"e": 1}, {"e": 2}]
    decision = coord.determine_next_agent("router", st, HandoffTrigger.TASK_COMPLETION)
    assert decision is not None and decision[0] == "error_recovery"
