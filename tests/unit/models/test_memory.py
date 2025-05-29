"""Tests for memory database models."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List

from pydantic import ValidationError

from tripsage_core.models.db.memory import (
    Memory,
    SessionMemory,
    MemorySearchResult,
    MemoryCreate,
    MemoryUpdate,
)


class TestMemory:
    """Test Memory model."""

    def test_valid_memory(self):
        """Test creating a valid memory."""
        memory_data = {
            "id": uuid4(),
            "user_id": "user_123",
            "memory": "User prefers window seats on flights",
            "metadata": {"preference_type": "flight", "category": "seating"},
            "categories": ["travel_preferences", "flights"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "is_deleted": False,
            "version": 1,
            "hash": "abc123",
            "relevance_score": 1.0,
        }
        memory = Memory(**memory_data)
        
        assert memory.user_id == "user_123"
        assert memory.memory == "User prefers window seats on flights"
        assert memory.is_active is True
        assert memory.relevance_score == 1.0
        assert len(memory.categories) == 2

    def test_memory_content_validation(self):
        """Test memory content validation."""
        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="user_123",
                memory="",  # Empty content
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        assert "Memory content cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="user_123",
                memory="   ",  # Whitespace only
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        assert "Memory content cannot be empty" in str(exc_info.value)

    def test_user_id_validation(self):
        """Test user ID validation."""
        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="",  # Empty user ID
                memory="Test memory",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        assert "User ID cannot be empty" in str(exc_info.value)

    def test_relevance_score_validation(self):
        """Test relevance score validation."""
        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="user_123",
                memory="Test memory",
                relevance_score=1.5,  # Invalid score > 1.0
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        assert "Relevance score must be between 0.0 and 1.0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="user_123",
                memory="Test memory",
                relevance_score=-0.1,  # Invalid score < 0.0
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        assert "Relevance score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_categories_validation(self):
        """Test categories validation and cleaning."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            categories=["Travel", "TRAVEL", "travel", "", "  flights  ", "travel"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        # Should remove duplicates, empty strings, and normalize to lowercase
        assert memory.categories == ["travel", "flights"]

    def test_metadata_validation(self):
        """Test metadata validation."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            metadata=None,  # Should default to empty dict
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert memory.metadata == {}

    def test_add_category(self):
        """Test adding a category."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            categories=["travel"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        memory.add_category("flights")
        assert "flights" in memory.categories
        
        # Adding duplicate should not duplicate
        memory.add_category("flights")
        assert memory.categories.count("flights") == 1

    def test_remove_category(self):
        """Test removing a category."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            categories=["travel", "flights"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        memory.remove_category("flights")
        assert "flights" not in memory.categories
        assert "travel" in memory.categories

    def test_update_metadata(self):
        """Test updating metadata."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            metadata={"key1": "value1"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        memory.update_metadata({"key2": "value2", "key1": "updated_value1"})
        assert memory.metadata["key1"] == "updated_value1"
        assert memory.metadata["key2"] == "value2"

    def test_is_active_property(self):
        """Test is_active property."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            is_deleted=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert memory.is_active is True
        
        memory.is_deleted = True
        assert memory.is_active is False


class TestSessionMemory:
    """Test SessionMemory model."""

    def test_valid_session_memory(self):
        """Test creating a valid session memory."""
        now = datetime.now()
        session_memory_data = {
            "id": uuid4(),
            "session_id": "session_123",
            "user_id": "user_123",
            "message_index": 5,
            "role": "user",
            "content": "I want to book a flight to Paris",
            "metadata": {"intent": "flight_booking", "destination": "Paris"},
            "created_at": now,
            "expires_at": now + timedelta(hours=24),
        }
        session_memory = SessionMemory(**session_memory_data)
        
        assert session_memory.session_id == "session_123"
        assert session_memory.user_id == "user_123"
        assert session_memory.message_index == 5
        assert session_memory.role == "user"

    def test_role_validation(self):
        """Test role validation."""
        with pytest.raises(ValidationError) as exc_info:
            SessionMemory(
                id=uuid4(),
                session_id="session_123",
                user_id="user_123",
                message_index=5,
                role="invalid_role",  # Invalid role
                content="Test content",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
            )
        assert "Role must be one of" in str(exc_info.value)

    def test_content_validation(self):
        """Test content validation."""
        with pytest.raises(ValidationError) as exc_info:
            SessionMemory(
                id=uuid4(),
                session_id="session_123",
                user_id="user_123",
                message_index=5,
                role="user",
                content="",  # Empty content
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
            )
        assert "Content cannot be empty" in str(exc_info.value)

    def test_message_index_validation(self):
        """Test message index validation."""
        with pytest.raises(ValidationError) as exc_info:
            SessionMemory(
                id=uuid4(),
                session_id="session_123",
                user_id="user_123",
                message_index=-1,  # Negative index
                role="user",
                content="Test content",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
            )
        assert "Message index must be non-negative" in str(exc_info.value)

    def test_is_expired_property(self):
        """Test is_expired property."""
        now = datetime.now()
        session_memory = SessionMemory(
            id=uuid4(),
            session_id="session_123",
            user_id="user_123",
            message_index=5,
            role="user",
            content="Test content",
            created_at=now,
            expires_at=now + timedelta(hours=1),  # Expires in 1 hour
        )
        assert session_memory.is_expired is False
        
        # Test with past expiry
        session_memory.expires_at = now - timedelta(hours=1)  # Expired 1 hour ago
        assert session_memory.is_expired is True

    def test_extend_expiry(self):
        """Test extending expiry time."""
        now = datetime.now()
        session_memory = SessionMemory(
            id=uuid4(),
            session_id="session_123",
            user_id="user_123",
            message_index=5,
            role="user",
            content="Test content",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        
        original_expiry = session_memory.expires_at
        session_memory.extend_expiry(24)
        
        # Should extend by 24 hours from now, not from original expiry
        assert session_memory.expires_at > original_expiry


class TestMemorySearchResult:
    """Test MemorySearchResult model."""

    def test_valid_search_result(self):
        """Test creating a valid search result."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        search_result = MemorySearchResult(
            memory=memory,
            similarity=0.85,
            rank=1,
        )
        
        assert search_result.memory == memory
        assert search_result.similarity == 0.85
        assert search_result.rank == 1

    def test_similarity_validation(self):
        """Test similarity score validation."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError) as exc_info:
            MemorySearchResult(
                memory=memory,
                similarity=1.5,  # Invalid similarity > 1.0
                rank=1,
            )
        assert "Similarity score must be between 0.0 and 1.0" in str(exc_info.value)

    def test_rank_validation(self):
        """Test rank validation."""
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError) as exc_info:
            MemorySearchResult(
                memory=memory,
                similarity=0.85,
                rank=0,  # Invalid rank < 1
            )
        assert "Rank must be positive" in str(exc_info.value)


class TestMemoryCreate:
    """Test MemoryCreate model."""

    def test_valid_memory_create(self):
        """Test creating a valid memory creation request."""
        memory_create = MemoryCreate(
            user_id="user_123",
            memory="User prefers window seats",
            metadata={"preference_type": "flight"},
            categories=["travel_preferences"],
            relevance_score=0.9,
        )
        
        assert memory_create.user_id == "user_123"
        assert memory_create.memory == "User prefers window seats"
        assert memory_create.relevance_score == 0.9

    def test_default_values(self):
        """Test default values for optional fields."""
        memory_create = MemoryCreate(
            user_id="user_123",
            memory="Test memory",
        )
        
        assert memory_create.metadata == {}
        assert memory_create.categories == []
        assert memory_create.relevance_score == 1.0


class TestMemoryUpdate:
    """Test MemoryUpdate model."""

    def test_valid_memory_update(self):
        """Test creating a valid memory update request."""
        memory_update = MemoryUpdate(
            memory="Updated memory content",
            metadata={"updated": True},
            categories=["updated_category"],
            relevance_score=0.8,
        )
        
        assert memory_update.memory == "Updated memory content"
        assert memory_update.relevance_score == 0.8

    def test_optional_fields(self):
        """Test that all fields are optional."""
        memory_update = MemoryUpdate()
        
        assert memory_update.memory is None
        assert memory_update.metadata is None
        assert memory_update.categories is None
        assert memory_update.relevance_score is None

    def test_partial_update(self):
        """Test partial update with only some fields."""
        memory_update = MemoryUpdate(
            memory="Updated memory content",
        )
        
        assert memory_update.memory == "Updated memory content"
        assert memory_update.metadata is None
        assert memory_update.categories is None
        assert memory_update.relevance_score is None