"""Memory update node implementation for LangGraph orchestration.

This module handles updating persistent memory and session state with
insights learned during conversation.
"""

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class MemoryUpdateNode(BaseAgentNode):
    """Node for updating persistent memory and session state.

    This node extracts learnable insights from conversations and updates
    both the knowledge graph and session data for future reference.
    """

    def __init__(self, service_registry):
        """Initialize the memory update node."""
        super().__init__("memory_update", service_registry)

    def _initialize_tools(self) -> None:
        """Initialize memory management tools using simple tool catalog."""
        from tripsage.orchestration.tools.simple_tools import get_tools_for_agent

        # Get tools for memory update agent using simple catalog
        self.available_tools = get_tools_for_agent("memory_update")

        # Extract memory tool for convenience
        self.memory_tool = next(
            (tool for tool in self.available_tools if "memory" in tool.name.lower()),
            None,
        )

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Update memory with conversation insights.

        Args:
            state: Current travel planning state

        Returns:
            State after memory updates
        """
        # Extract learnable insights from conversation
        insights = await self._extract_insights(state)

        if insights:
            # Update knowledge graph via Memory MCP
            await self._update_knowledge_graph(state, insights)

            # Update session data in Supabase
            await self._update_session_data(state)

            logger.info(
                "Updated memory with %s insights for user %s",
                len(insights),
                state["user_id"],
            )

        return state

    async def _extract_insights(self, state: TravelPlanningState) -> list[str]:
        """Extract learnable insights from conversation state.

        Args:
            state: Current conversation state

        Returns:
            List of insights to store in memory
        """
        insights = []

        # Extract budget preferences
        if state.get("budget_constraints"):
            budget_info = state["budget_constraints"]
            if isinstance(budget_info, dict):
                for key, value in budget_info.items():
                    insights.append(f"Budget preference - {key}: {value}")
            else:
                insights.append(f"Budget constraint: {budget_info}")

        # Extract user preferences
        if state.get("user_preferences"):
            for pref_type, value in state["user_preferences"].items():
                insights.append(f"Travel preference - {pref_type}: {value}")

        # Extract destination interests
        if state.get("destination_info"):
            dest_info = state["destination_info"]
            if isinstance(dest_info, dict):
                if dest_info.get("name"):
                    insights.append(f"Interested in destination: {dest_info['name']}")
                if dest_info.get("preferences"):
                    for pref in dest_info["preferences"]:
                        insights.append(f"Destination preference: {pref}")
            else:
                insights.append(f"Interested in destination: {dest_info}")

        # Extract travel dates and patterns
        if state.get("travel_dates"):
            dates_info = state["travel_dates"]
            if isinstance(dates_info, dict):
                if dates_info.get("departure"):
                    insights.append(
                        f"Departure date preference: {dates_info['departure']}"
                    )
                if dates_info.get("return"):
                    insights.append(f"Return date preference: {dates_info['return']}")
                if dates_info.get("flexibility"):
                    insights.append(f"Date flexibility: {dates_info['flexibility']}")

        # Extract insights from search patterns
        insights.extend(self._extract_search_insights(state))

        # Extract insights from agent interactions
        insights.extend(self._extract_interaction_insights(state))

        return insights

    def _extract_search_insights(self, state: TravelPlanningState) -> list[str]:
        """Extract insights from search behavior.

        Args:
            state: Current conversation state

        Returns:
            List of search-related insights
        """
        insights = []

        # Flight search patterns
        if state.get("flight_searches"):
            flight_searches = state["flight_searches"]

            # Analyze route preferences
            routes = set()
            for search in flight_searches:
                params = search.get("parameters", {})
                origin = params.get("origin")
                destination = params.get("destination")
                if origin and destination:
                    routes.add(f"{origin}-{destination}")

            for route in routes:
                insights.append(f"Searched flight route: {route}")

            # Analyze search frequency
            if len(flight_searches) > 1:
                insights.append(f"Performed {len(flight_searches)} flight searches")

        # Accommodation search patterns
        if state.get("accommodation_searches"):
            accommodation_searches = state["accommodation_searches"]

            # Analyze location preferences
            locations = set()
            for search in accommodation_searches:
                params = search.get("parameters", {})
                location = params.get("location")
                if location:
                    locations.add(location)

            for location in locations:
                insights.append(f"Searched accommodation in: {location}")

        # Activity search patterns
        if state.get("activity_searches"):
            activity_searches = state["activity_searches"]

            # Analyze activity preferences
            activity_types = set()
            for search in activity_searches:
                params = search.get("parameters", {})
                activity_type = params.get("type")
                if activity_type:
                    activity_types.add(activity_type)

            for activity_type in activity_types:
                insights.append(f"Interested in activity type: {activity_type}")

        return insights

    def _extract_interaction_insights(self, state: TravelPlanningState) -> list[str]:
        """Extract insights from agent interaction patterns.

        Args:
            state: Current conversation state

        Returns:
            List of interaction-related insights
        """
        insights = []

        # Analyze agent usage patterns
        agent_history = state.get("agent_history", [])
        if agent_history:
            # Count agent usage
            agent_counts = {}
            for agent in agent_history:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1

            # Identify primary interests
            for agent, count in agent_counts.items():
                if count > 1:
                    insights.append(f"Frequently used {agent} ({count} times)")

        # Analyze conversation length and complexity
        message_count = len(state.get("messages", []))
        if message_count > 5:
            insights.append(
                f"Engaged in detailed conversation ({message_count} messages)"
            )

        # Analyze error patterns
        error_info = state.get("error_info", {})
        error_count = error_info.get("error_count", 0)
        if error_count > 0:
            insights.append(f"Encountered {error_count} errors during session")

        return insights

    async def _update_knowledge_graph(
        self, state: TravelPlanningState, insights: list[str]
    ) -> None:
        """Update knowledge graph with insights.

        Args:
            state: Current conversation state
            insights: List of insights to store
        """
        if not self.memory_tool or not insights:
            return

        try:
            # Prepare memory update data
            entity_name = f"user:{state['user_id']}"

            # Add observations to the user entity
            memory_data = {"entity_name": entity_name, "observations": insights}

            # Execute memory update
            await self.memory_tool._arun(**memory_data)
            logger.info("Updated knowledge graph with %s insights", len(insights))

        except Exception:
            logger.exception("Failed to update knowledge graph")

    async def _update_session_data(self, state: TravelPlanningState) -> None:
        """Update session data in Supabase.

        Args:
            state: Current conversation state
        """
        try:
            # Log session metrics
            session_id = state["session_id"]
            # TODO: Implement Supabase session update
            # user_id = state["user_id"]
            # message_count = len(state.get("messages", []))
            # error_count = state.get("error_count", 0)

            # session_summary = {
            #     "session_id": session_id,
            #     "user_id": user_id,
            #     "message_count": message_count,
            #     "error_count": error_count,
            # }
            # await supabase_client.update_session(session_summary)

            logger.info("Updated session data for %s", session_id)

        except Exception:
            logger.exception("Failed to update session data")
