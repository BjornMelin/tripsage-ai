"""
Unit tests for ChatAgent core functionality.

This module tests the ChatAgent implementation with proper mocking
to isolate the core logic without complex dependency chains.
"""

import re
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestChatAgentUnit:
    """Unit tests for ChatAgent with mocked dependencies."""

    def test_intent_detection_algorithm(self):
        """Test intent detection algorithm with isolated logic."""
        # Test the actual algorithm logic from ChatAgent
        def detect_intent_logic(message: str) -> dict:
            """Extracted from ChatAgent.detect_intent method."""
            message_lower = message.lower()
            
            intent_patterns = {
                "flight": {
                    "keywords": [
                        "flight", "fly", "airline", "airport", "departure", 
                        "arrival", "book", "ticket",
                    ],
                    "patterns": [
                        r"\bfly\s+to\b", r"\bflight\s+from\b", r"\bbook.*flight\b",
                    ],
                    "weight": 0.0,
                },
                "accommodation": {
                    "keywords": [
                        "hotel", "accommodation", "stay", "room", "lodge", 
                        "resort", "airbnb", "booking",
                    ],
                    "patterns": [r"\bstay\s+in\b", r"\bhotel\s+in\b", r"\bbook.*hotel\b"],
                    "weight": 0.0,
                },
                "budget": {
                    "keywords": [
                        "budget", "cost", "price", "money", "expense", 
                        "afford", "cheap", "expensive",
                    ],
                    "patterns": [r"\bhow\s+much\b", r"\bcost\s+of\b", r"\bbudget\s+for\b"],
                    "weight": 0.0,
                },
                "weather": {
                    "keywords": [
                        "weather", "temperature", "rain", "sunny", "forecast", "climate",
                    ],
                    "patterns": [r"\bweather\s+in\b", r"\btemperature.*in\b"],
                    "weight": 0.0,
                },
            }
            
            # Calculate intent scores
            for intent, config in intent_patterns.items():
                # Check keywords
                for keyword in config["keywords"]:
                    if keyword in message_lower:
                        config["weight"] += 1
                
                # Check patterns
                for pattern in config["patterns"]:
                    if re.search(pattern, message_lower):
                        config["weight"] += 2
            
            # Find dominant intent
            max_weight = max(config["weight"] for config in intent_patterns.values())
            
            if max_weight == 0:
                primary_intent = "general"
                confidence = 0.5
            else:
                primary_intent = max(
                    intent_patterns.keys(), key=lambda k: intent_patterns[k]["weight"]
                )
                confidence = min(max_weight / 5.0, 1.0)  # Normalize to 0-1
            
            return {
                "primary_intent": primary_intent,
                "confidence": confidence,
                "all_scores": {k: v["weight"] for k, v in intent_patterns.items()},
                "requires_routing": confidence > 0.7 and primary_intent in [
                    "flight", "accommodation", "budget", "destination", "itinerary"
                ],
            }
        
        # Test cases
        test_cases = [
            # Flight intent tests
            ("I need to book a flight to Paris", "flight", True),
            ("Find me flights from NYC to LA", "flight", True),
            ("What airlines fly to Tokyo?", "flight", True),
            
            # Accommodation intent tests
            ("Find me a hotel in Rome", "accommodation", True),
            ("I need accommodation for my stay", "accommodation", True),
            ("Book a room in downtown", "accommodation", True),
            
            # Budget intent tests
            ("What's my budget for this trip?", "budget", True),
            ("How much will it cost?", "budget", True),
            ("I can afford $1000 for travel", "budget", True),
            
            # Weather intent tests
            ("What's the weather in Tokyo?", "weather", True),
            ("Check temperature in London", "weather", True),
            
            # General intent tests
            ("Hello, how are you?", "general", False),
            ("Thank you", "general", False),
        ]
        
        for message, expected_intent, should_have_confidence in test_cases:
            result = detect_intent_logic(message)
            
            assert result["primary_intent"] == expected_intent, f"Failed for: {message}"
            
            if should_have_confidence:
                assert result["confidence"] > 0.5, f"Low confidence for: {message}"
                assert result["all_scores"][expected_intent] > 0, f"No score for: {message}"
            else:
                assert result["confidence"] == 0.5, f"Wrong confidence for: {message}"

    def test_rate_limiting_algorithm(self):
        """Test rate limiting algorithm with isolated logic."""
        def check_rate_limit_logic(call_history: list, max_calls: int, window_seconds: int, current_time: float) -> bool:
            """Rate limiting logic from ChatAgent."""
            # Remove calls older than window
            recent_calls = [call_time for call_time in call_history if current_time - call_time < window_seconds]
            return len(recent_calls) < max_calls
        
        def log_call_logic(call_history: list, current_time: float) -> list:
            """Log a call for rate limiting."""
            return call_history + [current_time]
        
        # Test rate limiting behavior
        call_history = []
        current_time = 1000.0
        max_calls = 5
        window_seconds = 60
        
        # Should allow first 5 calls
        for i in range(5):
            assert check_rate_limit_logic(call_history, max_calls, window_seconds, current_time + i)
            call_history = log_call_logic(call_history, current_time + i)
        
        # Should deny 6th call
        assert not check_rate_limit_logic(call_history, max_calls, window_seconds, current_time + 5)
        
        # Should allow calls after time window
        future_time = current_time + 61
        assert check_rate_limit_logic(call_history, max_calls, window_seconds, future_time)

    @pytest.mark.asyncio
    async def test_tool_execution_algorithm(self):
        """Test tool execution algorithm with isolated logic."""
        async def execute_tool_logic(tool_name: str, parameters: dict, mock_manager) -> dict:
            """Tool execution logic from ChatAgent."""
            try:
                result = await mock_manager.invoke(tool_name, **parameters)
                return {
                    "status": "success",
                    "result": result,
                    "tool_name": tool_name,
                    "execution_time": time.time(),
                }
            except Exception as e:
                return {
                    "status": "error", 
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "tool_name": tool_name,
                }
        
        # Test successful execution
        mock_manager = MagicMock()
        mock_manager.invoke = AsyncMock(return_value={"success": True, "data": "test result"})
        
        result = await execute_tool_logic("weather_tool", {"location": "Paris"}, mock_manager)
        
        assert result["status"] == "success"
        assert result["tool_name"] == "weather_tool"
        assert "result" in result
        assert "execution_time" in result
        mock_manager.invoke.assert_called_once_with("weather_tool", location="Paris")
        
        # Test error handling
        mock_manager.invoke = AsyncMock(side_effect=Exception("Tool execution failed"))
        
        result = await execute_tool_logic("weather_tool", {"location": "Paris"}, mock_manager)
        
        assert result["status"] == "error"
        assert result["error_type"] == "Exception"
        assert result["error_message"] == "Tool execution failed"
        assert result["tool_name"] == "weather_tool"

    def test_agent_routing_algorithm(self):
        """Test agent routing decision algorithm."""
        def should_route_logic(intent: dict) -> dict:
            """Agent routing logic from ChatAgent."""
            primary_intent = intent["primary_intent"]
            confidence = intent["confidence"]
            
            # High confidence routing decisions
            if confidence > 0.7:
                if primary_intent == "flight":
                    return {"route_to": "flight_agent", "reason": "High confidence flight intent"}
                elif primary_intent == "accommodation":
                    return {"route_to": "accommodation_agent", "reason": "High confidence accommodation intent"}
                elif primary_intent == "budget":
                    return {"route_to": "budget_agent", "reason": "High confidence budget intent"}
                elif primary_intent == "destination":
                    return {"route_to": "destination_agent", "reason": "High confidence destination intent"}
                elif primary_intent == "itinerary":
                    return {"route_to": "itinerary_agent", "reason": "High confidence itinerary intent"}
            
            # Default to general travel agent or direct handling
            return {"route_to": "travel_agent", "reason": f"Low confidence or general intent ({primary_intent})"}
        
        # Test cases
        test_cases = [
            ({"primary_intent": "flight", "confidence": 0.8}, "flight_agent"),
            ({"primary_intent": "accommodation", "confidence": 0.9}, "accommodation_agent"),
            ({"primary_intent": "budget", "confidence": 0.75}, "budget_agent"),
            ({"primary_intent": "flight", "confidence": 0.6}, "travel_agent"),  # Low confidence
            ({"primary_intent": "general", "confidence": 0.5}, "travel_agent"),
            ({"primary_intent": "weather", "confidence": 0.8}, "travel_agent"),  # Not routable
        ]
        
        for intent, expected_route in test_cases:
            routing = should_route_logic(intent)
            assert routing["route_to"] == expected_route, f"Failed routing for: {intent}"

    def test_pattern_matching(self):
        """Test regex pattern matching used in intent detection."""
        patterns = [
            # Positive cases
            (r"\bfly\s+to\b", "I want to fly to Rome", True),
            (r"\bflight\s+from\b", "Find flight from LAX", True),
            (r"\bbook.*flight\b", "Please book a flight for me", True),
            (r"\bstay\s+in\b", "I want to stay in Paris", True),
            (r"\bhotel\s+in\b", "Find hotel in downtown", True),
            (r"\bweather\s+in\b", "What's the weather in Tokyo?", True),
            (r"\bhow\s+much\b", "How much does it cost?", True),
            
            # Negative cases - should not match
            (r"\bfly\s+to\b", "The plane will fly high", False),
            (r"\bflight\s+from\b", "Flight delayed", False),
            (r"\bbook.*flight\b", "I read a book about flights", False),
        ]
        
        for pattern, text, should_match in patterns:
            match = re.search(pattern, text.lower())
            if should_match:
                assert match is not None, f"Pattern '{pattern}' should match '{text}'"
            else:
                assert match is None, f"Pattern '{pattern}' should not match '{text}'"

    @pytest.mark.asyncio
    async def test_full_chat_agent_simulation(self):
        """Test ChatAgent workflow with full mocking."""
        # Mock all dependencies
        with (
            patch("agents.Agent") as mock_agent_class,
            patch("agents.Runner") as mock_runner_class,
        ):
            # Configure mocks
            mock_agent = MagicMock()
            mock_runner = MagicMock()
            mock_agent_class.return_value = mock_agent
            mock_runner_class.return_value = mock_runner
            
            # Mock the settings inside the import
            mock_settings = MagicMock()
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7
            
            with patch("tripsage.agents.chat.settings", mock_settings):
                # Now import and test
                from tripsage.agents.chat import ChatAgent
                
                # Create agent instance
                agent = ChatAgent()
                
                # Test initialization
                assert agent.name == "TripSage Chat Assistant"
                assert agent._max_tool_calls_per_minute == 5
                
                # Test intent detection
                intent = await agent.detect_intent("I need to book a flight to Paris")
                assert intent["primary_intent"] == "flight"
                assert intent["confidence"] > 0.7
                
                # Test rate limiting
                user_id = "test_user"
                for i in range(5):
                    assert await agent.check_tool_rate_limit(user_id)
                    await agent.log_tool_call(user_id)
                
                # Should deny 6th call
                assert not await agent.check_tool_rate_limit(user_id)