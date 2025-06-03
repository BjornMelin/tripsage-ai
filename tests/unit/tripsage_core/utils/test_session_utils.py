"""
Unit tests for TripSage Core session utilities.

Tests session memory initialization, preference tracking, session summary storage,
learned facts processing, and integration with Mem0 memory system.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.utils.session_utils import (
    ConversationMessage,
    SessionMemory,
    SessionSummary,
    UserPreferences,
    _process_conversation_context,
    _process_learned_facts,
    _update_user_preferences_memory,
    initialize_session_memory,
    store_session_summary,
    update_session_memory,
)


class TestSessionModels:
    """Test session memory models."""

    def test_conversation_message_model(self):
        """Test ConversationMessage model."""
        message = ConversationMessage(
            role="user", content="I want to plan a trip to Paris"
        )
        assert message.role == "user"
        assert message.content == "I want to plan a trip to Paris"

    def test_session_summary_model(self):
        """Test SessionSummary model."""
        summary = SessionSummary(
            user_id="user123",
            session_id="session456",
            summary="User planned a trip to Paris",
            key_insights=["Budget-conscious traveler", "Prefers cultural activities"],
            decisions_made=["Selected 3-star hotel", "Booked museum passes"],
        )
        assert summary.user_id == "user123"
        assert summary.session_id == "session456"
        assert summary.summary == "User planned a trip to Paris"
        assert len(summary.key_insights) == 2
        assert len(summary.decisions_made) == 2

    def test_session_summary_model_minimal(self):
        """Test SessionSummary model with minimal data."""
        summary = SessionSummary(
            user_id="user123", session_id="session456", summary="Brief session"
        )
        assert summary.user_id == "user123"
        assert summary.session_id == "session456"
        assert summary.summary == "Brief session"
        assert summary.key_insights is None
        assert summary.decisions_made is None

    def test_user_preferences_model(self):
        """Test UserPreferences model."""
        preferences = UserPreferences(
            budget_range={"min": 1000, "max": 5000},
            preferred_destinations=["Paris", "Tokyo", "New York"],
            travel_style="cultural",
            accommodation_preferences={"type": "hotel", "stars": 4},
            dietary_restrictions=["vegetarian"],
            accessibility_needs=["wheelchair_accessible"],
        )
        assert preferences.budget_range["min"] == 1000
        assert "Paris" in preferences.preferred_destinations
        assert preferences.travel_style == "cultural"
        assert preferences.accommodation_preferences["type"] == "hotel"
        assert "vegetarian" in preferences.dietary_restrictions
        assert "wheelchair_accessible" in preferences.accessibility_needs

    def test_user_preferences_model_empty(self):
        """Test UserPreferences model with all None values."""
        preferences = UserPreferences()
        assert preferences.budget_range is None
        assert preferences.preferred_destinations is None
        assert preferences.travel_style is None
        assert preferences.accommodation_preferences is None
        assert preferences.dietary_restrictions is None
        assert preferences.accessibility_needs is None


class TestSessionMemoryUtility:
    """Test SessionMemory utility class."""

    def test_session_memory_initialization(self):
        """Test SessionMemory initialization."""
        session = SessionMemory("session123", "user456")
        assert session.session_id == "session123"
        assert session.user_id == "user456"
        assert session._memory_data == {}

    def test_session_memory_without_user(self):
        """Test SessionMemory initialization without user ID."""
        session = SessionMemory("session123")
        assert session.session_id == "session123"
        assert session.user_id is None

    def test_get_set_operations(self):
        """Test basic get and set operations."""
        session = SessionMemory("session123")

        # Test setting and getting
        session.set("key1", "value1")
        assert session.get("key1") == "value1"

        # Test getting non-existent key
        assert session.get("nonexistent") is None

        # Test getting with default
        assert session.get("nonexistent", "default") == "default"

    def test_update_operation(self):
        """Test update operation."""
        session = SessionMemory("session123")

        session.set("existing", "old_value")
        session.update({"existing": "new_value", "new_key": "new_value"})

        assert session.get("existing") == "new_value"
        assert session.get("new_key") == "new_value"

    def test_clear_operation(self):
        """Test clear operation."""
        session = SessionMemory("session123")

        session.set("key1", "value1")
        session.set("key2", "value2")
        assert len(session._memory_data) == 2

        session.clear()
        assert len(session._memory_data) == 0
        assert session.get("key1") is None

    def test_to_dict_operation(self):
        """Test to_dict conversion."""
        session = SessionMemory("session123", "user456")
        session.set("preference", "cultural")
        session.set("budget", 2000)

        result = session.to_dict()

        assert result["session_id"] == "session123"
        assert result["user_id"] == "user456"
        assert result["data"]["preference"] == "cultural"
        assert result["data"]["budget"] == 2000


class TestInitializeSessionMemory:
    """Test session memory initialization."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock()
        service.get_memories.return_value = []
        return service

    async def test_initialize_without_user_id(self):
        """Test initialization without user ID."""
        result = await initialize_session_memory()

        assert "user" in result
        assert "preferences" in result
        assert "recent_trips" in result
        assert "popular_destinations" in result
        assert "insights" in result

        assert result["user"] is None
        assert result["preferences"] == {}
        assert result["recent_trips"] == []

    async def test_initialize_with_user_id_no_memories(self, mock_memory_service):
        """Test initialization with user ID but no existing memories."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await initialize_session_memory("user123")

            assert result["user"]["id"] == "user123"
            assert result["preferences"] == {}
            assert result["recent_trips"] == []

    async def test_initialize_with_existing_preferences(self, mock_memory_service):
        """Test initialization with existing user preferences."""
        # Mock preference memories
        preference_memory = MagicMock()
        preference_memory.content = {
            "budget_range": {"min": 1000, "max": 3000},
            "travel_style": "adventure",
        }

        mock_memory_service.get_memories.side_effect = [
            [preference_memory],  # Preferences
            [],  # Trip history
        ]

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await initialize_session_memory("user123")

            assert result["user"]["id"] == "user123"
            assert result["preferences"]["budget_range"]["min"] == 1000
            assert result["preferences"]["travel_style"] == "adventure"

    async def test_initialize_with_trip_history(self, mock_memory_service):
        """Test initialization with existing trip history."""
        # Mock trip memories
        trip_memory1 = MagicMock()
        trip_memory1.content = {"destination": "Paris", "year": 2023}
        trip_memory2 = MagicMock()
        trip_memory2.content = {"destination": "Tokyo", "year": 2022}

        mock_memory_service.get_memories.side_effect = [
            [],  # Preferences
            [trip_memory1, trip_memory2],  # Trip history
        ]

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await initialize_session_memory("user123")

            assert len(result["recent_trips"]) == 2
            assert result["recent_trips"][0]["destination"] == "Paris"
            assert result["recent_trips"][1]["destination"] == "Tokyo"

    async def test_initialize_with_service_error(self, caplog):
        """Test initialization when memory service fails."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            side_effect=Exception("Service error"),
        ):
            result = await initialize_session_memory("user123")

            # Should return default structure despite error
            assert result["user"] is None
            assert result["preferences"] == {}
            assert result["recent_trips"] == []

            # Should log the error
            assert "Error loading user context" in caplog.text

    async def test_initialize_memory_limit(self, mock_memory_service):
        """Test that trip history is limited to 5 most recent."""
        # Create 10 trip memories
        trip_memories = []
        for i in range(10):
            memory = MagicMock()
            memory.content = {"destination": f"City{i}", "year": 2020 + i}
            trip_memories.append(memory)

        mock_memory_service.get_memories.side_effect = [
            [],  # Preferences
            trip_memories,  # Trip history
        ]

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await initialize_session_memory("user123")

            # Should only include first 5 (most recent)
            assert len(result["recent_trips"]) == 5


class TestUpdateSessionMemory:
    """Test session memory updates."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock()
        service.add_memory.return_value = "memory_id_123"
        return service

    async def test_update_with_preferences(self, mock_memory_service):
        """Test updating session memory with preferences."""
        updates = {
            "preferences": {
                "budget_range": {"min": 2000, "max": 4000},
                "travel_style": "luxury",
            }
        }

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await update_session_memory("user123", updates)

            assert result["success"] is True
            assert result["preferences_updated"] == 1
            assert result["memories_created"] == 1
            assert len(result["errors"]) == 0

    async def test_update_with_learned_facts(self, mock_memory_service):
        """Test updating session memory with learned facts."""
        updates = {
            "learned_facts": [
                {"fact": "User prefers morning flights"},
                {"fact": "User has dietary restrictions"},
            ]
        }

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await update_session_memory("user123", updates)

            assert result["success"] is True
            assert result["facts_processed"] == 2
            assert result["memories_created"] == 2

    async def test_update_with_conversation_context(self, mock_memory_service):
        """Test updating session memory with conversation context."""
        updates = {
            "conversation_context": {
                "destinations_discussed": ["Paris", "Rome"],
                "travel_intent": "vacation",
                "budget_mentioned": 3000,
                "dates_mentioned": "July 2024",
            }
        }

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await update_session_memory("user123", updates)

            assert result["success"] is True
            assert result["memories_created"] == 1

    async def test_update_with_all_types(self, mock_memory_service):
        """Test updating session memory with all update types."""
        updates = {
            "preferences": {"travel_style": "adventure"},
            "learned_facts": [{"fact": "User likes hiking"}],
            "conversation_context": {"destinations_discussed": ["Nepal"]},
        }

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await update_session_memory("user123", updates)

            assert result["success"] is True
            assert result["preferences_updated"] == 1
            assert result["facts_processed"] == 1
            assert result["memories_created"] == 3

    async def test_update_with_service_error(self):
        """Test update when memory service fails."""
        updates = {"preferences": {"travel_style": "cultural"}}

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            side_effect=Exception("Service error"),
        ):
            result = await update_session_memory("user123", updates)

            assert result["success"] is False
            assert len(result["errors"]) == 1
            assert "Service error" in result["errors"][0]

    async def test_update_empty_updates(self, mock_memory_service):
        """Test update with empty updates."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await update_session_memory("user123", {})

            assert result["success"] is True
            assert result["memories_created"] == 0


class TestStoreSessionSummary:
    """Test session summary storage."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock()
        service.add_memory.return_value = "summary_memory_id"
        return service

    async def test_store_basic_summary(self, mock_memory_service):
        """Test storing basic session summary."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await store_session_summary(
                user_id="user123",
                summary="User planned a trip to Paris",
                session_id="session456",
            )

            assert result["status"] == "success"
            assert result["memory_id"] == "summary_memory_id"
            assert result["memories_created"] == 1

    async def test_store_detailed_summary(self, mock_memory_service):
        """Test storing detailed session summary with insights and decisions."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await store_session_summary(
                user_id="user123",
                summary="Comprehensive trip planning session",
                session_id="session456",
                key_insights=["Budget-conscious", "Prefers cultural activities"],
                decisions_made=["Selected budget hotel", "Booked museum passes"],
            )

            assert result["status"] == "success"
            assert result["memory_id"] == "summary_memory_id"
            assert result["memories_created"] == 1

            # Verify the call was made with correct content
            mock_memory_service.add_memory.assert_called_once()
            call_args = mock_memory_service.add_memory.call_args
            content = call_args[1]["content"]

            assert content["session_id"] == "session456"
            assert content["summary"] == "Comprehensive trip planning session"
            assert len(content["key_insights"]) == 2
            assert len(content["decisions_made"]) == 2

    async def test_store_summary_service_failure(self, mock_memory_service):
        """Test storing summary when memory service fails."""
        mock_memory_service.add_memory.return_value = None

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            return_value=mock_memory_service,
        ):
            result = await store_session_summary(
                user_id="user123", summary="Failed summary", session_id="session456"
            )

            assert result["status"] == "error"
            assert result["error"] == "Failed to create memory"
            assert result["memories_created"] == 0

    async def test_store_summary_exception(self):
        """Test storing summary when exception occurs."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            side_effect=Exception("Connection error"),
        ):
            result = await store_session_summary(
                user_id="user123", summary="Exception summary", session_id="session456"
            )

            assert result["status"] == "error"
            assert "Connection error" in result["error"]
            assert result["memories_created"] == 0


class TestPrivateHelperFunctions:
    """Test private helper functions."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock()
        service.add_memory.return_value = "helper_memory_id"
        return service

    async def test_update_user_preferences_memory(self, mock_memory_service):
        """Test _update_user_preferences_memory helper."""
        preferences = {
            "budget_range": {"min": 1000, "max": 3000},
            "travel_style": "adventure",
        }
        result = {"errors": [], "memories_created": 0}

        await _update_user_preferences_memory(
            "user123", preferences, result, mock_memory_service
        )

        assert result["preferences_updated"] == 1
        assert result["memories_created"] == 1
        assert len(result.get("errors", [])) == 0

    async def test_update_preferences_invalid_data(self, mock_memory_service):
        """Test preference update with invalid data."""
        # Invalid preferences that don't match UserPreferences model
        preferences = {"invalid_field": "invalid_value"}
        result = {"errors": []}

        await _update_user_preferences_memory(
            "user123", preferences, result, mock_memory_service
        )

        # Should handle the error gracefully
        assert "errors" in result
        assert len(result["errors"]) > 0

    async def test_process_learned_facts(self, mock_memory_service):
        """Test _process_learned_facts helper."""
        facts = [
            {"fact": "User likes adventure travel"},
            "Simple string fact",
            {"insight": "User prefers budget options"},
        ]
        result = {"errors": [], "memories_created": 0}

        await _process_learned_facts("user123", facts, result, mock_memory_service)

        assert result["facts_processed"] == 3
        assert result["memories_created"] == 3

    async def test_process_conversation_context(self, mock_memory_service):
        """Test _process_conversation_context helper."""
        context = {
            "destinations_discussed": ["Paris", "London"],
            "travel_intent": "business",
            "budget_mentioned": 2500,
            "dates_mentioned": "Q2 2024",
            "irrelevant_field": "should be filtered out",
        }
        result = {"errors": [], "memories_created": 0}

        await _process_conversation_context(
            "user123", context, result, mock_memory_service
        )

        assert result["memories_created"] == 1

        # Verify only relevant fields were included
        call_args = mock_memory_service.add_memory.call_args
        content = call_args[1]["content"]

        assert "destinations_discussed" in content
        assert "travel_intent" in content
        assert "budget_mentioned" in content
        assert "dates_mentioned" in content
        assert "irrelevant_field" not in content

    async def test_process_conversation_context_empty(self, mock_memory_service):
        """Test conversation context processing with no relevant data."""
        context = {"irrelevant_field1": "value1", "irrelevant_field2": "value2"}
        result = {"errors": [], "memories_created": 0}

        await _process_conversation_context(
            "user123", context, result, mock_memory_service
        )

        # Should not create any memories for irrelevant data
        assert result.get("memories_created", 0) == 0
        mock_memory_service.add_memory.assert_not_called()


class TestErrorHandling:
    """Test error handling in session utilities."""

    async def test_memory_service_import_error(self):
        """Test handling of memory service import errors."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            side_effect=ImportError("Module not found"),
        ):
            result = await initialize_session_memory("user123")

            # Should return default structure
            assert result["user"] is None
            assert result["preferences"] == {}

    async def test_memory_service_connection_error(self):
        """Test handling of memory service connection errors."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService",
            side_effect=ConnectionError("Cannot connect"),
        ):
            result = await update_session_memory(
                "user123", {"preferences": {"style": "luxury"}}
            )

            assert result["success"] is False
            assert "Cannot connect" in result["errors"][0]

    async def test_partial_failure_handling(self):
        """Test handling of partial failures in updates."""
        # Mock service that fails on second call
        mock_service = AsyncMock()
        mock_service.add_memory.side_effect = [
            "memory_id_1",  # First call succeeds
            Exception("Second call fails"),  # Second call fails
            "memory_id_3",  # Third call succeeds
        ]

        updates = {
            "preferences": {"travel_style": "adventure"},
            "learned_facts": [{"fact": "User likes hiking"}],
            "conversation_context": {"destinations_discussed": ["Nepal"]},
        }

        with patch(
            "tripsage_core.services.business.memory_service.MemoryService", return_value=mock_service
        ):
            result = await update_session_memory("user123", updates)

            # Should be marked as failed due to exception
            assert result["success"] is False
            assert len(result["errors"]) > 0
