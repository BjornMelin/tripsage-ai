"""Comprehensive tests for orchestration state management.

This module provides full test coverage for the TravelPlanningState and
related Pydantic models used in the orchestration system.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from tripsage.orchestration.state import (
    BookingProgress,
    DestinationInfo,
    ErrorInfo,
    HandoffContext,
    SearchResult,
    ToolCallInfo,
    TravelDates,
    UserPreferences,
    create_initial_state,
    update_state_timestamp,
)


class TestUserPreferences:
    """Test UserPreferences Pydantic model."""

    def test_user_preferences_creation(self):
        """Test creating UserPreferences with valid data."""
        prefs = UserPreferences(
            budget_total=5000.0,
            budget_currency="EUR",
            preferred_airlines=["Delta", "United"],
            seat_class="business",
            accommodation_type="hotel",
            meal_preferences=["vegetarian"],
            accessibility_needs=["wheelchair_accessible"],
            travel_style="comfort",
        )

        assert prefs.budget_total == 5000.0
        assert prefs.budget_currency == "EUR"
        assert prefs.preferred_airlines == ["Delta", "United"]
        assert prefs.seat_class == "business"
        assert prefs.accommodation_type == "hotel"
        assert prefs.meal_preferences == ["vegetarian"]
        assert prefs.accessibility_needs == ["wheelchair_accessible"]
        assert prefs.travel_style == "comfort"

    def test_user_preferences_defaults(self):
        """Test UserPreferences with default values."""
        prefs = UserPreferences()

        assert prefs.budget_total is None
        assert prefs.budget_currency == "USD"
        assert prefs.preferred_airlines == []
        assert prefs.seat_class is None
        assert prefs.accommodation_type is None
        assert prefs.meal_preferences == []
        assert prefs.accessibility_needs == []
        assert prefs.travel_style is None

    def test_user_preferences_invalid_seat_class(self):
        """Test UserPreferences with invalid seat class."""
        with pytest.raises(ValidationError):
            UserPreferences(seat_class="invalid_class")

    def test_user_preferences_invalid_accommodation_type(self):
        """Test UserPreferences with invalid accommodation type."""
        with pytest.raises(ValidationError):
            UserPreferences(accommodation_type="invalid_type")

    def test_user_preferences_invalid_travel_style(self):
        """Test UserPreferences with invalid travel style."""
        with pytest.raises(ValidationError):
            UserPreferences(travel_style="invalid_style")


class TestTravelDates:
    """Test TravelDates Pydantic model."""

    def test_travel_dates_creation(self):
        """Test creating TravelDates with valid data."""
        dates = TravelDates(
            departure_date="2024-06-15",
            return_date="2024-06-22",
            flexible_dates=True,
            date_range_days=3,
        )

        assert dates.departure_date == "2024-06-15"
        assert dates.return_date == "2024-06-22"
        assert dates.flexible_dates is True
        assert dates.date_range_days == 3

    def test_travel_dates_defaults(self):
        """Test TravelDates with default values."""
        dates = TravelDates()

        assert dates.departure_date is None
        assert dates.return_date is None
        assert dates.flexible_dates is False
        assert dates.date_range_days is None

    def test_travel_dates_one_way(self):
        """Test TravelDates for one-way trip."""
        dates = TravelDates(departure_date="2024-06-15", flexible_dates=False)

        assert dates.departure_date == "2024-06-15"
        assert dates.return_date is None
        assert dates.flexible_dates is False


class TestDestinationInfo:
    """Test DestinationInfo Pydantic model."""

    def test_destination_info_creation(self):
        """Test creating DestinationInfo with valid data."""
        dest = DestinationInfo(
            origin="New York",
            destination="Paris",
            intermediate_stops=["London"],
            trip_type="round_trip",
            purpose="leisure",
        )

        assert dest.origin == "New York"
        assert dest.destination == "Paris"
        assert dest.intermediate_stops == ["London"]
        assert dest.trip_type == "round_trip"
        assert dest.purpose == "leisure"

    def test_destination_info_defaults(self):
        """Test DestinationInfo with default values."""
        dest = DestinationInfo()

        assert dest.origin is None
        assert dest.destination is None
        assert dest.intermediate_stops == []
        assert dest.trip_type is None
        assert dest.purpose is None

    def test_destination_info_invalid_trip_type(self):
        """Test DestinationInfo with invalid trip type."""
        with pytest.raises(ValidationError):
            DestinationInfo(trip_type="invalid_type")

    def test_destination_info_invalid_purpose(self):
        """Test DestinationInfo with invalid purpose."""
        with pytest.raises(ValidationError):
            DestinationInfo(purpose="invalid_purpose")


class TestSearchResult:
    """Test SearchResult Pydantic model."""

    def test_search_result_creation(self):
        """Test creating SearchResult with valid data."""
        result = SearchResult(
            search_id="search_123",
            timestamp="2024-01-15T10:00:00Z",
            agent="flight_agent",
            parameters={"origin": "NYC", "destination": "LAX"},
            results=[{"flight_id": "FL123", "price": 299}],
            result_count=1,
            status="success",
        )

        assert result.search_id == "search_123"
        assert result.timestamp == "2024-01-15T10:00:00Z"
        assert result.agent == "flight_agent"
        assert result.parameters == {"origin": "NYC", "destination": "LAX"}
        assert result.results == [{"flight_id": "FL123", "price": 299}]
        assert result.result_count == 1
        assert result.status == "success"
        assert result.error_message is None

    def test_search_result_with_error(self):
        """Test SearchResult with error status."""
        result = SearchResult(
            search_id="search_456",
            timestamp="2024-01-15T10:00:00Z",
            agent="flight_agent",
            parameters={"origin": "NYC"},
            results=[],
            result_count=0,
            status="error",
            error_message="Missing destination",
        )

        assert result.status == "error"
        assert result.error_message == "Missing destination"
        assert result.result_count == 0

    def test_search_result_invalid_status(self):
        """Test SearchResult with invalid status."""
        with pytest.raises(ValidationError):
            SearchResult(
                search_id="search_789",
                timestamp="2024-01-15T10:00:00Z",
                agent="flight_agent",
                parameters={},
                results=[],
                result_count=0,
                status="invalid_status",
            )


class TestBookingProgress:
    """Test BookingProgress Pydantic model."""

    def test_booking_progress_creation(self):
        """Test creating BookingProgress with valid data."""
        progress = BookingProgress(
            flight_booking={"booking_id": "FL123", "status": "confirmed"},
            accommodation_booking={"booking_id": "HT456", "status": "pending"},
            activity_bookings=[{"booking_id": "AC789", "status": "confirmed"}],
            total_cost=1500.0,
            currency="EUR",
            status="booking",
        )

        assert progress.flight_booking == {"booking_id": "FL123", "status": "confirmed"}
        assert progress.accommodation_booking == {
            "booking_id": "HT456",
            "status": "pending",
        }
        assert progress.activity_bookings == [
            {"booking_id": "AC789", "status": "confirmed"}
        ]
        assert progress.total_cost == 1500.0
        assert progress.currency == "EUR"
        assert progress.status == "booking"

    def test_booking_progress_defaults(self):
        """Test BookingProgress with default values."""
        progress = BookingProgress()

        assert progress.flight_booking is None
        assert progress.accommodation_booking is None
        assert progress.activity_bookings == []
        assert progress.total_cost is None
        assert progress.currency == "USD"
        assert progress.status == "planning"

    def test_booking_progress_invalid_status(self):
        """Test BookingProgress with invalid status."""
        with pytest.raises(ValidationError):
            BookingProgress(status="invalid_status")


class TestHandoffContext:
    """Test HandoffContext Pydantic model."""

    def test_handoff_context_creation(self):
        """Test creating HandoffContext with valid data."""
        context = HandoffContext(
            from_agent="router",
            to_agent="flight_agent",
            routing_confidence=0.95,
            routing_reasoning="User mentioned flights and specific dates",
            timestamp="2024-01-15T10:00:00Z",
            message_analyzed="I need flights from NYC to LAX on June 15th",
            additional_context={
                "extracted_entities": {"origin": "NYC", "destination": "LAX"}
            },
        )

        assert context.from_agent == "router"
        assert context.to_agent == "flight_agent"
        assert context.routing_confidence == 0.95
        assert context.routing_reasoning == "User mentioned flights and specific dates"
        assert context.timestamp == "2024-01-15T10:00:00Z"
        assert context.message_analyzed == "I need flights from NYC to LAX on June 15th"
        assert context.additional_context == {
            "extracted_entities": {"origin": "NYC", "destination": "LAX"}
        }

    def test_handoff_context_required_fields(self):
        """Test HandoffContext with only required fields."""
        context = HandoffContext(
            from_agent="router",
            to_agent="flight_agent",
            routing_confidence=0.8,
            routing_reasoning="Flight search request",
            timestamp="2024-01-15T10:00:00Z",
            message_analyzed="book flights",
        )

        assert context.additional_context == {}


class TestErrorInfo:
    """Test ErrorInfo Pydantic model."""

    def test_error_info_creation(self):
        """Test creating ErrorInfo with valid data."""
        error_info = ErrorInfo(
            error_count=3,
            last_error="Connection timeout",
            retry_attempts={"flight_agent": 2, "accommodation_agent": 1},
            error_history=[
                {"error": "timeout", "timestamp": "2024-01-15T10:00:00Z"},
                {"error": "service unavailable", "timestamp": "2024-01-15T10:05:00Z"},
            ],
        )

        assert error_info.error_count == 3
        assert error_info.last_error == "Connection timeout"
        assert error_info.retry_attempts == {
            "flight_agent": 2,
            "accommodation_agent": 1,
        }
        assert len(error_info.error_history) == 2

    def test_error_info_defaults(self):
        """Test ErrorInfo with default values."""
        error_info = ErrorInfo()

        assert error_info.error_count == 0
        assert error_info.last_error is None
        assert error_info.retry_attempts == {}
        assert error_info.error_history == []


class TestToolCallInfo:
    """Test ToolCallInfo Pydantic model."""

    def test_tool_call_info_creation(self):
        """Test creating ToolCallInfo with valid data."""
        tool_call = ToolCallInfo(
            tool_name="flights_search_flights",
            timestamp="2024-01-15T10:00:00Z",
            parameters={"origin": "NYC", "destination": "LAX"},
            result={"flights": []},
            status="success",
            execution_time_ms=1500.0,
        )

        assert tool_call.tool_name == "flights_search_flights"
        assert tool_call.timestamp == "2024-01-15T10:00:00Z"
        assert tool_call.parameters == {"origin": "NYC", "destination": "LAX"}
        assert tool_call.result == {"flights": []}
        assert tool_call.status == "success"
        assert tool_call.execution_time_ms == 1500.0

    def test_tool_call_info_defaults(self):
        """Test ToolCallInfo with default values."""
        tool_call = ToolCallInfo(
            tool_name="test_tool", timestamp="2024-01-15T10:00:00Z", parameters={}
        )

        assert tool_call.result is None
        assert tool_call.status == "pending"
        assert tool_call.error_message is None
        assert tool_call.execution_time_ms is None

    def test_tool_call_info_with_error(self):
        """Test ToolCallInfo with error status."""
        tool_call = ToolCallInfo(
            tool_name="test_tool",
            timestamp="2024-01-15T10:00:00Z",
            parameters={},
            status="error",
            error_message="Tool execution failed",
        )

        assert tool_call.status == "error"
        assert tool_call.error_message == "Tool execution failed"

    def test_tool_call_info_invalid_status(self):
        """Test ToolCallInfo with invalid status."""
        with pytest.raises(ValidationError):
            ToolCallInfo(
                tool_name="test_tool",
                timestamp="2024-01-15T10:00:00Z",
                parameters={},
                status="invalid_status",
            )


class TestTravelPlanningState:
    """Test TravelPlanningState TypedDict and related functions."""

    def test_create_initial_state(self):
        """Test creating initial state with default values."""
        state = create_initial_state(
            user_id="user_123", message="I want to plan a trip to Paris"
        )

        # Check core fields
        assert state["user_id"] == "user_123"
        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "user"
        assert state["messages"][0]["content"] == "I want to plan a trip to Paris"
        assert "timestamp" in state["messages"][0]

        # Check session ID generation
        assert state["session_id"].startswith("session_user_123_")

        # Check structured fields are None initially
        assert state["user_preferences"] is None
        assert state["travel_dates"] is None
        assert state["destination_info"] is None
        assert state["booking_progress"] is None
        assert state["handoff_context"] is None

        # Check empty lists
        assert state["flight_searches"] == []
        assert state["accommodation_searches"] == []
        assert state["activity_searches"] == []
        assert state["active_tool_calls"] == []
        assert state["completed_tool_calls"] == []

        # Check error info
        error_info = ErrorInfo.model_validate(state["error_info"])
        assert error_info.error_count == 0
        assert error_info.last_error is None

        # Check agent coordination
        assert state["current_agent"] is None
        assert state["agent_history"] == []

        # Check session metadata
        assert state["created_at"] is not None
        assert state["updated_at"] is not None
        assert state["last_activity"] is not None
        assert state["is_active"] is True

        # Check memory fields
        assert state["conversation_summary"] is None
        assert state["extracted_entities"] == {}
        assert state["user_intent"] is None
        assert state["confidence_score"] is None

    def test_create_initial_state_with_session_id(self):
        """Test creating initial state with provided session ID."""
        custom_session_id = "custom_session_456"

        state = create_initial_state(
            user_id="user_123", message="Hello", session_id=custom_session_id
        )

        assert state["session_id"] == custom_session_id

    def test_update_state_timestamp(self):
        """Test updating state timestamp."""
        state = create_initial_state(user_id="user_123", message="Test message")

        original_timestamp = state["updated_at"]

        # Wait a small amount to ensure timestamp difference
        import time

        time.sleep(0.001)

        updated_state = update_state_timestamp(state)

        assert updated_state["updated_at"] != original_timestamp
        assert updated_state is state  # Should modify in place


class TestStateModels:
    """Test state model serialization and validation."""

    def test_user_preferences_serialization(self):
        """Test UserPreferences model serialization for state storage."""
        prefs = UserPreferences(
            budget_total=2000.0, preferred_airlines=["Delta"], seat_class="economy"
        )

        # Test serialization
        prefs_dict = prefs.model_dump()
        assert isinstance(prefs_dict, dict)
        assert prefs_dict["budget_total"] == 2000.0
        assert prefs_dict["preferred_airlines"] == ["Delta"]
        assert prefs_dict["seat_class"] == "economy"

        # Test deserialization
        reconstructed = UserPreferences.model_validate(prefs_dict)
        assert reconstructed.budget_total == 2000.0
        assert reconstructed.preferred_airlines == ["Delta"]
        assert reconstructed.seat_class == "economy"

    def test_search_result_serialization(self):
        """Test SearchResult model serialization for state storage."""
        result = SearchResult(
            search_id="search_123",
            timestamp="2024-01-15T10:00:00Z",
            agent="flight_agent",
            parameters={"origin": "NYC"},
            results=[{"flight_id": "FL123"}],
            result_count=1,
            status="success",
        )

        # Test serialization
        result_dict = result.model_dump()
        assert isinstance(result_dict, dict)
        assert result_dict["search_id"] == "search_123"
        assert result_dict["status"] == "success"

        # Test deserialization
        reconstructed = SearchResult.model_validate(result_dict)
        assert reconstructed.search_id == "search_123"
        assert reconstructed.status == "success"

    def test_error_info_accumulation(self):
        """Test ErrorInfo model for accumulating error information."""
        error_info = ErrorInfo()

        # Simulate error accumulation
        error_info.error_count += 1
        error_info.last_error = "First error"
        error_info.retry_attempts["agent_1"] = 1
        error_info.error_history.append(
            {
                "error": "First error",
                "timestamp": "2024-01-15T10:00:00Z",
                "agent": "agent_1",
            }
        )

        # Add another error
        error_info.error_count += 1
        error_info.last_error = "Second error"
        error_info.retry_attempts["agent_1"] = 2
        error_info.error_history.append(
            {
                "error": "Second error",
                "timestamp": "2024-01-15T10:05:00Z",
                "agent": "agent_1",
            }
        )

        assert error_info.error_count == 2
        assert error_info.last_error == "Second error"
        assert error_info.retry_attempts["agent_1"] == 2
        assert len(error_info.error_history) == 2

    def test_handoff_context_workflow(self):
        """Test HandoffContext model for agent handoff scenarios."""
        # Router to flight agent handoff
        handoff = HandoffContext(
            from_agent="router",
            to_agent="flight_agent",
            routing_confidence=0.9,
            routing_reasoning="User specifically mentioned flights and dates",
            timestamp="2024-01-15T10:00:00Z",
            message_analyzed="I need to book flights from NYC to LAX for June 15th",
            additional_context={
                "extracted_entities": {
                    "origin": "NYC",
                    "destination": "LAX",
                    "departure_date": "2024-06-15",
                },
                "confidence_factors": ["explicit_flight_mention", "specific_dates"],
            },
        )

        assert handoff.from_agent == "router"
        assert handoff.to_agent == "flight_agent"
        assert handoff.routing_confidence == 0.9
        assert "extracted_entities" in handoff.additional_context
        assert handoff.additional_context["extracted_entities"]["origin"] == "NYC"


class TestStateIntegration:
    """Integration tests for state management."""

    def test_complete_state_workflow(self):
        """Test a complete state workflow with all components."""
        # Create initial state
        state = create_initial_state(
            user_id="user_456", message="I want to plan a honeymoon trip to Italy"
        )

        # Add user preferences
        preferences = UserPreferences(
            budget_total=5000.0, travel_style="luxury", accommodation_type="hotel"
        )
        state["user_preferences"] = preferences.model_dump()

        # Add travel dates
        dates = TravelDates(
            departure_date="2024-07-15",
            return_date="2024-07-29",
            flexible_dates=True,
            date_range_days=3,
        )
        state["travel_dates"] = dates.model_dump()

        # Add destination info
        destination = DestinationInfo(
            destination="Italy", trip_type="round_trip", purpose="honeymoon"
        )
        state["destination_info"] = destination.model_dump()

        # Add a search result
        search_result = SearchResult(
            search_id="search_italy_hotels",
            timestamp=datetime.now().isoformat(),
            agent="accommodation_agent",
            parameters={"location": "Italy", "check_in": "2024-07-15"},
            results=[{"hotel_id": "HT123", "name": "Grand Hotel Rome"}],
            result_count=1,
            status="success",
        )
        state["accommodation_searches"] = [search_result.model_dump()]

        # Update state timestamp
        state = update_state_timestamp(state)

        # Verify state integrity
        assert state["user_id"] == "user_456"
        assert len(state["accommodation_searches"]) == 1

        # Verify model reconstruction
        reconstructed_prefs = UserPreferences.model_validate(state["user_preferences"])
        assert reconstructed_prefs.budget_total == 5000.0
        assert reconstructed_prefs.travel_style == "luxury"

        reconstructed_dates = TravelDates.model_validate(state["travel_dates"])
        assert reconstructed_dates.departure_date == "2024-07-15"
        assert reconstructed_dates.flexible_dates is True

        reconstructed_dest = DestinationInfo.model_validate(state["destination_info"])
        assert reconstructed_dest.destination == "Italy"
        assert reconstructed_dest.purpose == "honeymoon"

        reconstructed_search = SearchResult.model_validate(
            state["accommodation_searches"][0]
        )
        assert reconstructed_search.agent == "accommodation_agent"
        assert reconstructed_search.status == "success"
