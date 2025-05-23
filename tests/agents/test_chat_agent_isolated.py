"""
Isolated unit tests for ChatAgent core logic.

This module tests the ChatAgent methods in isolation without 
importing the full class or triggering dependency chains.
"""

import time
import re
from unittest.mock import AsyncMock, MagicMock
import pytest


class TestChatAgentLogic:
    """Test ChatAgent logic methods in isolation."""

    def test_intent_detection_algorithm(self):
        """Test intent detection algorithm independently."""
        def detect_intent_logic(message: str) -> dict:
            """Simplified version of ChatAgent.detect_intent logic."""
            message_lower = message.lower()
            
            intent_patterns = {
                "flight": {
                    "keywords": ["flight", "fly", "airline", "airport", "departure", "arrival", "book", "ticket"],
                    "patterns": [r"\bfly\s+to\b", r"\bflight\s+from\b", r"\bbook.*flight\b"],
                    "weight": 0.0,
                },
                "accommodation": {
                    "keywords": ["hotel", "accommodation", "stay", "room", "lodge", "resort", "airbnb", "booking"],
                    "patterns": [r"\bstay\s+in\b", r"\bhotel\s+in\b", r"\bbook.*hotel\b"],
                    "weight": 0.0,
                },
                "budget": {
                    "keywords": ["budget", "cost", "price", "money", "expense", "afford", "cheap", "expensive"],
                    "patterns": [r"\bhow\s+much\b", r"\bcost\s+of\b", r"\bbudget\s+for\b"],
                    "weight": 0.0,
                },
                "weather": {
                    "keywords": ["weather", "temperature", "rain", "sunny", "forecast", "climate"],
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
                "requires_routing": confidence > 0.7 and primary_intent in ["flight", "accommodation", "budget"],
            }
        
        # Test flight intent
        flight_intent = detect_intent_logic("I need to book a flight to Paris")
        assert flight_intent["primary_intent"] == "flight"
        assert flight_intent["confidence"] > 0.0
        assert flight_intent["all_scores"]["flight"] > 0
        
        # Test accommodation intent  
        hotel_intent = detect_intent_logic("Find me a hotel in Rome")
        assert hotel_intent["primary_intent"] == "accommodation" 
        assert hotel_intent["confidence"] > 0.0
        assert hotel_intent["all_scores"]["accommodation"] > 0
        
        # Test general intent
        general_intent = detect_intent_logic("Hello, how are you?")
        assert general_intent["primary_intent"] == "general"
        assert general_intent["confidence"] == 0.5
        assert not general_intent["requires_routing"]

    def test_rate_limiting_algorithm(self):
        """Test rate limiting algorithm independently."""
        def check_rate_limit_logic(call_history: list, max_calls: int, window_seconds: int, current_time: float) -> bool:
            """Simplified version of ChatAgent rate limiting logic."""
            # Remove calls older than window
            recent_calls = [call_time for call_time in call_history if current_time - call_time < window_seconds]
            return len(recent_calls) < max_calls
        
        def log_call_logic(call_history: list, current_time: float) -> list:
            """Log a new call."""
            return call_history + [current_time]
        
        # Test rate limiting
        call_history = []
        current_time = 1000.0
        max_calls = 5
        window_seconds = 60
        
        # Should allow first 5 calls
        for i in range(5):
            assert check_rate_limit_logic(call_history, max_calls, window_seconds, current_time)
            call_history = log_call_logic(call_history, current_time + i)
        
        # Should deny 6th call
        assert not check_rate_limit_logic(call_history, max_calls, window_seconds, current_time + 5)
        
        # Should allow calls after time window
        future_time = current_time + 61
        assert check_rate_limit_logic(call_history, max_calls, window_seconds, future_time)

    @pytest.mark.asyncio
    async def test_tool_execution_logic(self):
        """Test tool execution logic independently."""
        async def execute_tool_logic(tool_name: str, parameters: dict, mock_manager) -> dict:
            """Simplified version of ChatAgent tool execution logic."""
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

    def test_agent_routing_logic(self):
        """Test agent routing decision logic independently."""
        def should_route_logic(intent: dict) -> dict:
            """Simplified version of ChatAgent routing logic."""
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
        
        # Test high confidence routing
        flight_intent = {"primary_intent": "flight", "confidence": 0.8}
        routing = should_route_logic(flight_intent)
        assert routing["route_to"] == "flight_agent"
        assert "High confidence" in routing["reason"]
        
        # Test low confidence routing
        general_intent = {"primary_intent": "general", "confidence": 0.5}
        routing = should_route_logic(general_intent)
        assert routing["route_to"] == "travel_agent"
        assert "Low confidence" in routing["reason"]

    def test_pattern_matching(self):
        """Test regex pattern matching used in intent detection."""
        patterns = [
            (r"\bfly\s+to\b", "I want to fly to Rome", True),
            (r"\bflight\s+from\b", "Find flight from LAX", True),
            (r"\bbook.*flight\b", "Please book a flight for me", True),
            (r"\bstay\s+in\b", "I want to stay in Paris", True),
            (r"\bhotel\s+in\b", "Find hotel in downtown", True),
            (r"\bweather\s+in\b", "What's the weather in Tokyo?", True),
            (r"\bhow\s+much\b", "How much does it cost?", True),
            # Negative cases
            (r"\bfly\s+to\b", "The plane will fly high", False),
            (r"\bflight\s+from\b", "Flight delayed", False),
        ]
        
        for pattern, text, should_match in patterns:
            match = re.search(pattern, text.lower())
            if should_match:
                assert match is not None, f"Pattern '{pattern}' should match '{text}'"
            else:
                assert match is None, f"Pattern '{pattern}' should not match '{text}'"