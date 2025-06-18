"""
Test utilities for orchestration tests.

Provides common mocking utilities for LangChain and OpenAI API calls.
"""

from typing import Any, Optional
from unittest.mock import AsyncMock, Mock

class MockLLMResponse:
    """Mock response for LLM calls."""

    def __init__(self, content: str):
        self.content = content

class MockChatOpenAI:
    """Mock ChatOpenAI that doesn't make real API calls."""

    def __init__(self, *args, **kwargs):
        """Initialize mock without making API calls."""
        self.model = kwargs.get("model", "gpt-3.5-turbo")
        self.temperature = kwargs.get("temperature", 0.7)
        # Store responses for different scenarios
        self._responses = {}
        self._default_response = "I understand your request."

    def set_response(self, key: str, response: str):
        """Set a specific response for a key."""
        self._responses[key] = response

    def set_default_response(self, response: str):
        """Set the default response."""
        self._default_response = response

    async def ainvoke(
        self, messages: list[dict[str, str]], **kwargs
    ) -> MockLLMResponse:
        """Mock async invoke."""
        # Extract content from messages
        if messages:
            last_message = messages[-1]
            content = (
                last_message.get("content", "")
                if isinstance(last_message, dict)
                else str(last_message)
            )

            # Return specific responses based on content
            if "extract" in content.lower() and "parameters" in content.lower():
                # Parameter extraction responses
                if "accommodation" in content.lower():
                    return MockLLMResponse(
                        '{"location": "Paris", "check_in": "2024-06-15", '
                        '"check_out": "2024-06-20"}'
                    )
                elif "flight" in content.lower():
                    return MockLLMResponse(
                        '{"origin": "NYC", "destination": "LAX", '
                        '"departure_date": "2024-06-15"}'
                    )
                elif "budget" in content.lower():
                    # Check if it's asking about a specific budget amount
                    if "$2000" in content:
                        return MockLLMResponse(
                            '{"operation": "optimize", "total_budget": 2000, '
                            '"trip_length": 7}'
                        )
                    else:
                        return MockLLMResponse(
                            '{"operation": "optimize", "total_budget": 2000, '
                            '"trip_length": 7}'
                        )
                elif "destination" in content.lower():
                    return MockLLMResponse(
                        '{"destination": "Tokyo", "research_type": "overview"}'
                    )
                elif "itinerary" in content.lower():
                    return MockLLMResponse(
                        '{"operation": "create", "destination": "Rome", "duration": 5}'
                    )
                else:
                    return MockLLMResponse("null")

            # Intent classification for router
            if "classify" in content.lower() and "intent" in content.lower():
                if "flight" in content.lower():
                    return MockLLMResponse(
                        '{"agent": "flight_agent", "confidence": 0.9, '
                        '"reasoning": "User mentioned flights"}'
                    )
                elif "hotel" in content.lower() or "accommodation" in content.lower():
                    return MockLLMResponse(
                        '{"agent": "accommodation_agent", "confidence": 0.9, '
                        '"reasoning": "User mentioned hotels"}'
                    )
                elif "budget" in content.lower():
                    return MockLLMResponse(
                        '{"agent": "budget_agent", "confidence": 0.9, '
                        '"reasoning": "User mentioned budget"}'
                    )
                else:
                    return MockLLMResponse(
                        '{"agent": "general_agent", "confidence": 0.3, '
                        '"reasoning": "Unclear intent"}'
                    )

            # Response generation for agents
            if (
                "provide a helpful response" in content.lower()
                or "general" in content.lower()
            ):
                if "accommodation" in content.lower():
                    return MockLLMResponse(
                        "I'd be happy to help you find accommodations! "
                        "Could you please tell me your destination, "
                        "check-in and check-out dates?"
                    )
                elif "flight" in content.lower():
                    return MockLLMResponse(
                        "I'd be happy to help you find flights! "
                        "Could you please tell me your departure city, "
                        "destination, and travel dates?"
                    )
                elif "budget" in content.lower():
                    return MockLLMResponse(
                        "I'd be happy to help optimize your travel budget! "
                        "Could you please share your total budget and trip details?"
                    )

            # Response generation
            if "generate" in content.lower() and "response" in content.lower():
                if "accommodation" in content.lower():
                    return MockLLMResponse("I found great hotels in Paris for you!")
                elif "flight" in content.lower():
                    return MockLLMResponse(
                        "I found several flight options from NYC to LAX."
                    )
                elif "budget" in content.lower():
                    return MockLLMResponse(
                        "I've optimized your $2000 budget for a 7-day trip."
                    )
                elif "destination" in content.lower():
                    return MockLLMResponse(
                        "Tokyo is an amazing destination with rich culture!"
                    )
                elif "itinerary" in content.lower():
                    return MockLLMResponse("I've created a 5-day itinerary for Rome.")

            # Check for custom responses
            for key, response in self._responses.items():
                if key in content:
                    return MockLLMResponse(response)

        # Default response
        return MockLLMResponse(self._default_response)

    def invoke(self, messages: list[dict[str, str]], **kwargs) -> MockLLMResponse:
        """Mock sync invoke."""
        import asyncio

        return asyncio.run(self.ainvoke(messages, **kwargs))

def create_mock_llm(default_response: str = "Test response") -> MockChatOpenAI:
    """Create a mock LLM instance."""
    mock_llm = MockChatOpenAI()
    mock_llm.set_default_response(default_response)
    return mock_llm

def patch_openai_in_module(module_path: str):
    """
    Create a patch decorator for mocking ChatOpenAI in a specific module.

    Args:
        module_path: The module path to patch
            (e.g., 'tripsage.orchestration.nodes.accommodation_agent')

    Returns:
        Patch decorator
    """
    from unittest.mock import patch

    return patch(f"{module_path}.ChatOpenAI", MockChatOpenAI)

def create_mock_service_registry(services: dict[str, Any] | None = None) -> Mock:
    """
    Create a mock service registry with common services.

    Args:
        services: Optional dictionary of service name to mock service

    Returns:
        Mock service registry
    """
    registry = Mock()

    # Default services
    default_services = {
        "flight_service": Mock(),
        "accommodation_service": Mock(),
        "memory_service": Mock(),
        "user_service": Mock(),
        "chat_service": Mock(),
        "destination_service": Mock(),
        "itinerary_service": Mock(),
        "budget_service": Mock(),
    }

    # Override with provided services
    if services:
        default_services.update(services)

    # Set up service methods
    for service_name, service_mock in default_services.items():
        setattr(registry, service_name, service_mock)

    # Mock get_service and get_optional_service methods
    def get_service(name: str):
        return default_services.get(name)

    def get_optional_service(name: str):
        return default_services.get(name)

    registry.get_service = Mock(side_effect=get_service)
    registry.get_optional_service = Mock(side_effect=get_optional_service)

    return registry

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
            "I've optimized your $2000 budget: Flights $600, "
            "Accommodation $700, Food $400, Activities $300."
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
            "I've created a 5-day itinerary for Rome. Day 1: Visit "
            "Colosseum and Roman Forum."
        ),
    },
}
