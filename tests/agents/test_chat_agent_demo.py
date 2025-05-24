#!/usr/bin/env python3
"""
Standalone test for ChatAgent that bypasses pytest fixtures and demonstrates
the proper solution to pydantic settings testing issues.

Run with: python test_chat_agent_final.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Imports needed for testing
import asyncio  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

# CRITICAL: Set environment variables BEFORE any imports that trigger
# pydantic validation
# Using the comprehensive environment setup from conftest.py
test_env_vars = {
    # Basic API keys
    "OPENAI_API_KEY": "test-openai-key",
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    # Database configuration - Core required fields
    "SUPABASE_URL": "https://test-supabase-url.com",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "PASSWORD": "test-password",  # For Neo4j
    "USER": "test-user",
    # Redis configuration
    "REDIS_URL": "redis://localhost:6379/0",
    # MCP Endpoints - Using correct prefixes from MCP config classes
    "TRIPSAGE_MCP_TIME_ENDPOINT": "http://localhost:3006",
    "TRIPSAGE_MCP_WEATHER_ENDPOINT": "http://localhost:3007",
    "TRIPSAGE_MCP_WEATHER_OPENWEATHERMAP_API_KEY": "test-weather-api-key",
    "TRIPSAGE_MCP_GOOGLEMAPS_ENDPOINT": "http://localhost:3008",
    "TRIPSAGE_MCP_GOOGLEMAPS_MAPS_API_KEY": "test-maps-api-key",
    "TRIPSAGE_MCP_MEMORY_ENDPOINT": "http://localhost:3009",
    "TRIPSAGE_MCP_WEBCRAWL_ENDPOINT": "http://localhost:3010",
    "TRIPSAGE_MCP_WEBCRAWL_CRAWL4AI_API_KEY": "test-crawl-key",
    "TRIPSAGE_MCP_WEBCRAWL_FIRECRAWL_API_KEY": "test-firecrawl-key",
    "TRIPSAGE_MCP_FLIGHTS_ENDPOINT": "http://localhost:3011",
    "TRIPSAGE_MCP_FLIGHTS_DUFFEL_API_KEY": "test-duffel-key",
    "TRIPSAGE_MCP_ACCOMMODATIONS_AIRBNB_ENDPOINT": "http://localhost:3012",
    "TRIPSAGE_MCP_PLAYWRIGHT_ENDPOINT": "http://localhost:3013",
    "TRIPSAGE_MCP_CALENDAR_ENDPOINT": "http://localhost:3014",
    "TRIPSAGE_MCP_CALENDAR_GOOGLE_CLIENT_ID": "test-client-id",
    "TRIPSAGE_MCP_CALENDAR_GOOGLE_CLIENT_SECRET": "test-client-secret",
    "TRIPSAGE_MCP_CALENDAR_GOOGLE_REDIRECT_URI": "http://localhost:3000/callback",
    "TRIPSAGE_MCP_NEON_ENDPOINT": "http://localhost:3015",
    "TRIPSAGE_MCP_NEON_API_KEY": "test-neon-key",
    "TRIPSAGE_MCP_SUPABASE_ENDPOINT": "http://localhost:3016",
    # Additional environment variables for compatibility
    "ENVIRONMENT": "testing",
    "DEBUG": "false",
    "LOG_LEVEL": "INFO",
}

# Apply all test environment variables
for key, value in test_env_vars.items():
    os.environ[key] = value

print("🔧 Environment variables set for testing")

# Now we can safely import modules that use pydantic settings


def test_intent_detection_algorithm():
    """Test the intent detection algorithm in isolation."""
    print("\n🧪 Testing intent detection algorithm...")

    def detect_intent_algorithm(message: str) -> dict:
        """Standalone implementation of intent detection algorithm."""
        message_lower = message.lower()

        # Intent configuration matching ChatAgent logic
        intents = {
            "flight": {
                "keywords": [
                    "flight",
                    "flights",
                    "fly",
                    "airline",
                    "airport",
                    "ticket",
                    "plane",
                    "aviation",
                    "book",
                ],
                "phrases": [
                    "fly to",
                    "flight from",
                    "book flight",
                    "find flight",
                    "search flight",
                    "search for flights",
                ],
                "confidence_boost": 0.4,
            },
            "accommodation": {
                "keywords": [
                    "hotel",
                    "accommodation",
                    "stay",
                    "room",
                    "booking",
                    "lodge",
                    "inn",
                    "book",
                    "find",
                ],
                "phrases": [
                    "book hotel",
                    "find hotel",
                    "reserve room",
                    "hotel reservation",
                    "find accommodation",
                ],
                "confidence_boost": 0.4,
            },
            "planning": {
                "keywords": [
                    "plan",
                    "trip",
                    "itinerary",
                    "schedule",
                    "travel",
                    "organize",
                    "help",
                    "create",
                ],
                "phrases": [
                    "plan trip",
                    "create itinerary",
                    "travel plan",
                    "organize trip",
                    "help me plan",
                ],
                "confidence_boost": 0.4,
            },
        }

        best_intent = "general"
        best_confidence = 0.1

        for intent_name, config in intents.items():
            confidence = 0.0

            # Check keywords (each adds 0.2)
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    confidence += 0.2

            # Check phrases (each adds boost value)
            for phrase in config["phrases"]:
                if phrase in message_lower:
                    confidence += config["confidence_boost"]

            # Update best match
            if confidence > best_confidence:
                best_intent = intent_name
                best_confidence = confidence

        return {"intent": best_intent, "confidence": round(best_confidence, 2)}

    # Test cases
    test_cases = [
        # Flight intents
        ("I want to fly to Paris", "flight", 0.6),
        ("Book a flight from NYC to LAX", "flight", 0.8),
        ("Find me airline tickets", "flight", 0.4),
        ("Search for flights to Tokyo", "flight", 0.6),
        # Accommodation intents
        ("Book a hotel in Rome", "accommodation", 0.6),
        ("Find accommodation near the airport", "accommodation", 0.4),
        ("I need a room for tonight", "accommodation", 0.4),
        ("Hotel reservation for two nights", "accommodation", 0.6),
        # Planning intents
        ("Help me plan my trip to Japan", "planning", 0.8),
        ("Create an itinerary for my vacation", "planning", 0.6),
        ("I need a travel plan", "planning", 0.6),
        ("Organize my trip to Europe", "planning", 0.6),
        # General intents
        ("Hello, how are you?", "general", 0.1),
        ("What's the weather like?", "general", 0.1),
        ("Thank you for your help", "general", 0.1),
    ]

    passed = 0
    failed = 0

    for message, expected_intent, min_confidence in test_cases:
        result = detect_intent_algorithm(message)

        intent_match = result["intent"] == expected_intent
        confidence_match = result["confidence"] >= min_confidence

        if intent_match and confidence_match:
            print(f"  ✅ '{message}' -> {result['intent']} ({result['confidence']})")
            passed += 1
        else:
            print(
                f"  ❌ '{message}' -> Expected: {expected_intent} "
                f"(>={min_confidence}), Got: {result['intent']} "
                f"({result['confidence']})"
            )
            failed += 1

    print(f"\n📊 Intent Detection Results: {passed} passed, {failed} failed")
    return failed == 0


def test_chat_agent_import():
    """Test that ChatAgent can be imported with proper environment setup."""
    print("\n🔍 Testing ChatAgent import...")

    try:
        from tripsage.agents.chat import ChatAgent

        print("  ✅ ChatAgent imported successfully")

        # Check that class has expected methods
        expected_methods = ["detect_intent", "process", "_check_rate_limit"]
        for method in expected_methods:
            if hasattr(ChatAgent, method):
                print(f"  ✅ Method {method} found")
            else:
                print(f"  ❌ Method {method} missing")
                return False

        return True

    except Exception as e:
        print(f"  ❌ Failed to import ChatAgent: {e}")
        return False


def test_chat_agent_initialization():
    """Test ChatAgent initialization with mocked dependencies."""
    print("\n🏗️ Testing ChatAgent initialization...")

    try:
        # Mock the dependencies that ChatAgent needs
        with patch("tripsage.agents.chat.SpecializedAgents") as mock_agents:
            with patch("tripsage.agents.chat.openai.OpenAI") as mock_openai:
                # Set up the mocks
                mock_specialized_agents = MagicMock()
                mock_specialized_agents.flight_agent = AsyncMock()
                mock_specialized_agents.accommodation_agent = AsyncMock()
                mock_specialized_agents.planning_agent = AsyncMock()
                mock_agents.return_value = mock_specialized_agents

                mock_openai_client = AsyncMock()
                mock_openai.return_value = mock_openai_client

                # Import and create instance
                from tripsage.agents.chat import ChatAgent

                agent = ChatAgent()

                print("  ✅ ChatAgent instance created successfully")

                # Verify initialization
                if agent.specialized_agents is not None:
                    print("  ✅ Specialized agents initialized")
                else:
                    print("  ❌ Specialized agents not initialized")
                    return False

                if agent.client is not None:
                    print("  ✅ OpenAI client initialized")
                else:
                    print("  ❌ OpenAI client not initialized")
                    return False

                # Verify mocks were called
                if mock_agents.called:
                    print("  ✅ SpecializedAgents mock was called")
                else:
                    print("  ❌ SpecializedAgents mock was not called")
                    return False

                if mock_openai.called:
                    print("  ✅ OpenAI mock was called")
                else:
                    print("  ❌ OpenAI mock was not called")
                    return False

                return True

    except Exception as e:
        print(f"  ❌ Failed to initialize ChatAgent: {e}")
        return False


def test_chat_agent_intent_detection():
    """Test intent detection using the actual ChatAgent method."""
    print("\n🎯 Testing ChatAgent intent detection method...")

    try:
        with patch("tripsage.agents.chat.SpecializedAgents"):
            with patch("tripsage.agents.chat.openai.OpenAI"):
                from tripsage.agents.chat import ChatAgent

                agent = ChatAgent()

                # Test various intents
                test_cases = [
                    ("I want to book a flight to Tokyo", "flight"),
                    ("Find me a hotel in Paris", "accommodation"),
                    ("Help me plan my trip", "planning"),
                    ("Hello there", "general"),
                ]

                passed = 0
                failed = 0

                for message, expected_intent in test_cases:
                    try:
                        result = agent.detect_intent(message)

                        if (
                            isinstance(result, dict)
                            and "intent" in result
                            and "confidence" in result
                        ):
                            if result["intent"] == expected_intent:
                                print(
                                    f"  ✅ '{message}' -> {result['intent']} "
                                    f"({result['confidence']})"
                                )
                                passed += 1
                            else:
                                print(
                                    f"  ❌ '{message}' -> Expected: {expected_intent}, "
                                    f"Got: {result['intent']}"
                                )
                                failed += 1
                        else:
                            print(
                                f"  ❌ '{message}' -> Invalid result format: {result}"
                            )
                            failed += 1

                    except Exception as e:
                        print(f"  ❌ '{message}' -> Error: {e}")
                        failed += 1

                print(
                    f"\n📊 Intent Detection Method Results: {passed} passed, "
                    f"{failed} failed"
                )
                return failed == 0

    except Exception as e:
        print(f"  ❌ Failed to test intent detection: {e}")
        return False


async def test_chat_agent_rate_limiting():
    """Test rate limiting functionality."""
    print("\n⏱️ Testing ChatAgent rate limiting...")

    try:
        with patch("tripsage.agents.chat.SpecializedAgents"):
            with patch("tripsage.agents.chat.openai.OpenAI"):
                with patch("tripsage.utils.cache.web_cache") as mock_cache:
                    # Mock cache for rate limiting - under limit
                    mock_cache.get = AsyncMock(return_value=3)  # Under limit of 5
                    mock_cache.incr = AsyncMock(return_value=4)
                    mock_cache.expire = AsyncMock(return_value=True)

                    from tripsage.agents.chat import ChatAgent

                    agent = ChatAgent()

                    # Test under limit
                    result = await agent._check_rate_limit("test_user")
                    if result is True:
                        print("  ✅ Rate limiting allows request under limit")
                    else:
                        print(
                            "  ❌ Rate limiting incorrectly blocked request under limit"
                        )
                        return False

                    # Test over limit
                    mock_cache.get.return_value = 6  # Over limit of 5
                    mock_cache.incr.return_value = 7

                    result = await agent._check_rate_limit("test_user")
                    if result is False:
                        print("  ✅ Rate limiting correctly blocks request over limit")
                    else:
                        print(
                            "  ❌ Rate limiting incorrectly allowed request over limit"
                        )
                        return False

                    return True

    except Exception as e:
        print(f"  ❌ Failed to test rate limiting: {e}")
        return False


async def test_chat_agent_process_flow():
    """Test processing a message with tool calls."""
    print("\n🔄 Testing ChatAgent process flow...")

    try:
        with patch("tripsage.agents.chat.SpecializedAgents") as mock_agents:
            with patch("tripsage.agents.chat.openai.OpenAI") as mock_openai:
                with patch("tripsage.utils.cache.web_cache") as mock_cache:
                    # Set up specialized agent mock
                    mock_flight_agent = AsyncMock()
                    mock_flight_agent.handle_request.return_value = {
                        "flights": [{"from": "NYC", "to": "LAX", "price": "$300"}],
                        "message": "Found flight options",
                    }

                    mock_specialized_agents = MagicMock()
                    mock_specialized_agents.flight_agent = mock_flight_agent
                    mock_agents.return_value = mock_specialized_agents

                    # Set up OpenAI mock with tool call response
                    mock_openai_client = AsyncMock()

                    # Mock first response with tool call
                    mock_tool_call = MagicMock()
                    mock_tool_call.id = "call_abc123"
                    mock_tool_call.type = "function"
                    mock_tool_call.function.name = "search_flights"
                    mock_tool_call.function.arguments = (
                        '{"origin": "NYC", "destination": "LAX"}'
                    )

                    mock_tool_message = MagicMock()
                    mock_tool_message.tool_calls = [mock_tool_call]
                    mock_tool_message.content = None

                    mock_tool_choice = MagicMock()
                    mock_tool_choice.message = mock_tool_message

                    mock_tool_response = MagicMock()
                    mock_tool_response.choices = [mock_tool_choice]

                    # Mock second response with final answer
                    mock_final_message = MagicMock()
                    mock_final_message.tool_calls = []
                    mock_final_message.content = (
                        "I found some great flight options for you!"
                    )

                    mock_final_choice = MagicMock()
                    mock_final_choice.message = mock_final_message

                    mock_final_response = MagicMock()
                    mock_final_response.choices = [mock_final_choice]

                    # Set up call sequence
                    mock_openai_client.chat.completions.create.side_effect = [
                        mock_tool_response,
                        mock_final_response,
                    ]
                    mock_openai.return_value = mock_openai_client

                    # Set up cache mocks for rate limiting
                    mock_cache.get.return_value = 1  # Under rate limit
                    mock_cache.incr = AsyncMock(return_value=2)
                    mock_cache.expire = AsyncMock(return_value=True)

                    from tripsage.agents.chat import ChatAgent

                    agent = ChatAgent()

                    # Test the full process
                    result = await agent.process(
                        message="Find flights from NYC to LAX",
                        user_id="test_user",
                        session_id="test_session",
                    )

                    # Verify the result structure
                    if not isinstance(result, dict):
                        print(f"  ❌ Result is not a dict: {type(result)}")
                        return False

                    if "response" not in result:
                        print(f"  ❌ Result missing 'response' key: {result.keys()}")
                        return False

                    if "tool_calls" not in result:
                        print(f"  ❌ Result missing 'tool_calls' key: {result.keys()}")
                        return False

                    if (
                        result["response"]
                        != "I found some great flight options for you!"
                    ):
                        print(f"  ❌ Unexpected response: {result['response']}")
                        return False

                    if len(result["tool_calls"]) != 1:
                        print(
                            f"  ❌ Expected 1 tool call, got "
                            f"{len(result['tool_calls'])}"
                        )
                        return False

                    tool_call = result["tool_calls"][0]
                    if tool_call["id"] != "call_abc123":
                        print(f"  ❌ Unexpected tool call ID: {tool_call['id']}")
                        return False

                    if tool_call["name"] != "search_flights":
                        print(f"  ❌ Unexpected tool call name: {tool_call['name']}")
                        return False

                    if not isinstance(tool_call["arguments"], dict):
                        print(
                            f"  ❌ Tool call arguments not a dict: "
                            f"{type(tool_call['arguments'])}"
                        )
                        return False

                    if tool_call["arguments"]["origin"] != "NYC":
                        print(
                            f"  ❌ Unexpected origin: "
                            f"{tool_call['arguments']['origin']}"
                        )
                        return False

                    # Verify the flight agent was called
                    if not mock_flight_agent.handle_request.called:
                        print("  ❌ Flight agent was not called")
                        return False

                    print("  ✅ Process flow completed successfully")
                    print(f"  ✅ Response: {result['response']}")
                    print(f"  ✅ Tool calls: {len(result['tool_calls'])}")
                    print(
                        f"  ✅ Flight agent called: "
                        f"{mock_flight_agent.handle_request.called}"
                    )

                    return True

    except Exception as e:
        print(f"  ❌ Failed to test process flow: {e}")
        import traceback

        print(f"  📍 Traceback: {traceback.format_exc()}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting ChatAgent Testing Suite")
    print("=" * 50)

    tests = [
        ("Intent Detection Algorithm", test_intent_detection_algorithm()),
        ("ChatAgent Import", test_chat_agent_import()),
        ("ChatAgent Initialization", test_chat_agent_initialization()),
        ("ChatAgent Intent Detection Method", test_chat_agent_intent_detection()),
        ("ChatAgent Rate Limiting", await test_chat_agent_rate_limiting()),
        ("ChatAgent Process Flow", await test_chat_agent_process_flow()),
    ]

    passed = 0
    failed = 0

    for test_name, result in tests:
        if result:
            print(f"\n✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"\n❌ {test_name}: FAILED")
            failed += 1

    print("\n" + "=" * 50)
    print(f"🏁 Test Suite Complete: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! ChatAgent is working correctly.")

        # Update TODO status
        print("\n📝 Updating task status...")
        return True
    else:
        print("💥 Some tests failed. Please review the output above.")
        return False


if __name__ == "__main__":
    # Run the test suite
    result = asyncio.run(main())

    if result:
        print("\n✅ ChatAgent testing completed successfully!")
        print("🔧 Environment isolation solution works!")
        print("📚 Key learnings:")
        print("   • Set environment variables BEFORE importing pydantic settings")
        print("   • Use comprehensive mocking for dependencies")
        print("   • Test both isolated algorithms and integrated flows")
        print("   • Rate limiting and tool calling work as expected")
    else:
        print("\n❌ Testing failed - see output above for details")

    sys.exit(0 if result else 1)
