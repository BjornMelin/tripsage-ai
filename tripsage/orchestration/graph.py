# pylint: disable=import-error,too-many-instance-attributes,too-many-return-statements

"""LangGraph-based orchestrator for TripSage AI."""

from __future__ import annotations

from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.config import get_default_config
from tripsage.orchestration.handoff_coordinator import (
    HandoffTrigger,
    get_handoff_coordinator,
)
from tripsage.orchestration.nodes.accommodation_agent import AccommodationAgentNode
from tripsage.orchestration.nodes.budget_agent import BudgetAgentNode
from tripsage.orchestration.nodes.destination_research_agent import (
    DestinationResearchAgentNode,
)
from tripsage.orchestration.nodes.error_recovery import ErrorRecoveryNode
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.nodes.itinerary_agent import ItineraryAgentNode
from tripsage.orchestration.nodes.memory_update import MemoryUpdateNode
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class TripSageOrchestrator:
    """LangGraph orchestrator that coordinates all TripSage agent flows."""

    def __init__(
        self,
        services: AppServiceContainer,
        *,
        checkpointer: Any | None = None,
        config: Any | None = None,
    ):
        """Initialize the orchestrator with graph construction and checkpointing.

        Args:
            services: Application service container supplying dependencies.
            checkpointer: Optional checkpointer for state persistence
                         (defaults to MemorySaver for development)
            config: Optional configuration object (defaults to environment config)
        """
        self.services = services
        self.config = config or get_default_config()
        try:
            self.checkpoint_service = self.services.get_required_service(
                "checkpoint_service"
            )
        except ValueError as exc:
            raise ValueError(
                "TripSageOrchestrator requires a configured checkpoint service."
            ) from exc
        self.checkpointer = checkpointer
        try:
            self.memory_bridge = self.services.get_required_service("memory_bridge")
        except ValueError as exc:
            raise ValueError(
                "TripSageOrchestrator requires a configured session memory bridge."
            ) from exc
        self.handoff_coordinator = get_handoff_coordinator()
        self.graph = self._build_graph()
        self.compiled_graph = None  # Will be set in async initialize
        self._initialized = False

    async def initialize(self) -> None:
        """Async initialization for PostgreSQL checkpointer and other components."""
        if self._initialized:
            return

        # Initialize checkpointer if using PostgreSQL
        if self.checkpointer is None or isinstance(self.checkpointer, MemorySaver):
            try:
                self.checkpointer = (
                    await self.checkpoint_service.get_async_checkpointer()
                )
                logger.info("Initialized PostgreSQL checkpointer")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    (
                        "Failed to initialize PostgreSQL checkpointer, using "
                        "MemorySaver: %s"
                    ),
                    exc,
                )
                self.checkpointer = MemorySaver()

        # Compile graph with checkpointer
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
        self._initialized = True

        logger.info("TripSage LangGraph orchestrator initialized successfully")

    def _build_graph(self) -> StateGraph:
        """Construct the main orchestration graph.

        Returns:
            Configured StateGraph with all nodes and edges
        """
        logger.info("Building LangGraph orchestration graph")

        # Create the graph with our state schema
        graph = StateGraph(TravelPlanningState)

        # Add the router node (entry point for all requests)
        router_node = RouterNode(self.services)
        graph.add_node("router", router_node)

        # Add specialized agent nodes with service registry
        flight_agent_node = FlightAgentNode(self.services)
        accommodation_agent_node = AccommodationAgentNode(self.services)
        budget_agent_node = BudgetAgentNode(self.services)
        destination_research_agent_node = DestinationResearchAgentNode(self.services)
        itinerary_agent_node = ItineraryAgentNode(self.services)

        graph.add_node("flight_agent", flight_agent_node)
        graph.add_node("accommodation_agent", accommodation_agent_node)
        graph.add_node("budget_agent", budget_agent_node)
        graph.add_node("destination_research_agent", destination_research_agent_node)
        graph.add_node("itinerary_agent", itinerary_agent_node)

        # General purpose agent for unrouted requests
        graph.add_node("general_agent", self._create_general_agent())

        # Add utility nodes with service registry
        memory_update_node = MemoryUpdateNode(self.services)
        error_recovery_node = ErrorRecoveryNode(self.services)
        graph.add_node("memory_update", memory_update_node)
        graph.add_node("error_recovery", error_recovery_node)

        # Set entry point
        graph.set_entry_point("router")

        # Add conditional routing from router to agents
        graph.add_conditional_edges(
            "router",
            self._route_to_agent,
            {
                "flight_agent": "flight_agent",
                "accommodation_agent": "accommodation_agent",
                "budget_agent": "budget_agent",
                "itinerary_agent": "itinerary_agent",
                "destination_research_agent": "destination_research_agent",
                "general_agent": "general_agent",
                "error_recovery": "error_recovery",
                "end": END,
            },
        )

        # Add agent completion flows (all agents can end or continue)
        for agent in [
            "flight_agent",
            "accommodation_agent",
            "budget_agent",
            "itinerary_agent",
            "destination_research_agent",
            "general_agent",
        ]:
            graph.add_conditional_edges(
                agent,
                self._determine_next_step,
                {
                    "continue": "router",
                    "memory": "memory_update",
                    "error": "error_recovery",
                    "end": END,
                },
            )

        # Utility node flows
        graph.add_edge("memory_update", "router")
        graph.add_conditional_edges(
            "error_recovery", self._handle_recovery, {"retry": "router", "end": END}
        )

        logger.info("Graph construction completed")
        return graph

    def _route_to_agent(self, state: TravelPlanningState) -> str:
        """Determine which agent should handle the current state.

        Args:
            state: Current travel planning state

        Returns:
            Agent name to route to
        """
        current_agent = state.get("current_agent")

        # Router should have set the current_agent
        if current_agent in [
            "flight_agent",
            "accommodation_agent",
            "budget_agent",
            "itinerary_agent",
            "destination_research_agent",
            "general_agent",
        ]:
            return current_agent

        # Error case or empty state
        error_info = state.get("error_info", {})
        error_count = error_info.get("error_count", 0)
        if error_count > 2:
            return "error_recovery"

        # Default fallback
        return "general_agent"

    def _determine_next_step(self, state: TravelPlanningState) -> str:
        """Determine the next step after agent completion.

        Args:
            state: Current travel planning state

        Returns:
            Next step identifier
        """
        # Check for errors using the enhanced error structure
        error_info = state.get("error_info", {})
        if error_info.get("error_count", 0) > 0:
            return "error"

        # Check for handoff using handoff coordinator
        current_agent_value = state.get("current_agent")
        current_agent = (
            current_agent_value
            if isinstance(current_agent_value, str)
            else "general_agent"
        )
        handoff_result = self.handoff_coordinator.determine_next_agent(
            current_agent, state, HandoffTrigger.TASK_COMPLETION
        )

        if handoff_result:
            next_agent, handoff_context = handoff_result
            # Update state with handoff information
            state["current_agent"] = next_agent
            state["handoff_context"] = handoff_context.model_dump()
            return "continue"  # Continue to router for handoff

        # Check if we should update memory (e.g., learned something about user)
        if (
            state.get("user_preferences")
            or state.get("destination_info")
            or state.get("booking_progress")
        ):
            return "memory"

        # Check conversation state for natural completion
        last_message = state["messages"][-1] if state["messages"] else {}
        if last_message.get("role") == "assistant":
            # If the response indicates completion or escalation, end conversation
            keywords = ["escalation", "human support", "technical difficulties"]
            if any(
                keyword in last_message.get("content", "").lower()
                for keyword in keywords
            ):
                return "end"

            # Check if user needs to respond
            content = last_message.get("content", "")
            question_phrases = [
                "Would you like",
                "Do you want",
                "What would you prefer",
            ]
            if any(phrase in content for phrase in question_phrases):
                return "end"  # Wait for user response

            # Agent provided informational response, can continue
            return "end"

        # Default to continue conversation
        return "continue"

    def _handle_recovery(self, state: TravelPlanningState) -> str:
        """Handle error recovery decisions.

        Args:
            state: Current travel planning state

        Returns:
            Recovery action
        """
        error_info = state.get("error_info", {})
        error_count = error_info.get("error_count", 0)
        retry_threshold = 3

        if error_count < retry_threshold:
            return "retry"
        return "end"

    def _create_general_agent(self):
        """Create a general-purpose agent for handling unrouted requests.

        Returns:
            General agent function
        """

        async def general_agent(state: TravelPlanningState) -> TravelPlanningState:
            logger.info("Executing general agent")

            # Generate helpful response for general travel inquiries
            response_message = {
                "role": "assistant",
                "content": (
                    "I can assist with flight planning, accommodation searches, "
                    "budget analysis, destination research, and itinerary drafting. "
                    "Share the details you would like me to work on next."
                ),
                "agent": "general_agent",
            }

            state["messages"].append(response_message)
            state["current_agent"] = "general_agent"

            return state

        return general_agent

    async def process_message(
        self, user_id: str, message: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Main entry point for processing user messages.

        Args:
            user_id: Unique identifier for the user
            message: User message to process
            session_id: Optional session ID for conversation continuity

        Returns:
            Dictionary containing response and session information
        """
        try:
            # Ensure async initialization is complete
            await self.initialize()

            # Create initial state if new conversation
            if not session_id:
                initial_state = create_initial_state(user_id, message)
                session_id = initial_state["session_id"]
            else:
                # For existing conversations, create minimal state
                # (In production, this would load from checkpointer)
                initial_state = create_initial_state(user_id, message, session_id)

            # Hydrate state with user context and preferences from memory
            try:
                initial_state = await self.memory_bridge.hydrate_state(initial_state)
                logger.debug("Hydrated state with user context for user %s", user_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to hydrate state from memory: %s", exc)

            # Configure for session-based persistence
            runnable_config: RunnableConfig = {
                "configurable": {"thread_id": session_id}
            }

            if self.compiled_graph is None:
                raise RuntimeError(
                    "TripSageOrchestrator must be initialized before "
                    "processing messages"
                )

            result = await self.compiled_graph.ainvoke(
                initial_state, config=runnable_config
            )
            result_state = cast(TravelPlanningState, result)

            # Extract and persist insights from the conversation
            try:
                insights = await self.memory_bridge.extract_and_persist_insights(
                    result_state
                )
                logger.debug("Persisted conversation insights: %s", insights)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to persist insights to memory: %s", exc)

            # Extract response from the last assistant message
            response_content = "I'm ready to help with your travel planning!"
            for msg in reversed(result_state["messages"]):
                if msg.get("role") == "assistant":
                    response_content = msg["content"]
                    break

            logger.info("Successfully processed message for user %s", user_id)

            return {
                "response": response_content,
                "session_id": session_id,
                "agent_used": result_state.get("current_agent", "router"),
                "state": result_state,
            }

        except Exception as e:
            logger.exception("Error processing message")
            return {
                "response": (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try again."
                ),
                "session_id": session_id,
                "error": str(e),
            }

    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """Get the current state for a session.

        Args:
            session_id: Session ID to retrieve state for

        Returns:
            Session state or None if not found
        """
        try:
            if self.compiled_graph is None:
                raise RuntimeError(
                    "TripSageOrchestrator must be initialized before fetching state"
                )

            config: RunnableConfig = {"configurable": {"thread_id": session_id}}
            state = self.compiled_graph.get_state(config)
            return state.values if state else None
        except Exception:
            logger.exception("Error retrieving session state")
            return None
