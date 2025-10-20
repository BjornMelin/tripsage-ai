"""Simplified LangGraph orchestrator for TripSage AI.

This module implements a simple, maintainable graph-based orchestration system
using modern LangGraph patterns with create_react_agent for simplicity.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from tripsage.orchestration.tools import get_all_tools
from tripsage_core.config import get_settings
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class SimpleTripSageOrchestrator:
    """Simplified LangGraph orchestrator using modern create_react_agent pattern.

    This replaces the complex multi-agent graph with a single, powerful agent
    that has access to all travel tools and can handle all travel planning tasks.
    """

    def __init__(self, service_registry=None):
        """Initialize the simple orchestrator."""
        self.service_registry = service_registry

        # Initialize LLM
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.model_temperature,
            api_key=settings.openai_api_key.get_secret_value(),
        )

        # Get all tools
        self.tools = get_all_tools()

        # Create the agent using modern LangGraph pattern
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=MemorySaver(),
            system_prompt=self._get_system_prompt(),
        )

        logger.info(
            f"Initialized SimpleTripSageOrchestrator with {len(self.tools)} tools"
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the travel planning agent."""
        return """You are TripSage, an expert AI travel planning assistant. 
You help users plan comprehensive trips by:

1. **Flight Search**: Use search_flights to find and compare flight options
2. **Accommodation Search**: Use search_accommodations to find hotels, 
   Airbnbs, and other lodging
3. **Location Services**: Use geocode_location to get coordinates and location details
4. **Weather Information**: Use get_weather to provide weather forecasts 
   for destinations
5. **Research**: Use web_search to research destinations, activities, and travel tips
6. **Memory Management**: Use add_memory and search_memories to remember 
   user preferences and past conversations

**Guidelines:**
- Always be helpful, accurate, and comprehensive in your travel planning
- Ask clarifying questions when you need more information
- Provide multiple options when possible
- Consider user preferences, budget, and travel dates
- Use tools efficiently to gather the information you need
- Save important user preferences to memory for future reference
- Be proactive in suggesting improvements and alternatives

**Example Workflow:**
1. When a user asks about travel, extract key details (origin, destination, 
   dates, budget)
2. Use appropriate tools to search for flights and accommodations
3. Research the destination for activities and tips
4. Check weather for the travel dates
5. Save user preferences to memory
6. Provide a comprehensive response with options and recommendations

Start by greeting the user and asking how you can help with their travel planning!"""

    async def process_conversation(
        self, messages: list[dict[str, Any]], config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Process a conversation using the simple agent.

        Args:
            messages: List of conversation messages
            config: Optional configuration (e.g., thread_id for persistence)

        Returns:
            Updated conversation state with agent response
        """
        try:
            # Convert messages to LangChain format if needed
            langchain_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "human")
                    content = msg.get("content", "")

                    if role == "user" or role == "human":
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == "assistant" or role == "ai":
                        langchain_messages.append(AIMessage(content=content))
                    elif role == "system":
                        langchain_messages.append(SystemMessage(content=content))
                else:
                    langchain_messages.append(msg)

            # Use default config if none provided
            if config is None:
                config = {"configurable": {"thread_id": "default"}}

            # Invoke the agent
            result = await self.agent.ainvoke(
                {"messages": langchain_messages}, config=config
            )

            # Convert back to dictionary format
            response_messages = []
            for msg in result["messages"]:
                response_messages.append(
                    {
                        "role": self._get_role_from_message(msg),
                        "content": msg.content,
                        "timestamp": msg.additional_kwargs.get("timestamp", None),
                    }
                )

            return {"messages": response_messages, "success": True}

        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            return {
                "messages": messages
                + [
                    {
                        "role": "assistant",
                        "content": f"I apologize, but I encountered an error while "
                        f"processing your request: {e!s}. Please try again.",
                    }
                ],
                "success": False,
                "error": str(e),
            }

    def _get_role_from_message(self, message) -> str:
        """Convert LangChain message type to role string."""
        if isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        elif isinstance(message, SystemMessage):
            return "system"
        else:
            return "unknown"

    async def stream_conversation(
        self, messages: list[dict[str, Any]], config: dict[str, Any] | None = None
    ):
        """Stream a conversation response from the agent.

        Args:
            messages: List of conversation messages
            config: Optional configuration

        Yields:
            Streaming chunks of the agent response
        """
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "human")
                    content = msg.get("content", "")

                    if role == "user" or role == "human":
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == "assistant" or role == "ai":
                        langchain_messages.append(AIMessage(content=content))

            if config is None:
                config = {"configurable": {"thread_id": "default"}}

            # Stream the agent response
            async for chunk in self.agent.astream(
                {"messages": langchain_messages}, config=config
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error streaming conversation: {e}")
            yield {
                "error": str(e),
                "messages": [{"role": "assistant", "content": f"Error: {e!s}"}],
            }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the orchestrator."""
        try:
            # Test basic agent functionality
            test_result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content="Health check")]},
                config={"configurable": {"thread_id": "health"}},
            )

            return {
                "status": "healthy",
                "agent_responsive": True,
                "tools_count": len(self.tools),
                "timestamp": test_result["messages"][-1].additional_kwargs.get(
                    "timestamp"
                ),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "agent_responsive": False, "error": str(e)}


# Global orchestrator instance
_global_orchestrator: SimpleTripSageOrchestrator | None = None


def get_orchestrator(service_registry=None) -> SimpleTripSageOrchestrator:
    """Get the global orchestrator instance."""
    global _global_orchestrator
    if _global_orchestrator is None or service_registry is not None:
        _global_orchestrator = SimpleTripSageOrchestrator(service_registry)
    return _global_orchestrator
