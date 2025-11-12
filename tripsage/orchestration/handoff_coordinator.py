"""Inter-Agent Handoff Coordinator for LangGraph.

This module provides intelligent agent handoff coordination within the LangGraph
orchestration system, enabling seamless context preservation and task routing
between specialized agents.
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from tripsage.orchestration.state import TravelPlanningState


logger = logging.getLogger(__name__)


class HandoffTrigger(str, Enum):
    """Enumeration of handoff trigger types."""

    USER_REQUEST = "user_request"
    TASK_COMPLETION = "task_completion"
    MISSING_CAPABILITY = "missing_capability"
    ERROR_RECOVERY = "error_recovery"
    TIMEOUT = "timeout"
    QUALITY_THRESHOLD = "quality_threshold"


class AgentCapability(str, Enum):
    """Enumeration of agent capabilities."""

    FLIGHT_SEARCH = "flight_search"
    ACCOMMODATION_SEARCH = "accommodation_search"
    BUDGET_OPTIMIZATION = "budget_optimization"
    ITINERARY_PLANNING = "itinerary_planning"
    GENERAL_ASSISTANCE = "general_assistance"
    ERROR_HANDLING = "error_handling"


class HandoffRule(BaseModel):
    """Configuration for agent handoff rules."""

    model_config = ConfigDict(extra="forbid")

    from_agent: str = Field(description="Source agent name")
    to_agent: str = Field(description="Target agent name")
    trigger: HandoffTrigger = Field(description="Handoff trigger type")
    conditions: dict[str, Any] = Field(
        default_factory=dict, description="Handoff conditions"
    )
    priority: int = Field(default=1, description="Rule priority (higher wins)")
    context_keys: list[str] = Field(
        default_factory=list, description="State keys to preserve in handoff"
    )


class HandoffContext(BaseModel):
    """Context information for agent handoffs."""

    model_config = ConfigDict(extra="forbid")

    from_agent: str = Field(description="Source agent")
    to_agent: str = Field(description="Target agent")
    trigger: HandoffTrigger = Field(description="Handoff trigger")
    reason: str = Field(description="Reason for handoff")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    preserved_context: dict[str, Any] = Field(
        default_factory=dict, description="Context to preserve"
    )
    handoff_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AgentHandoffCoordinator:
    """Coordinates agent handoffs within the LangGraph orchestration system.

    This coordinator analyzes the current state, determines appropriate handoff
    targets, and manages context preservation during agent transitions.
    """

    def __init__(self):
        """Initialize the handoff coordinator."""
        self.handoff_rules: list[HandoffRule] = []
        self.agent_capabilities: dict[str, set[AgentCapability]] = {}
        self.handoff_history: list[HandoffContext] = []
        self._initialize_default_rules()
        self._initialize_agent_capabilities()

    def _initialize_default_rules(self) -> None:
        """Initialize default handoff rules."""
        default_rules = [
            # Flight-related handoffs
            HandoffRule(
                from_agent="general_agent",
                to_agent="flight_agent",
                trigger=HandoffTrigger.USER_REQUEST,
                conditions={
                    "keywords": [
                        "flight",
                        "fly",
                        "airplane",
                        "airline",
                        "departure",
                        "arrival",
                    ]
                },
                priority=10,
                context_keys=[
                    "travel_dates",
                    "departure_location",
                    "destination",
                    "passenger_count",
                ],
            ),
            # Accommodation handoffs
            HandoffRule(
                from_agent="general_agent",
                to_agent="accommodation_agent",
                trigger=HandoffTrigger.USER_REQUEST,
                conditions={
                    "keywords": [
                        "hotel",
                        "accommodation",
                        "stay",
                        "room",
                        "booking",
                        "airbnb",
                    ]
                },
                priority=10,
                context_keys=[
                    "travel_dates",
                    "destination",
                    "guest_count",
                    "accommodation_preferences",
                ],
            ),
            # Budget optimization handoffs
            HandoffRule(
                from_agent="*",  # Any agent
                to_agent="budget_agent",
                trigger=HandoffTrigger.USER_REQUEST,
                conditions={
                    "keywords": [
                        "budget",
                        "cost",
                        "price",
                        "money",
                        "expensive",
                        "cheap",
                        "afford",
                    ]
                },
                priority=8,
                context_keys=[
                    "budget_constraints",
                    "total_budget",
                    "expense_categories",
                ],
            ),
            # Itinerary planning handoffs
            HandoffRule(
                from_agent="*",
                to_agent="itinerary_agent",
                trigger=HandoffTrigger.TASK_COMPLETION,
                conditions={"has_flights": True, "has_accommodation": True},
                priority=7,
                context_keys=[
                    "flight_selections",
                    "accommodation_selections",
                    "destination_info",
                    "travel_dates",
                ],
            ),
            # Error recovery handoffs
            HandoffRule(
                from_agent="*",
                to_agent="general_agent",
                trigger=HandoffTrigger.ERROR_RECOVERY,
                conditions={"error_count": {">=": 3}},
                priority=15,
                context_keys=["error_history", "last_successful_state"],
            ),
        ]

        self.handoff_rules.extend(default_rules)
        logger.info("Initialized %s default handoff rules", len(default_rules))

    def _initialize_agent_capabilities(self) -> None:
        """Initialize agent capability mappings."""
        self.agent_capabilities = {
            "flight_agent": {
                AgentCapability.FLIGHT_SEARCH,
            },
            "accommodation_agent": {
                AgentCapability.ACCOMMODATION_SEARCH,
            },
            "budget_agent": {
                AgentCapability.BUDGET_OPTIMIZATION,
            },
            "itinerary_agent": {
                AgentCapability.ITINERARY_PLANNING,
            },
            "general_agent": {
                AgentCapability.GENERAL_ASSISTANCE,
                AgentCapability.ERROR_HANDLING,
            },
        }

    def add_handoff_rule(self, rule: HandoffRule) -> None:
        """Add a custom handoff rule.

        Args:
            rule: Handoff rule to add
        """
        self.handoff_rules.append(rule)
        # Sort by priority (higher priority first)
        self.handoff_rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug("Added handoff rule: %s -> %s", rule.from_agent, rule.to_agent)

    def determine_next_agent(
        self,
        current_agent: str,
        state: TravelPlanningState,
        trigger: HandoffTrigger = HandoffTrigger.USER_REQUEST,
    ) -> tuple[str, HandoffContext] | None:
        """Determine the next agent based on current state and handoff rules.

        Args:
            current_agent: Currently active agent
            state: Current LangGraph state
            trigger: Handoff trigger type

        Returns:
            Tuple of (next_agent_name, handoff_context) or None if no handoff needed
        """
        logger.debug(
            "Determining next agent from %s with trigger %s", current_agent, trigger
        )

        # Analyze state and find matching rules
        for rule in self.handoff_rules:
            if self._matches_rule(rule, current_agent, state, trigger):
                handoff_context = self._create_handoff_context(
                    rule, current_agent, state, trigger
                )

                logger.info(
                    "Handoff determined: %s -> %s (%s)",
                    current_agent,
                    rule.to_agent,
                    trigger,
                )
                return rule.to_agent, handoff_context

        logger.debug("No handoff needed for %s", current_agent)
        return None

    def _matches_rule(
        self,
        rule: HandoffRule,
        current_agent: str,
        state: TravelPlanningState,
        trigger: HandoffTrigger,
    ) -> bool:
        """Check if a handoff rule matches the current situation.

        Args:
            rule: Handoff rule to check
            current_agent: Current agent name
            state: Current state
            trigger: Handoff trigger

        Returns:
            True if rule matches
        """
        # Check agent match
        if rule.from_agent not in {"*", current_agent}:
            return False

        # Check trigger match
        if rule.trigger != trigger:
            return False

        # Check conditions
        return self._evaluate_conditions(rule.conditions, state)

    def _evaluate_conditions(
        self, conditions: dict[str, Any], state: TravelPlanningState
    ) -> bool:
        """Evaluate handoff conditions against current state.

        Args:
            conditions: Rule conditions to evaluate
            state: Current state

        Returns:
            True if all conditions are met
        """
        for condition_key, condition_value in conditions.items():
            if not self._condition_matches(condition_key, condition_value, state):
                return False
        return True

    def _condition_matches(
        self, condition_key: str, condition_value: Any, state: TravelPlanningState
    ) -> bool:
        """Return True when a handoff condition is satisfied."""
        result: bool = True

        if condition_key == "keywords":
            result = self._has_keywords(condition_value, state)

        elif condition_key == "has_flights":
            has_flights = bool(state.get("flight_selections", []))
            if bool(condition_value) != has_flights:
                result = False

        elif condition_key == "has_accommodation":
            has_accommodation = bool(state.get("accommodation_selections", []))
            if bool(condition_value) != has_accommodation:
                result = False

        elif condition_key == "error_count":
            # error_info is a structured dict in state;
            # fall back to history list if present.
            error_info = state.get("error_info", {})
            error_history = error_info.get("error_history", [])
            error_count = (
                len(cast(list[dict[str, Any]], error_history))
                if isinstance(error_history, list)
                else 0
            )

            if isinstance(condition_value, dict):
                # Build a typed operator→threshold map from possibly unknown dict views
                raw: dict[object, object] = cast(dict[object, object], condition_value)
                cond_map: dict[str, int] = {}
                for k, v in raw.items():
                    key_str: str = str(k)
                    if isinstance(v, (int, str)):
                        try:
                            val_int: int = int(v)
                        except ValueError:
                            continue
                        cond_map[key_str] = val_int
                if not cond_map:
                    return False
                for operator, threshold in cond_map.items():
                    if operator == ">=" and error_count < threshold:
                        result = False
                        break
                    if operator == "<=" and error_count > threshold:
                        result = False
                        break
                    if operator == "==" and error_count != threshold:
                        result = False
                        break
            # Single-threshold comparison
            elif isinstance(condition_value, (int, str)):
                try:
                    threshold_int = int(condition_value)
                    result = error_count == threshold_int
                except ValueError:
                    result = False
            else:
                result = False

        elif condition_key in state:
            # Avoid passing Unknown to bool(); compare directly to produce a bool
            state_val: Any = state.get(condition_key)
            result = state_val == condition_value

        return result

    def _has_keywords(self, keywords: list[str], state: TravelPlanningState) -> bool:
        """Check if any keywords appear in recent messages.

        Args:
            keywords: Keywords to search for
            state: Current state

        Returns:
            True if any keyword found
        """
        messages = state.get("messages", [])
        if not messages:
            return False

        # Check last few messages for keywords
        recent_messages = messages[-3:] if len(messages) >= 3 else messages

        for message in recent_messages:
            content = message.get("content", "").lower()
            if any(keyword.lower() in content for keyword in keywords):
                return True

        return False

    def _create_handoff_context(
        self,
        rule: HandoffRule,
        current_agent: str,
        state: TravelPlanningState,
        trigger: HandoffTrigger,
    ) -> HandoffContext:
        """Create handoff context with preserved state information.

        Args:
            rule: Matching handoff rule
            current_agent: Current agent
            state: Current state
            trigger: Handoff trigger

        Returns:
            HandoffContext with preserved information
        """
        # Extract preserved context based on rule
        preserved_context: dict[str, Any] = {}
        for key in rule.context_keys:
            if key in state:
                preserved_context[key] = state[key]

        # Generate handoff reason
        reason = self._generate_handoff_reason(rule, trigger, state)

        handoff_context = HandoffContext(
            from_agent=current_agent,
            to_agent=rule.to_agent,
            trigger=trigger,
            reason=reason,
            preserved_context=preserved_context,
            handoff_metadata={
                "rule_priority": rule.priority,
                "conditions_met": rule.conditions,
                "context_keys_preserved": rule.context_keys,
            },
        )

        # Add to history
        self.handoff_history.append(handoff_context)

        return handoff_context

    def _generate_handoff_reason(
        self, rule: HandoffRule, trigger: HandoffTrigger, state: TravelPlanningState
    ) -> str:
        """Generate human-readable handoff reason."""
        reasons = {
            HandoffTrigger.USER_REQUEST: (
                f"User request requires {rule.to_agent} capabilities"
            ),
            HandoffTrigger.TASK_COMPLETION: (
                f"Task completed, transitioning to {rule.to_agent} for next phase"
            ),
            HandoffTrigger.MISSING_CAPABILITY: (
                "Current agent lacks required capability, "
                f"transferring to {rule.to_agent}"
            ),
            HandoffTrigger.ERROR_RECOVERY: (
                f"Error recovery required, transferring to {rule.to_agent}"
            ),
            HandoffTrigger.TIMEOUT: (
                f"Operation timeout, transferring to {rule.to_agent}"
            ),
            HandoffTrigger.QUALITY_THRESHOLD: (
                f"Quality threshold unmet, handing off to {rule.to_agent}"
            ),
        }

        return reasons.get(
            trigger, f"Handoff to {rule.to_agent} triggered by {trigger}"
        )

    async def execute_handoff(
        self, handoff_context: HandoffContext, state: TravelPlanningState
    ) -> TravelPlanningState:
        """Execute agent handoff and update state.

        Args:
            handoff_context: Handoff context information
            state: Current state

        Returns:
            Updated state with handoff information
        """
        logger.info(
            "Executing handoff: %s -> %s",
            handoff_context.from_agent,
            handoff_context.to_agent,
        )

        # Update state with handoff information
        agent_history = state.get("agent_history", [])
        agent_history.append(handoff_context.to_agent)
        state["agent_history"] = agent_history

        # Set current agent
        state["current_agent"] = handoff_context.to_agent

        # Preserve handoff context in state
        state["handoff_context"] = handoff_context.model_dump()

        # Merge preserved context into state
        for key, value in handoff_context.preserved_context.items():
            state[key] = value

        logger.debug("Handoff executed successfully to %s", handoff_context.to_agent)
        return state

    def get_agent_capabilities(self, agent_name: str) -> set[AgentCapability]:
        """Get capabilities for a specific agent."""
        return self.agent_capabilities.get(agent_name, set())

    def can_handle_capability(
        self, agent_name: str, capability: AgentCapability
    ) -> bool:
        """Check if an agent can handle a specific capability."""
        agent_caps = self.get_agent_capabilities(agent_name)
        return capability in agent_caps

    def find_agents_with_capability(self, capability: AgentCapability) -> list[str]:
        """Find all agents that can handle a specific capability."""
        return [
            agent
            for agent, caps in self.agent_capabilities.items()
            if capability in caps
        ]

    def get_handoff_history(self, limit: int = 10) -> list[HandoffContext]:
        """Get recent handoff history."""
        return self.handoff_history[-limit:]

    def clear_handoff_history(self) -> None:
        """Clear handoff history."""
        self.handoff_history.clear()
        logger.info("Handoff history cleared")


@lru_cache(maxsize=1)
def get_handoff_coordinator() -> AgentHandoffCoordinator:
    """Return a cached handoff coordinator instance."""
    return AgentHandoffCoordinator()
