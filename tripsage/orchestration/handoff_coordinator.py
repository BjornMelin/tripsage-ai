"""Inter-Agent Handoff Coordinator for LangGraph

This module provides intelligent agent handoff coordination within the LangGraph
orchestration system, enabling seamless context preservation and task routing
between specialized agents.
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

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
    DESTINATION_RESEARCH = "destination_research"
    ITINERARY_PLANNING = "itinerary_planning"
    GENERAL_ASSISTANCE = "general_assistance"
    ERROR_HANDLING = "error_handling"


class HandoffRule(BaseModel):
    """Configuration for agent handoff rules."""

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
                from_agent="general",
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
                from_agent="general",
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
            # Destination research handoffs
            HandoffRule(
                from_agent="general",
                to_agent="destination_research_agent",
                trigger=HandoffTrigger.USER_REQUEST,
                conditions={
                    "keywords": [
                        "destination",
                        "place",
                        "where",
                        "attractions",
                        "things to do",
                        "research",
                    ]
                },
                priority=9,
                context_keys=[
                    "destination",
                    "travel_dates",
                    "interests",
                    "travel_style",
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
                to_agent="general",
                trigger=HandoffTrigger.ERROR_RECOVERY,
                conditions={"error_count": {">=": 3}},
                priority=15,
                context_keys=["error_history", "last_successful_state"],
            ),
        ]

        self.handoff_rules.extend(default_rules)
        logger.info(f"Initialized {len(default_rules)} default handoff rules")

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
            "destination_research_agent": {
                AgentCapability.DESTINATION_RESEARCH,
            },
            "itinerary_agent": {
                AgentCapability.ITINERARY_PLANNING,
            },
            "general": {
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
        logger.debug(f"Added handoff rule: {rule.from_agent} -> {rule.to_agent}")

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
            f"Determining next agent from {current_agent} with trigger {trigger}"
        )

        # Analyze state and find matching rules
        for rule in self.handoff_rules:
            if self._matches_rule(rule, current_agent, state, trigger):
                handoff_context = self._create_handoff_context(
                    rule, current_agent, state, trigger
                )

                logger.info(
                    f"Handoff determined: {current_agent} -> {rule.to_agent} "
                    f"({trigger})"
                )
                return rule.to_agent, handoff_context

        logger.debug(f"No handoff needed for {current_agent}")
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
        if rule.from_agent != "*" and rule.from_agent != current_agent:
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
            if condition_key == "keywords":
                # Check if any keywords appear in recent messages
                if not self._has_keywords(condition_value, state):
                    return False

            elif condition_key == "has_flights":
                flight_selections = state.get("flight_selections", [])
                if (condition_value and not flight_selections) or (
                    not condition_value and flight_selections
                ):
                    return False

            elif condition_key == "has_accommodation":
                accommodation_selections = state.get("accommodation_selections", [])
                if (condition_value and not accommodation_selections) or (
                    not condition_value and accommodation_selections
                ):
                    return False

            elif condition_key == "error_count":
                error_history = state.get("error_history", [])
                error_count = len(error_history)

                if isinstance(condition_value, dict):
                    for operator, threshold in condition_value.items():
                        if (
                            (operator == ">=" and error_count < threshold)
                            or (operator == "<=" and error_count > threshold)
                            or (operator == "==" and error_count != threshold)
                        ):
                            return False
                else:
                    if error_count != condition_value:
                        return False

            elif condition_key in state:
                # Direct state value comparison
                if state[condition_key] != condition_value:
                    return False

        return True

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
        preserved_context = {}
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
        if trigger == HandoffTrigger.USER_REQUEST:
            return f"User request requires {rule.to_agent} capabilities"
        elif trigger == HandoffTrigger.TASK_COMPLETION:
            return f"Task completed, transitioning to {rule.to_agent} for next phase"
        elif trigger == HandoffTrigger.MISSING_CAPABILITY:
            return (
                f"Current agent lacks required capability, "
                f"transferring to {rule.to_agent}"
            )
        elif trigger == HandoffTrigger.ERROR_RECOVERY:
            return f"Error recovery required, transferring to {rule.to_agent}"
        elif trigger == HandoffTrigger.TIMEOUT:
            return f"Operation timeout, transferring to {rule.to_agent}"
        else:
            return f"Handoff to {rule.to_agent} triggered by {trigger}"

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
            f"Executing handoff: {handoff_context.from_agent} -> "
            f"{handoff_context.to_agent}"
        )

        # Update state with handoff information
        agent_history = state.get("agent_history", [])
        agent_history.append(
            {
                "agent": handoff_context.from_agent,
                "handoff_to": handoff_context.to_agent,
                "timestamp": handoff_context.timestamp,
                "trigger": handoff_context.trigger,
                "reason": handoff_context.reason,
            }
        )
        state["agent_history"] = agent_history

        # Set current agent
        state["current_agent"] = handoff_context.to_agent

        # Preserve handoff context in state
        state["handoff_context"] = handoff_context.model_dump()

        # Merge preserved context into state
        for key, value in handoff_context.preserved_context.items():
            state[key] = value

        logger.debug(f"Handoff executed successfully to {handoff_context.to_agent}")
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


# Global coordinator instance
_global_handoff_coordinator: AgentHandoffCoordinator | None = None


def get_handoff_coordinator() -> AgentHandoffCoordinator:
    """Get the global handoff coordinator instance."""
    global _global_handoff_coordinator
    if _global_handoff_coordinator is None:
        _global_handoff_coordinator = AgentHandoffCoordinator()
    return _global_handoff_coordinator
