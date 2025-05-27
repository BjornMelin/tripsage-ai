"""
Main LangGraph orchestrator for TripSage AI.

This module implements the core graph-based orchestration system that coordinates
all specialized agents and manages the conversation flow.
"""

from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from tripsage.orchestration.config import get_default_config
from tripsage.orchestration.nodes.error_recovery import ErrorRecoveryNode
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.nodes.memory_update import MemoryUpdateNode
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class TripSageOrchestrator:
    """
    Main LangGraph orchestrator for TripSage AI.

    This class builds and manages the graph-based workflow that coordinates
    all specialized travel planning agents using LangGraph.
    """

    def __init__(
        self, checkpointer: Optional[Any] = None, config: Optional[Any] = None
    ):
        """
        Initialize the orchestrator with graph construction and checkpointing.

        Args:
            checkpointer: Optional checkpointer for state persistence
                         (defaults to MemorySaver for development)
            config: Optional configuration object (defaults to environment config)
        """
        self.config = config or get_default_config()
        self.checkpointer = checkpointer or MemorySaver()
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)

        logger.info("TripSage LangGraph orchestrator initialized successfully")

    def _build_graph(self) -> StateGraph:
        """
        Construct the main orchestration graph.

        Returns:
            Configured StateGraph with all nodes and edges
        """
        logger.info("Building LangGraph orchestration graph")

        # Create the graph with our state schema
        graph = StateGraph(TravelPlanningState)

        # Add the router node (entry point for all requests)
        router_node = RouterNode()
        graph.add_node("router", router_node)

        # Add specialized agent nodes
        flight_agent_node = FlightAgentNode()
        graph.add_node("flight_agent", flight_agent_node)

        # Stub nodes for Phase 2 migration (to be replaced)
        graph.add_node(
            "accommodation_agent", self._create_stub_node("accommodation_agent")
        )
        graph.add_node("budget_agent", self._create_stub_node("budget_agent"))
        graph.add_node("itinerary_agent", self._create_stub_node("itinerary_agent"))
        graph.add_node(
            "destination_agent", self._create_stub_node("destination_agent")
        )
        graph.add_node("travel_agent", self._create_stub_node("travel_agent"))

        # Add utility nodes
        memory_update_node = MemoryUpdateNode()
        error_recovery_node = ErrorRecoveryNode()
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
                "destination_agent": "destination_agent",
                "travel_agent": "travel_agent",
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
            "destination_agent",
            "travel_agent",
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
        """
        Determine which agent should handle the current state.

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
            "destination_agent",
            "travel_agent",
        ]:
            return current_agent

        # Error case or empty state
        error_count = state.get("error_count", 0)
        if error_count > 2:
            return "error_recovery"

        # Default fallback
        return "travel_agent"

    def _determine_next_step(self, state: TravelPlanningState) -> str:
        """
        Determine the next step after agent completion.

        Args:
            state: Current travel planning state

        Returns:
            Next step identifier
        """
        # Check for errors
        if state.get("error_count", 0) > 0:
            return "error"

        # Check if we should update memory (e.g., learned something about user)
        if (
            state.get("user_preferences")
            or state.get("destination_info")
            or state.get("budget_constraints")
        ):
            return "memory"

        # Check if conversation should continue
        last_message = state["messages"][-1] if state["messages"] else {}
        if last_message.get("role") == "assistant":
            # Agent provided a response, conversation can end or continue
            return "end"

        # Default to continue conversation
        return "continue"

    def _handle_recovery(self, state: TravelPlanningState) -> str:
        """
        Handle error recovery decisions.

        Args:
            state: Current travel planning state

        Returns:
            Recovery action
        """
        error_count = state.get("error_count", 0)
        retry_threshold = 3

        if error_count < retry_threshold:
            return "retry"
        else:
            return "end"

    def _create_stub_node(self, node_name: str):
        """
        Create a stub node for Phase 1 implementation.

        These will be replaced with full implementations in Phase 2.

        Args:
            node_name: Name of the node

        Returns:
            Simple stub function
        """

        async def stub_node(state: TravelPlanningState) -> TravelPlanningState:
            logger.info(f"Executing stub node: {node_name}")

            # Add a simple response message
            response_message = {
                "role": "assistant",
                "content": (
                    f"I'm {node_name} and I'm ready to help with your travel planning! "
                    f"(This is a Phase 1 implementation - "
                    f"full functionality coming in Phase 2)"
                ),
                "agent": node_name,
            }

            state["messages"].append(response_message)
            return state

        return stub_node

    async def process_message(
        self, user_id: str, message: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user messages.

        Args:
            user_id: Unique identifier for the user
            message: User message to process
            session_id: Optional session ID for conversation continuity

        Returns:
            Dictionary containing response and session information
        """
        try:
            # Create initial state if new conversation
            if not session_id:
                initial_state = create_initial_state(user_id, message)
                session_id = initial_state["session_id"]
            else:
                # For existing conversations, create minimal state
                # (In production, this would load from checkpointer)
                initial_state = create_initial_state(user_id, message, session_id)

            # Configure for session-based persistence
            config = {"configurable": {"thread_id": session_id}}

            # Process through the graph
            result = await self.compiled_graph.ainvoke(initial_state, config=config)

            # Extract response from the last assistant message
            response_content = "I'm ready to help with your travel planning!"
            for msg in reversed(result["messages"]):
                if msg.get("role") == "assistant":
                    response_content = msg["content"]
                    break

            logger.info(f"Successfully processed message for user {user_id}")

            return {
                "response": response_content,
                "session_id": session_id,
                "agent_used": result.get("current_agent", "router"),
                "state": result,
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try again."
                ),
                "session_id": session_id,
                "error": str(e),
            }

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state for a session.

        Args:
            session_id: Session ID to retrieve state for

        Returns:
            Session state or None if not found
        """
        try:
            config = {"configurable": {"thread_id": session_id}}
            state = self.compiled_graph.get_state(config)
            return state.values if state else None
        except Exception as e:
            logger.error(f"Error retrieving session state: {str(e)}")
            return None
