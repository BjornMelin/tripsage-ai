"""
Comprehensive test suite for memory tools.
Tests all memory tool functions, integration with memory service, and error handling.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.tools.memory_tools import (
    ConversationMessage,
    MemorySearchQuery,
    UserPreferences,
    add_conversation_memory,
    get_user_context,
    search_user_memories,
    update_user_preferences,
)


class TestMemoryTools:
    """Test suite for memory tool functions."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock()
        service.add_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem-123",
        }
        service.get_user_context.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation"},
                    "score": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {"accommodation": "luxury", "budget": "high"},
            "travel_patterns": {
                "favorite_destinations": ["Paris"],
                "avg_trip_duration": 7,
            },
        }
        service.search_memories.return_value = [
            {
                "content": "Looking for Paris hotels",
                "metadata": {"destination": "Paris"},
                "score": 0.88,
            }
        ]
        service.update_user_preferences.return_value = {"status": "success"}
        return service

    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages."""
        return [
            ConversationMessage(
                role="user",
                content="I'm planning a luxury honeymoon trip to Paris in June.",
                timestamp=datetime.fromisoformat("2024-01-01T10:00:00"),
            ),
            ConversationMessage(
                role="assistant",
                content="I'll help you plan a perfect honeymoon in Paris.",
                timestamp=datetime.fromisoformat("2024-01-01T10:01:00"),
            ),
        ]

    def test_conversation_message_model(self):
        """Test ConversationMessage pydantic model."""
        message = ConversationMessage(
            role="user",
            content="Test message content",
            timestamp=datetime.now(timezone.utc),
        )

        assert message.role == "user"
        assert message.content == "Test message content"
        assert isinstance(message.timestamp, datetime)

    def test_conversation_message_validation(self):
        """Test ConversationMessage validation."""
        # Test invalid role
        with pytest.raises(ValueError):
            ConversationMessage(
                role="invalid_role",
                content="Test",
                timestamp=datetime.now(timezone.utc),
            )

        # Test empty content
        with pytest.raises(ValueError):
            ConversationMessage(
                role="user", content="", timestamp=datetime.now(timezone.utc)
            )

    def test_memory_search_query_model(self):
        """Test MemorySearchQuery pydantic model."""
        query = MemorySearchQuery(
            user_id="user-123",
            query="luxury hotels Paris",
            limit=10,
            category_filter="accommodation",
        )

        assert query.user_id == "user-123"
        assert query.query == "luxury hotels Paris"
        assert query.limit == 10
        assert query.category_filter == "accommodation"

    def test_memory_search_query_defaults(self):
        """Test MemorySearchQuery default values."""
        query = MemorySearchQuery(user_id="user-123", query="test query")

        assert query.limit == 5  # Default limit
        assert query.category_filter is None

    def test_user_preferences_model(self):
        """Test UserPreferences pydantic model."""
        preferences = UserPreferences(
            user_id="user-123",
            accommodation="luxury",
            budget="high",
            destinations=["Europe", "Asia"],
            travel_style="adventure",
            dietary_restrictions=["vegetarian"],
        )

        assert preferences.user_id == "user-123"
        assert preferences.accommodation_type == "luxury"
        assert "Europe" in preferences.destinations
        assert "vegetarian" in preferences.dietary_restrictions

    @pytest.mark.asyncio
    async def test_add_conversation_memory_success(
        self, mock_memory_service, sample_messages
    ):
        """Test adding conversation memory successfully."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            result = await add_conversation_memory(
                messages=sample_messages, user_id="user-123", session_id="session-456"
            )

            assert result["status"] == "success"
            assert result["memory_id"] == "mem-123"

            # Verify service was called correctly
            mock_memory_service.add_conversation_memory.assert_called_once()
            call_args = mock_memory_service.add_conversation_memory.call_args[1]
            assert call_args["user_id"] == "user-123"
            assert call_args["session_id"] == "session-456"

    @pytest.mark.asyncio
    async def test_add_conversation_memory_with_metadata(
        self, mock_memory_service, sample_messages
    ):
        """Test adding conversation memory with additional metadata."""
        metadata = {"trip_type": "honeymoon", "destination": "Paris"}

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            await add_conversation_memory(
                messages=sample_messages, user_id="user-123", metadata=metadata
            )

            call_args = mock_memory_service.add_conversation_memory.call_args[1]
            assert call_args["metadata"]["trip_type"] == "honeymoon"
            assert call_args["metadata"]["destination"] == "Paris"

    @pytest.mark.asyncio
    async def test_add_conversation_memory_empty_messages(self, mock_memory_service):
        """Test adding conversation memory with empty messages."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            with pytest.raises(ValueError, match="Messages cannot be empty"):
                await add_conversation_memory(messages=[], user_id="user-123")

    @pytest.mark.asyncio
    async def test_add_conversation_memory_invalid_user_id(
        self, mock_memory_service, sample_messages
    ):
        """Test adding conversation memory with invalid user ID."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            with pytest.raises(ValueError, match="User ID cannot be empty"):
                await add_conversation_memory(messages=sample_messages, user_id="")

    @pytest.mark.asyncio
    async def test_get_user_context_success(self, mock_memory_service):
        """Test getting user context successfully."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            result = await get_user_context("user-123")

            assert "memories" in result
            assert "preferences" in result
            assert "travel_patterns" in result
            assert len(result["memories"]) == 1
            assert result["preferences"]["accommodation"] == "luxury"

            mock_memory_service.get_user_context.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_get_user_context_invalid_user_id(self, mock_memory_service):
        """Test getting user context with invalid user ID."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            with pytest.raises(ValueError, match="User ID cannot be empty"):
                await get_user_context("")

    @pytest.mark.asyncio
    async def test_search_user_memories_success(self, mock_memory_service):
        """Test searching user memories successfully."""
        query = MemorySearchQuery(
            user_id="user-123",
            query="Paris hotels",
            limit=10,
            category_filter="accommodation",
        )

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            result = await search_user_memories(query)

            assert len(result) == 1
            assert result[0]["content"] == "Looking for Paris hotels"
            assert result[0]["score"] == 0.88

            # Verify service was called with correct parameters
            mock_memory_service.search_memories.assert_called_once()
            call_args = mock_memory_service.search_memories.call_args[1]
            assert call_args["user_id"] == "user-123"
            assert call_args["query"] == "Paris hotels"
            assert call_args["limit"] == 10
            assert call_args["category_filter"] == "accommodation"

    @pytest.mark.asyncio
    async def test_search_user_memories_no_filter(self, mock_memory_service):
        """Test searching user memories without category filter."""
        query = MemorySearchQuery(user_id="user-123", query="travel plans")

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            await search_user_memories(query)

            call_args = mock_memory_service.search_memories.call_args[1]
            assert (
                "category_filter" not in call_args
                or call_args["category_filter"] is None
            )

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, mock_memory_service):
        """Test updating user preferences successfully."""
        preferences = UserPreferences(
            user_id="user-123",
            accommodation="luxury",
            budget="high",
            destinations=["Europe", "Asia"],
            travel_style="luxury",
        )

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            result = await update_user_preferences(preferences)

            assert result["status"] == "success"

            # Verify service was called correctly
            mock_memory_service.update_user_preferences.assert_called_once()
            call_args = mock_memory_service.update_user_preferences.call_args[1]
            assert call_args["user_id"] == "user-123"
            assert call_args["preferences"]["accommodation"] == "luxury"

    @pytest.mark.asyncio
    async def test_update_user_preferences_partial_update(self, mock_memory_service):
        """Test updating user preferences with partial data."""
        preferences = UserPreferences(
            user_id="user-123",
            accommodation="budget",  # Only updating accommodation
        )

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            await update_user_preferences(preferences)

            call_args = mock_memory_service.update_user_preferences.call_args[1]
            assert call_args["preferences"]["accommodation"] == "budget"
            # Other fields should not be included in the update
            assert "budget" not in call_args["preferences"]

    @pytest.mark.asyncio
    async def test_memory_service_error_handling(
        self, mock_memory_service, sample_messages
    ):
        """Test error handling when memory service fails."""
        mock_memory_service.add_conversation_memory.side_effect = Exception(
            "Service unavailable"
        )

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            # The @with_error_handling decorator should handle this gracefully
            result = await add_conversation_memory(
                messages=sample_messages, user_id="user-123"
            )

            # Should return error result, not raise exception
            assert result is not None

    @pytest.mark.asyncio
    async def test_memory_service_timeout_handling(self, mock_memory_service):
        """Test handling of service timeouts."""

        mock_memory_service.get_user_context.side_effect = asyncio.TimeoutError(
            "Service timeout"
        )

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            # Should handle timeout gracefully
            result = await get_user_context("user-123")
            assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, mock_memory_service):
        """Test concurrent memory operations."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            # Create multiple concurrent operations
            tasks = []
            for i in range(5):
                query = MemorySearchQuery(user_id=f"user-{i}", query=f"query-{i}")
                task = search_user_memories(query)
                tasks.append(task)

            # Wait for all to complete
            results = await asyncio.gather(*tasks)

            # Verify all completed successfully
            assert len(results) == 5
            assert all(isinstance(result, list) for result in results)

    def test_conversation_message_serialization(self):
        """Test ConversationMessage JSON serialization."""
        message = ConversationMessage(
            role="user",
            content="Test message",
            timestamp=datetime.fromisoformat("2024-01-01T10:00:00"),
        )

        # Test model_dump (Pydantic v2)
        data = message.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "Test message"

        # Test JSON serialization
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["role"] == "user"

    def test_memory_search_query_serialization(self):
        """Test MemorySearchQuery JSON serialization."""
        query = MemorySearchQuery(user_id="user-123", query="test query", limit=10)

        data = query.model_dump()
        assert data["user_id"] == "user-123"
        assert data["limit"] == 10

    def test_user_preferences_serialization(self):
        """Test UserPreferences JSON serialization."""
        preferences = UserPreferences(
            user_id="user-123", accommodation="luxury", destinations=["Europe"]
        )

        data = preferences.model_dump(exclude_unset=True, by_alias=True)
        assert data["accommodation"] == "luxury"
        assert "Europe" in data["destinations"]
        # Fields not set should be excluded
        assert "budget" not in data

    @pytest.mark.asyncio
    async def test_memory_tools_integration_workflow(self, mock_memory_service):
        """Test complete memory tools integration workflow."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            # Step 1: Add conversation memory
            messages = [
                ConversationMessage(
                    role="user",
                    content="Plan trip to Tokyo",
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            add_result = await add_conversation_memory(
                messages=messages, user_id="user-123"
            )

            # Step 2: Search for related memories
            search_query = MemorySearchQuery(user_id="user-123", query="Tokyo trip")

            search_result = await search_user_memories(search_query)

            # Step 3: Get user context
            context = await get_user_context("user-123")

            # Step 4: Update preferences
            preferences = UserPreferences(user_id="user-123", destinations=["Japan"])

            update_result = await update_user_preferences(preferences)

            # Verify all operations completed
            assert add_result["status"] == "success"
            assert len(search_result) > 0
            assert "memories" in context
            assert update_result["status"] == "success"

    @pytest.mark.asyncio
    async def test_memory_tools_data_validation(self):
        """Test data validation in memory tools."""
        # Test invalid message role
        with pytest.raises(ValueError):
            ConversationMessage(
                role="invalid", content="test", timestamp=datetime.now(timezone.utc)
            )

        # Test empty query
        with pytest.raises(ValueError):
            MemorySearchQuery(user_id="user-123", query="")

        # Test invalid limit
        with pytest.raises(ValueError):
            MemorySearchQuery(user_id="user-123", query="test", limit=0)

    @pytest.mark.asyncio
    async def test_memory_tools_performance(self, mock_memory_service):
        """Test memory tools performance characteristics."""
        import time

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            # Measure search performance
            start_time = time.time()

            query = MemorySearchQuery(user_id="user-123", query="performance test")

            result = await search_user_memories(query)

            end_time = time.time()
            operation_time = end_time - start_time

            # Should complete quickly (adjust threshold as needed)
            assert operation_time < 0.1  # 100ms
            assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_memory_tools_edge_cases(self, mock_memory_service):
        """Test memory tools edge cases."""
        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_memory_service):
            # Test with very long content
            long_content = "A" * 10000  # 10K characters
            messages = [
                ConversationMessage(
                    role="user",
                    content=long_content,
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            result = await add_conversation_memory(
                messages=messages, user_id="user-123"
            )

            assert result is not None

            # Test with special characters
            special_content = "Special chars: àáâãäåæçèéêë 🇫🇷 🎯 ñ"
            messages = [
                ConversationMessage(
                    role="user",
                    content=special_content,
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            result = await add_conversation_memory(
                messages=messages, user_id="user-123"
            )

            assert result is not None


class TestMemoryToolsIntegration:
    """Integration tests for memory tools with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_travel_planning_scenario(self):
        """Test memory tools in a travel planning scenario."""
        mock_service = AsyncMock()
        mock_service.add_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem-travel",
        }
        mock_service.get_user_context.return_value = {
            "memories": [
                {"id": "mem-1", "content": "Planning trip to Japan", "score": 0.9}
            ],
            "preferences": {"destination": "Japan", "budget": "medium"},
            "travel_patterns": {"avg_trip_duration": 10},
        }

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_service):
            # Simulate travel planning conversation
            messages = [
                ConversationMessage(
                    role="user",
                    content="I want to plan a 10-day trip to Japan in spring 2024",
                    timestamp=datetime.now(timezone.utc),
                ),
                ConversationMessage(
                    role="assistant",
                    content=(
                        "Japan in spring is beautiful! "
                        "I'll help you plan your cherry blossom trip."
                    ),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]

            # Store conversation
            result = await add_conversation_memory(
                messages=messages,
                user_id="traveler-123",
                metadata={"trip_type": "leisure", "season": "spring"},
            )

            # Get context for personalization
            context = await get_user_context("traveler-123")

            assert result["status"] == "success"
            assert "Japan" in str(context["memories"])

    @pytest.mark.asyncio
    async def test_preference_learning_scenario(self):
        """Test preference learning through conversations."""
        mock_service = AsyncMock()
        mock_service.update_user_preferences.return_value = {"status": "success"}

        with patch("tripsage.tools.memory_tools.get_memory_service", return_value=mock_service):
            # User reveals preferences through conversation
            preferences = UserPreferences(
                user_id="learner-123",
                accommodation="boutique",
                budget="medium",
                travel_style="cultural",
                dietary_restrictions=["vegetarian"],
                destinations=["Europe", "Asia"],
            )

            result = await update_user_preferences(preferences)

            assert result["status"] == "success"

            # Verify preferences were stored correctly
            call_args = mock_service.update_user_preferences.call_args[1]
            assert call_args["preferences"]["accommodation"] == "boutique"
            assert "vegetarian" in call_args["preferences"]["dietary_restrictions"]


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=tripsage.tools.memory_tools",
            "--cov-report=term-missing",
        ]
    )
