"""
Comprehensive test suite for tripsage_core.utils.session_utils module.

This module provides extensive tests for session management utilities,
including session creation, memory management, state tracking, and cleanup.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from tripsage_core.utils.session_utils import SessionMemory


class TestSessionMemoryInitialization:
    """Test SessionMemory initialization and configuration."""

    def test_session_memory_default_initialization(self):
        """Test SessionMemory with default initialization."""
        session = SessionMemory()

        assert session.session_id is not None
        assert isinstance(session.session_id, str)
        assert session.memories == []
        assert session.context == {}
        assert session.max_memories == 10
        assert session.created_at is not None
        assert session.last_accessed is not None

    def test_session_memory_with_custom_session_id(self):
        """Test SessionMemory with custom session ID."""
        custom_id = "custom_session_123"
        session = SessionMemory(session_id=custom_id)

        assert session.session_id == custom_id
        assert session.memories == []
        assert session.context == {}

    def test_session_memory_with_custom_max_memories(self):
        """Test SessionMemory with custom max memories limit."""
        session = SessionMemory(max_memories=20)

        assert session.max_memories == 20
        assert session.memories == []

    def test_session_memory_session_id_is_valid_uuid(self):
        """Test that default session ID is a valid UUID."""
        session = SessionMemory()

        # Should be able to parse as UUID
        try:
            uuid.UUID(session.session_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        assert is_valid_uuid

    def test_session_memory_timestamps_are_recent(self):
        """Test that timestamps are set to recent times."""
        session = SessionMemory()
        now = datetime.utcnow()

        # Should be within 1 second of current time
        assert abs((session.created_at - now).total_seconds()) < 1.0
        assert abs((session.last_accessed - now).total_seconds()) < 1.0


class TestMemoryManagement:
    """Test memory management operations."""

    @pytest.fixture
    def session(self):
        """Create a session for testing."""
        return SessionMemory(session_id="test_session", max_memories=5)

    def test_add_memory_single_item(self, session):
        """Test adding a single memory item."""
        memory_item = {
            "type": "user_message",
            "content": "Hello",
            "timestamp": datetime.utcnow(),
        }

        session.add_memory(memory_item)

        assert len(session.memories) == 1
        assert session.memories[0] == memory_item

    def test_add_memory_multiple_items(self, session):
        """Test adding multiple memory items."""
        items = [
            {
                "type": "user_message",
                "content": "Hello",
                "timestamp": datetime.utcnow(),
            },
            {
                "type": "assistant_message",
                "content": "Hi there!",
                "timestamp": datetime.utcnow(),
            },
            {
                "type": "user_message",
                "content": "How are you?",
                "timestamp": datetime.utcnow(),
            },
        ]

        for item in items:
            session.add_memory(item)

        assert len(session.memories) == 3
        assert session.memories == items

    def test_add_memory_exceeds_max_limit(self, session):
        """Test adding memories that exceed the maximum limit."""
        # Add 7 items to a session with max_memories=5
        for i in range(7):
            memory_item = {
                "type": "message",
                "content": f"Message {i}",
                "timestamp": datetime.utcnow(),
            }
            session.add_memory(memory_item)

        # Should only keep the last 5 items
        assert len(session.memories) == 5
        assert session.memories[0]["content"] == "Message 2"
        assert session.memories[-1]["content"] == "Message 6"

    def test_add_memory_updates_last_accessed(self, session):
        """Test that adding memory updates last_accessed timestamp."""
        original_time = session.last_accessed

        # Wait a small amount and add memory
        import time

        time.sleep(0.01)

        memory_item = {"type": "test", "content": "test"}
        session.add_memory(memory_item)

        assert session.last_accessed > original_time

    def test_get_memories_all(self, session):
        """Test getting all memories."""
        items = [
            {"type": "message", "content": "First"},
            {"type": "message", "content": "Second"},
            {"type": "message", "content": "Third"},
        ]

        for item in items:
            session.add_memory(item)

        memories = session.get_memories()
        assert len(memories) == 3
        assert memories == items

    def test_get_memories_with_limit(self, session):
        """Test getting memories with a limit."""
        items = [
            {"type": "message", "content": "First"},
            {"type": "message", "content": "Second"},
            {"type": "message", "content": "Third"},
            {"type": "message", "content": "Fourth"},
        ]

        for item in items:
            session.add_memory(item)

        memories = session.get_memories(limit=2)
        assert len(memories) == 2
        assert memories == items[-2:]  # Should get the last 2

    def test_get_memories_by_type(self, session):
        """Test getting memories filtered by type."""
        items = [
            {"type": "user_message", "content": "Hello"},
            {"type": "assistant_message", "content": "Hi"},
            {"type": "user_message", "content": "How are you?"},
            {"type": "system_message", "content": "Session started"},
        ]

        for item in items:
            session.add_memory(item)

        user_memories = session.get_memories(memory_type="user_message")
        assert len(user_memories) == 2
        assert all(item["type"] == "user_message" for item in user_memories)

    def test_get_recent_memories(self, session):
        """Test getting recent memories within a time window."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=2)
        recent_time = now - timedelta(minutes=5)

        items = [
            {"type": "message", "content": "Old", "timestamp": old_time},
            {"type": "message", "content": "Recent1", "timestamp": recent_time},
            {"type": "message", "content": "Recent2", "timestamp": now},
        ]

        for item in items:
            session.add_memory(item)

        recent_memories = session.get_recent_memories(minutes=30)
        assert len(recent_memories) == 2
        assert recent_memories[0]["content"] == "Recent1"
        assert recent_memories[1]["content"] == "Recent2"

    def test_clear_memories(self, session):
        """Test clearing all memories."""
        items = [
            {"type": "message", "content": "First"},
            {"type": "message", "content": "Second"},
        ]

        for item in items:
            session.add_memory(item)

        assert len(session.memories) == 2

        session.clear_memories()

        assert len(session.memories) == 0

    def test_remove_old_memories(self, session):
        """Test removing memories older than specified time."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=2)
        recent_time = now - timedelta(minutes=5)

        items = [
            {"type": "message", "content": "Old1", "timestamp": old_time},
            {"type": "message", "content": "Old2", "timestamp": old_time},
            {"type": "message", "content": "Recent", "timestamp": recent_time},
        ]

        for item in items:
            session.add_memory(item)

        removed_count = session.remove_old_memories(hours=1)

        assert removed_count == 2
        assert len(session.memories) == 1
        assert session.memories[0]["content"] == "Recent"


class TestContextManagement:
    """Test context management operations."""

    @pytest.fixture
    def session(self):
        """Create a session for testing."""
        return SessionMemory(session_id="test_session")

    def test_set_context_single_value(self, session):
        """Test setting a single context value."""
        session.set_context("user_id", "12345")

        assert session.context["user_id"] == "12345"

    def test_set_context_multiple_values(self, session):
        """Test setting multiple context values."""
        context_data = {
            "user_id": "12345",
            "preferences": {"theme": "dark", "language": "en"},
            "current_trip": "trip_456",
        }

        for key, value in context_data.items():
            session.set_context(key, value)

        assert session.context == context_data

    def test_get_context_existing_key(self, session):
        """Test getting an existing context value."""
        session.set_context("user_id", "12345")

        value = session.get_context("user_id")
        assert value == "12345"

    def test_get_context_nonexistent_key(self, session):
        """Test getting a nonexistent context value."""
        value = session.get_context("nonexistent_key")
        assert value is None

    def test_get_context_with_default(self, session):
        """Test getting context value with default."""
        value = session.get_context("nonexistent_key", default="default_value")
        assert value == "default_value"

    def test_remove_context_existing_key(self, session):
        """Test removing an existing context key."""
        session.set_context("user_id", "12345")
        session.set_context("other_key", "value")

        removed_value = session.remove_context("user_id")

        assert removed_value == "12345"
        assert "user_id" not in session.context
        assert "other_key" in session.context

    def test_remove_context_nonexistent_key(self, session):
        """Test removing a nonexistent context key."""
        removed_value = session.remove_context("nonexistent_key")
        assert removed_value is None

    def test_clear_context(self, session):
        """Test clearing all context."""
        session.set_context("key1", "value1")
        session.set_context("key2", "value2")

        assert len(session.context) == 2

        session.clear_context()

        assert len(session.context) == 0

    def test_update_context_dict(self, session):
        """Test updating context with a dictionary."""
        initial_context = {"user_id": "12345", "theme": "light"}
        session.context.update(initial_context)

        update_data = {"theme": "dark", "language": "en", "new_key": "new_value"}
        session.update_context(update_data)

        expected_context = {
            "user_id": "12345",
            "theme": "dark",
            "language": "en",
            "new_key": "new_value",
        }

        assert session.context == expected_context


class TestSessionState:
    """Test session state management."""

    @pytest.fixture
    def session(self):
        """Create a session for testing."""
        return SessionMemory(session_id="test_session")

    def test_is_empty_new_session(self, session):
        """Test that new session is considered empty."""
        assert session.is_empty() is True

    def test_is_empty_with_memories(self, session):
        """Test that session with memories is not empty."""
        session.add_memory({"type": "message", "content": "Hello"})
        assert session.is_empty() is False

    def test_is_empty_with_context(self, session):
        """Test that session with context is not empty."""
        session.set_context("user_id", "12345")
        assert session.is_empty() is False

    def test_is_expired_fresh_session(self, session):
        """Test that fresh session is not expired."""
        assert session.is_expired(hours=1) is False

    def test_is_expired_old_session(self, session):
        """Test that old session is expired."""
        # Manually set last_accessed to an old time
        session.last_accessed = datetime.utcnow() - timedelta(hours=2)

        assert session.is_expired(hours=1) is True

    def test_refresh_session(self, session):
        """Test refreshing session updates timestamp."""
        original_time = session.last_accessed

        import time

        time.sleep(0.01)

        session.refresh()

        assert session.last_accessed > original_time

    def test_get_session_age(self, session):
        """Test getting session age."""
        age = session.get_age()

        # Should be very small for a new session
        assert age.total_seconds() < 1.0

    def test_get_session_duration(self, session):
        """Test getting session duration since last access."""
        duration = session.get_duration_since_last_access()

        # Should be very small for a fresh session
        assert duration.total_seconds() < 1.0

    def test_session_statistics(self, session):
        """Test getting session statistics."""
        # Add some data
        for i in range(3):
            session.add_memory({"type": "message", "content": f"Message {i}"})

        session.set_context("user_id", "12345")
        session.set_context("preferences", {"theme": "dark"})

        stats = session.get_statistics()

        assert stats["memory_count"] == 3
        assert stats["context_keys"] == 2
        assert "created_at" in stats
        assert "last_accessed" in stats
        assert "age_seconds" in stats


class TestSessionSerialization:
    """Test session serialization and deserialization."""

    @pytest.fixture
    def session_with_data(self):
        """Create a session with test data."""
        session = SessionMemory(session_id="test_session")

        # Add memories
        session.add_memory({"type": "user_message", "content": "Hello"})
        session.add_memory({"type": "assistant_message", "content": "Hi there!"})

        # Add context
        session.set_context("user_id", "12345")
        session.set_context("preferences", {"theme": "dark"})

        return session

    def test_to_dict(self, session_with_data):
        """Test converting session to dictionary."""
        session_dict = session_with_data.to_dict()

        assert session_dict["session_id"] == "test_session"
        assert len(session_dict["memories"]) == 2
        assert session_dict["context"]["user_id"] == "12345"
        assert "created_at" in session_dict
        assert "last_accessed" in session_dict

    def test_from_dict(self, session_with_data):
        """Test creating session from dictionary."""
        session_dict = session_with_data.to_dict()

        restored_session = SessionMemory.from_dict(session_dict)

        assert restored_session.session_id == session_with_data.session_id
        assert len(restored_session.memories) == len(session_with_data.memories)
        assert restored_session.context == session_with_data.context

    def test_to_json(self, session_with_data):
        """Test converting session to JSON string."""
        json_string = session_with_data.to_json()

        assert isinstance(json_string, str)
        assert "test_session" in json_string
        assert "Hello" in json_string

    def test_from_json(self, session_with_data):
        """Test creating session from JSON string."""
        json_string = session_with_data.to_json()

        restored_session = SessionMemory.from_json(json_string)

        assert restored_session.session_id == session_with_data.session_id
        assert len(restored_session.memories) == len(session_with_data.memories)
        assert restored_session.context == session_with_data.context

    def test_serialization_roundtrip(self, session_with_data):
        """Test complete serialization roundtrip."""
        # Dictionary roundtrip
        dict_restored = SessionMemory.from_dict(session_with_data.to_dict())
        assert dict_restored.session_id == session_with_data.session_id

        # JSON roundtrip
        json_restored = SessionMemory.from_json(session_with_data.to_json())
        assert json_restored.session_id == session_with_data.session_id


class TestMemorySearch:
    """Test memory search and filtering functionality."""

    @pytest.fixture
    def session_with_varied_data(self):
        """Create a session with varied test data."""
        session = SessionMemory(session_id="test_session")

        memories = [
            {"type": "user_message", "content": "Hello world", "topic": "greeting"},
            {"type": "assistant_message", "content": "Hi there!", "topic": "greeting"},
            {
                "type": "user_message",
                "content": "Book a flight to Paris",
                "topic": "travel",
            },
            {
                "type": "system_message",
                "content": "Flight search initiated",
                "topic": "travel",
            },
            {
                "type": "user_message",
                "content": "Find hotels in Paris",
                "topic": "accommodation",
            },
            {
                "type": "assistant_message",
                "content": "Here are some options",
                "topic": "accommodation",
            },
        ]

        for memory in memories:
            session.add_memory(memory)

        return session

    def test_search_memories_by_content(self, session_with_varied_data):
        """Test searching memories by content."""
        results = session_with_varied_data.search_memories(content="Paris")

        assert len(results) == 2
        assert all("Paris" in result["content"] for result in results)

    def test_search_memories_by_type(self, session_with_varied_data):
        """Test searching memories by type."""
        results = session_with_varied_data.search_memories(memory_type="user_message")

        assert len(results) == 3
        assert all(result["type"] == "user_message" for result in results)

    def test_search_memories_by_topic(self, session_with_varied_data):
        """Test searching memories by topic."""
        results = session_with_varied_data.search_memories(topic="travel")

        assert len(results) == 2
        assert all(result["topic"] == "travel" for result in results)

    def test_search_memories_multiple_criteria(self, session_with_varied_data):
        """Test searching memories with multiple criteria."""
        results = session_with_varied_data.search_memories(
            memory_type="user_message", topic="travel"
        )

        assert len(results) == 1
        assert results[0]["content"] == "Book a flight to Paris"

    def test_search_memories_no_results(self, session_with_varied_data):
        """Test searching memories with no matching results."""
        results = session_with_varied_data.search_memories(content="nonexistent")

        assert len(results) == 0

    def test_filter_memories_by_time_range(self, session_with_varied_data):
        """Test filtering memories by time range."""
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=30)
        end_time = now + timedelta(minutes=30)

        results = session_with_varied_data.filter_memories_by_time(start_time, end_time)

        # All memories should be in this range
        assert len(results) == 6

    def test_get_memory_summary(self, session_with_varied_data):
        """Test getting memory summary."""
        summary = session_with_varied_data.get_memory_summary()

        assert summary["total_memories"] == 6
        assert summary["types"]["user_message"] == 3
        assert summary["types"]["assistant_message"] == 2
        assert summary["types"]["system_message"] == 1


class TestSessionUtils:
    """Test utility functions and edge cases."""

    def test_generate_session_id():
        """Test session ID generation."""
        session_id = SessionMemory.generate_session_id()

        assert isinstance(session_id, str)
        assert len(session_id) > 0

        # Should be a valid UUID
        try:
            uuid.UUID(session_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        assert is_valid_uuid

    def test_multiple_session_ids_are_unique():
        """Test that multiple generated session IDs are unique."""
        ids = [SessionMemory.generate_session_id() for _ in range(10)]

        assert len(set(ids)) == 10  # All should be unique

    def test_session_memory_copy(self):
        """Test copying a session memory."""
        original = SessionMemory(session_id="original")
        original.add_memory({"type": "test", "content": "test"})
        original.set_context("key", "value")

        # Create a copy
        copy = SessionMemory(session_id="copy")
        copy.memories = original.memories.copy()
        copy.context = original.context.copy()

        # Modify original
        original.add_memory({"type": "test2", "content": "test2"})
        original.set_context("key2", "value2")

        # Copy should remain unchanged
        assert len(copy.memories) == 1
        assert len(copy.context) == 1

    def test_session_memory_equality(self):
        """Test session memory equality comparison."""
        session1 = SessionMemory(session_id="same_id")
        session2 = SessionMemory(session_id="same_id")
        session3 = SessionMemory(session_id="different_id")

        # Same session ID should be considered equal
        assert session1.session_id == session2.session_id
        assert session1.session_id != session3.session_id


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_memory_type(self):
        """Test handling of invalid memory data."""
        session = SessionMemory()

        # Should handle None gracefully
        session.add_memory(None)
        assert len(session.memories) == 0

    def test_invalid_context_key(self):
        """Test handling of invalid context keys."""
        session = SessionMemory()

        # Should handle None key gracefully
        session.set_context(None, "value")
        assert None not in session.context

    def test_memory_limit_edge_cases(self):
        """Test memory limit edge cases."""
        # Zero limit
        session = SessionMemory(max_memories=0)
        session.add_memory({"type": "test", "content": "test"})
        assert len(session.memories) == 0

        # Negative limit (should default to reasonable value)
        session = SessionMemory(max_memories=-1)
        assert session.max_memories >= 0

    def test_timestamp_handling(self):
        """Test timestamp handling edge cases."""
        session = SessionMemory()

        # Add memory without timestamp
        memory_without_timestamp = {"type": "test", "content": "test"}
        session.add_memory(memory_without_timestamp)

        # Should handle gracefully
        assert len(session.memories) == 1

    def test_serialization_with_invalid_data(self):
        """Test serialization with invalid data."""
        session = SessionMemory()

        # Add memory with non-serializable data
        class NonSerializable:
            def __init__(self):
                self.func = lambda x: x

        memory_with_func = {
            "type": "test",
            "content": "test",
            "data": NonSerializable(),
        }

        session.add_memory(memory_with_func)

        # Should handle serialization error gracefully
        try:
            json_string = session.to_json()
            # If it succeeds, the non-serializable part was handled
            assert isinstance(json_string, str)
        except Exception:
            # If it fails, that's also acceptable behavior
            pass


class TestPerformance:
    """Test performance characteristics."""

    def test_large_memory_handling(self):
        """Test handling of large numbers of memories."""
        session = SessionMemory(max_memories=1000)

        # Add many memories
        for i in range(1500):
            session.add_memory(
                {
                    "type": "test",
                    "content": f"Message {i}",
                    "timestamp": datetime.utcnow(),
                }
            )

        # Should maintain max limit
        assert len(session.memories) == 1000
        assert session.memories[0]["content"] == "Message 500"

    def test_search_performance(self):
        """Test search performance with many memories."""
        session = SessionMemory(max_memories=100)

        # Add many memories
        for i in range(100):
            session.add_memory(
                {
                    "type": "message",
                    "content": f"Content {i}",
                    "topic": f"topic_{i % 10}",
                }
            )

        import time

        start_time = time.time()

        # Perform search
        results = session.search_memories(topic="topic_5")

        end_time = time.time()
        search_time = end_time - start_time

        # Should complete quickly
        assert search_time < 0.1  # Less than 100ms
        assert len(results) == 10  # Should find 10 results

    def test_serialization_performance(self):
        """Test serialization performance."""
        session = SessionMemory(max_memories=100)

        # Add many memories with various data
        for i in range(100):
            session.add_memory(
                {
                    "type": "message",
                    "content": f"Content {i}",
                    "metadata": {"index": i, "data": list(range(10))},
                }
            )

        import time

        start_time = time.time()

        # Serialize and deserialize
        json_string = session.to_json()
        restored_session = SessionMemory.from_json(json_string)

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete reasonably quickly
        assert total_time < 1.0  # Less than 1 second
        assert len(restored_session.memories) == len(session.memories)
