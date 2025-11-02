"""Test utilities for orchestration workflows.

Provides reusable mocks for LangChain and external API integrations while keeping
type information explicit so static analysers remain satisfied.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, Mock

from tripsage.app_state import AppServiceContainer


class MockLLMResponse:
    """Mock response for LLM calls."""

    def __init__(self, content: str) -> None:
        """Store mock content returned by the LLM."""
        self.content: str = content


class MockChatOpenAI:
    """Mock ChatOpenAI that doesn't make real API calls."""

    def __init__(self, *_: Any, **kwargs: Any) -> None:
        """Initialise mock without making API calls."""
        self.model: str = str(kwargs.get("model", "gpt-3.5-turbo"))
        self.temperature: float = float(kwargs.get("temperature", 0.7))
        # Store responses for different scenarios
        self._responses: dict[str, str] = {}
        self._default_response: str = "I understand your request."
        self._bound_tools: list[Any] = []

    def set_response(self, key: str, response: str):
        """Set a specific response for a key."""
        self._responses[key] = response

    def set_default_response(self, response: str):
        """Set the default response."""
        self._default_response = response

    async def ainvoke(
        self,
        messages: Sequence[Mapping[str, str] | str],
        **__: Any,
    ) -> MockLLMResponse:
        """Mock async invoke."""
        response_content: str = self._default_response

        # Extract content from messages
        if messages:
            last_message = messages[-1]
            content = (
                last_message.get("content", "")
                if isinstance(last_message, Mapping)
                else str(last_message)
            )

            # Return specific responses based on content
            if "extract" in content.lower() and "parameters" in content.lower():
                # Parameter extraction responses
                if "accommodation" in content.lower():
                    response_content = (
                        '{"location": "Paris", "check_in": "2024-06-15", '
                        '"check_out": "2024-06-20"}'
                    )
                elif "flight" in content.lower():
                    response_content = (
                        '{"origin": "NYC", "destination": "LAX", '
                        '"departure_date": "2024-06-15"}'
                    )
                elif "budget" in content.lower():
                    # Check if it's asking about a specific budget amount
                    response_content = (
                        '{"operation": "optimize", "total_budget": 2000, '
                        '"trip_length": 7}'
                    )
                elif "destination" in content.lower():
                    response_content = (
                        '{"destination": "Tokyo", "research_type": "overview"}'
                    )
                elif "itinerary" in content.lower():
                    response_content = (
                        '{"operation": "create", "destination": "Rome", "duration": 5}'
                    )
                else:
                    response_content = "null"

            # Intent classification for router
            elif "classify" in content.lower() and "intent" in content.lower():
                if "flight" in content.lower():
                    response_content = (
                        '{"agent": "flight_agent", "confidence": 0.9, '
                        '"reasoning": "User mentioned flights"}'
                    )
                elif "hotel" in content.lower() or "accommodation" in content.lower():
                    response_content = (
                        '{"agent": "accommodation_agent", "confidence": 0.9, '
                        '"reasoning": "User mentioned hotels"}'
                    )
                elif "budget" in content.lower():
                    response_content = (
                        '{"agent": "budget_agent", "confidence": 0.9, '
                        '"reasoning": "User mentioned budget"}'
                    )
                else:
                    response_content = (
                        '{"agent": "general_agent", "confidence": 0.3, '
                        '"reasoning": "Unclear intent"}'
                    )

            # Response generation for agents
            elif (
                "provide a helpful response" in content.lower()
                or "general" in content.lower()
            ):
                if "accommodation" in content.lower():
                    response_content = (
                        "I'd be happy to help you find accommodations! "
                        "Could you please tell me your destination, "
                        "check-in and check-out dates?"
                    )
                elif "flight" in content.lower():
                    response_content = (
                        "I'd be happy to help you find flights! "
                        "Could you please tell me your departure city, "
                        "destination, and travel dates?"
                    )
                elif "budget" in content.lower():
                    response_content = (
                        "I'd be happy to help optimize your travel budget! "
                        "Could you please share your total budget and trip details?"
                    )

            # Response generation
            elif "generate" in content.lower() and "response" in content.lower():
                if "accommodation" in content.lower():
                    response_content = "I found great hotels in Paris for you!"
                elif "flight" in content.lower():
                    response_content = "I found several flight options from NYC to LAX."
                elif "budget" in content.lower():
                    response_content = (
                        "I've optimized your $2000 budget for a 7-day trip."
                    )
                elif "destination" in content.lower():
                    response_content = (
                        "Tokyo is an amazing destination with rich culture!"
                    )
                elif "itinerary" in content.lower():
                    response_content = "I've created a 5-day itinerary for Rome."

            # Check for custom responses
            else:
                for key, response in self._responses.items():
                    if key in content:
                        response_content = response
                        break

        return MockLLMResponse(response_content)

    def invoke(
        self,
        messages: Sequence[Mapping[str, str] | str],
        **kwargs: Any,
    ) -> MockLLMResponse:
        """Mock sync invoke."""
        import asyncio

        coro = self.ainvoke(messages, **kwargs)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "MockChatOpenAI.invoke cannot run while an event loop is active; "
            "await ainvoke(...) instead."
        )

    def with_structured_output(self, schema: Any) -> MockChatOpenAI:
        """Return self to emulate LangChain structured output wrapper."""
        _unused_schema = schema
        del _unused_schema
        return self

    def bind_tools(self, tools: Sequence[Any] | None) -> MockChatOpenAI:
        """Return self to emulate tool binding."""
        self._bound_tools = list(tools or [])
        return self


def create_mock_llm(default_response: str = "Test response") -> MockChatOpenAI:
    """Create a mock LLM instance."""
    mock_llm = MockChatOpenAI()
    mock_llm.set_default_response(default_response)
    return mock_llm


def patch_openai_in_module(module_path: str) -> Callable[..., Any]:
    """Create a patch decorator for mocking ChatOpenAI in a specific module.

    Args:
        module_path: The module path to patch
            (e.g., 'tripsage.orchestration.nodes.accommodation_agent')

    Returns:
        Patch decorator
    """
    from unittest.mock import patch

    return patch(f"{module_path}.ChatOpenAI", MockChatOpenAI)


def create_mock_services(
    overrides: dict[str, Any] | None = None,
) -> AppServiceContainer:
    """Create an AppServiceContainer populated with mock services."""
    # Use unspecialised mocks to avoid importing heavy dependencies during
    # test collection
    flight_service = cast(Any, MagicMock())
    activity_service = cast(Any, MagicMock())
    unified_search_service = cast(Any, MagicMock())
    google_maps_service = cast(Any, MagicMock())
    weather_service = cast(Any, MagicMock())
    webcrawl_service = cast(Any, MagicMock())
    mcp_service = cast(Any, MagicMock())

    container = AppServiceContainer(
        accommodation_service=cast(Any, Mock()),
        # chat_service removed
        destination_service=cast(Any, Mock()),
        file_processing_service=cast(Any, Mock()),
        flight_service=flight_service,
        activity_service=activity_service,
        itinerary_service=cast(Any, Mock()),
        memory_service=cast(Any, Mock()),
        trip_service=cast(Any, Mock()),
        unified_search_service=unified_search_service,
        configuration_service=cast(Any, Mock()),
        calendar_service=cast(Any, Mock()),
        document_analyzer=cast(Any, Mock()),
        google_maps_service=google_maps_service,
        playwright_service=cast(Any, Mock()),
        time_service=cast(Any, Mock()),
        weather_service=weather_service,
        webcrawl_service=webcrawl_service,
        cache_service=cast(Any, Mock()),
        database_service=cast(Any, Mock()),
        checkpoint_service=cast(Any, Mock()),
        memory_bridge=cast(Any, Mock()),
        mcp_service=mcp_service,
    )

    assert container.google_maps_service is not None
    google_maps_mock = cast(Any, container.google_maps_service)
    google_maps_mock.connect = AsyncMock(return_value=None)
    google_maps_mock.geocode = AsyncMock(return_value=[])

    assert container.weather_service is not None
    weather_mock = cast(Any, container.weather_service)
    weather_mock.connect = AsyncMock(return_value=None)
    weather_mock.get_current_weather = AsyncMock(return_value={})

    assert container.webcrawl_service is not None
    webcrawl_mock = cast(Any, container.webcrawl_service)
    webcrawl_mock.connect = AsyncMock(return_value=None)
    webcrawl_mock.search_web = AsyncMock(return_value={"results": []})

    if overrides:
        for name, value in overrides.items():
            try:
                setattr(container, name, value)
            except AttributeError:
                object.__setattr__(container, name, value)

    return container


def create_mock_tool_registry():
    """Create a mock tool registry."""
    registry = Mock()

    # Mock tools
    mock_tool = Mock()
    mock_tool.execute = AsyncMock(return_value={"result": "success"})
    mock_tool._arun = AsyncMock(return_value={"result": "success"})

    registry.get_tools_for_agent = Mock(return_value=[mock_tool])
    registry.get_langchain_tools_for_agent = Mock(return_value=[])
    registry.get_tool = Mock(return_value=mock_tool)

    return registry


# Common test responses for different agents
AGENT_TEST_RESPONSES = {
    "flight_agent": {
        "parameter_extraction": (
            '{"origin": "NYC", "destination": "LAX", "departure_date": "2024-06-15"}'
        ),
        "search_result": {"flights": [{"id": "FL123", "price": 299.99}]},
        "response": "I found 1 flight from NYC to LAX for $299.99.",
    },
    "accommodation_agent": {
        "parameter_extraction": (
            '{"location": "Paris", "check_in": "2024-06-15", "check_out": "2024-06-20"}'
        ),
        "search_result": {
            "accommodations": [{"id": "H456", "name": "Hotel Paris", "price": 150.0}]
        },
        "response": "I found Hotel Paris in Paris for $150 per night.",
    },
    "budget_agent": {
        "parameter_extraction": (
            '{"operation": "optimize", "total_budget": 2000, "trip_length": 7}'
        ),
        "optimization_result": {
            "allocations": {
                "flights": 600,
                "accommodation": 700,
                "food": 400,
                "activities": 300,
            }
        },
        "response": (
            "I've optimized your $2000 budget: Flights $600, Accommodation $700, "
            "Food $400, Activities $300."
        ),
    },
    "destination_research_agent": {
        "parameter_extraction": (
            '{"destination": "Tokyo", "research_type": "overview"}'
        ),
        "research_result": {
            "overview": "Tokyo is Japan's capital...",
            "attractions": ["Senso-ji Temple", "Tokyo Tower"],
        },
        "response": (
            "Tokyo is an amazing destination! Top attractions include "
            "Senso-ji Temple and Tokyo Tower."
        ),
    },
    "itinerary_agent": {
        "parameter_extraction": (
            '{"operation": "create", "destination": "Rome", "duration": 5}'
        ),
        "itinerary_result": {
            "daily_schedule": [{"day": 1, "activities": ["Colosseum", "Roman Forum"]}]
        },
        "response": (
            "I've created a 5-day itinerary for Rome. Day 1: Visit Colosseum "
            "and Roman Forum."
        ),
    },
}
