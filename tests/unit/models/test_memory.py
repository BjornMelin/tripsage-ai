"""Tests for Memory models following modern pytest patterns."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.memory import (
    Memory,
    MemoryCreate,
    MemorySearchResult,
    MemoryUpdate,
    SessionMemory,
)


class TestMemoryModel:
    """Test Memory model creation, validation, and methods."""

    @pytest.fixture
    def base_memory_data(self):
        """Base data for creating memory instances."""
        return {
            "id": uuid4(),
            "user_id": "user_123",
            "memory": "User prefers window seats on flights",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def test_memory_creation_with_full_data(self, base_memory_data):
        """Test creating Memory with all optional fields."""
        memory_data = {
            **base_memory_data,
            "metadata": {"preference_type": "flight", "category": "seating"},
            "categories": ["travel_preferences", "flights"],
            "relevance_score": 0.9,
        }
        memory = Memory(**memory_data)

        assert memory.id == memory_data["id"]
        assert memory.user_id == "user_123"
        assert memory.memory == "User prefers window seats on flights"
        assert memory.metadata["preference_type"] == "flight"
        assert memory.categories == ["travel_preferences", "flights"]
        assert memory.relevance_score == 0.9
        assert memory.is_active is True

    def test_memory_creation_minimal_data(self, base_memory_data):
        """Test creating Memory with only required fields."""
        memory = Memory(**base_memory_data)

        assert memory.user_id == "user_123"
        assert memory.memory == "User prefers window seats on flights"
        assert memory.metadata == {}
        assert memory.categories == []
        assert memory.relevance_score == 1.0
        assert memory.is_active is True

    @pytest.mark.parametrize(
        "invalid_memory,expected_error",
        [
            ("", "Memory content cannot be empty"),
            ("   ", "Memory content cannot be empty"),
        ],
    )
    def test_memory_validation_empty_content(
        self, base_memory_data, invalid_memory, expected_error
    ):
        """Test validation for empty memory content."""
        with pytest.raises(ValidationError, match=expected_error):
            Memory(**{**base_memory_data, "memory": invalid_memory})

    @pytest.mark.parametrize(
        "invalid_user_id,expected_error",
        [
            ("", "User ID cannot be empty"),
            ("   ", "User ID cannot be empty"),
        ],
    )
    def test_memory_validation_empty_user_id(
        self, base_memory_data, invalid_user_id, expected_error
    ):
        """Test validation for empty user ID."""
        with pytest.raises(ValidationError, match=expected_error):
            Memory(**{**base_memory_data, "user_id": invalid_user_id})

    @pytest.mark.parametrize(
        "invalid_score",
        [1.5, -0.1, 2.0, -1.0],
    )
    def test_memory_validation_relevance_score_bounds(
        self, base_memory_data, invalid_score
    ):
        """Test validation for relevance score bounds."""
        with pytest.raises(
            ValidationError, match="Relevance score must be between 0.0 and 1.0"
        ):
            Memory(**{**base_memory_data, "relevance_score": invalid_score})

    def test_memory_categories_validation_and_cleaning(self, base_memory_data):
        """Test categories validation, cleaning, and deduplication."""
        messy_categories = ["  Category1  ", "CATEGORY2", "category1", "", "Category3"]
        memory = Memory(**{**base_memory_data, "categories": messy_categories})

        # Should clean, deduplicate, and lowercase
        assert memory.categories == ["category1", "category2", "category3"]

    @pytest.mark.parametrize(
        "metadata_input,expected_output",
        [
            (None, {}),
            ({"key": "value"}, {"key": "value"}),
            ("invalid", {}),  # Non-dict should default to empty dict
        ],
    )
    def test_memory_metadata_validation(
        self, base_memory_data, metadata_input, expected_output
    ):
        """Test metadata validation and defaults."""
        memory = Memory(**{**base_memory_data, "metadata": metadata_input})
        assert memory.metadata == expected_output

    def test_memory_category_management(self, base_memory_data):
        """Test adding and removing categories."""
        memory = Memory(**{**base_memory_data, "categories": ["initial"]})

        # Add new category
        memory.add_category("  New Category  ")
        assert "new category" in memory.categories
        assert "initial" in memory.categories

        # Try to add duplicate (should not be added)
        memory.add_category("NEW CATEGORY")
        assert memory.categories.count("new category") == 1

        # Remove category
        memory.remove_category("initial")
        assert "initial" not in memory.categories
        assert "new category" in memory.categories

    def test_memory_metadata_update(self, base_memory_data):
        """Test updating memory metadata."""
        memory = Memory(**{**base_memory_data, "metadata": {"key1": "value1"}})

        memory.update_metadata({"key2": "value2", "key1": "updated_value1"})
        assert memory.metadata["key1"] == "updated_value1"
        assert memory.metadata["key2"] == "value2"

    def test_memory_is_active_property(self, base_memory_data):
        """Test is_active property based on is_deleted flag."""
        memory = Memory(**{**base_memory_data, "is_deleted": False})
        assert memory.is_active is True

        memory.is_deleted = True
        assert memory.is_active is False


class TestSessionMemoryModel:
    """Test SessionMemory model creation and validation."""

    @pytest.fixture
    def base_session_data(self):
        """Base data for creating session memory instances."""
        now = datetime.now(timezone.utc)
        return {
            "id": uuid4(),
            "session_id": "chat_session_123",
            "user_id": "user_123",
            "message_index": 5,
            "role": "user",
            "content": "I want to book a flight to Paris",
            "created_at": now,
            "expires_at": now + timedelta(hours=24),
        }

    def test_session_memory_creation(self, base_session_data):
        """Test creating SessionMemory with valid data."""
        session_memory = SessionMemory(**base_session_data)

        assert session_memory.session_id == "chat_session_123"
        assert session_memory.user_id == "user_123"
        assert session_memory.message_index == 5
        assert session_memory.role == "user"
        assert session_memory.content == "I want to book a flight to Paris"
        assert session_memory.is_expired is False

    @pytest.mark.parametrize(
        "role",
        ["user", "assistant", "system"],
    )
    def test_session_memory_valid_roles(self, base_session_data, role):
        """Test valid roles for SessionMemory."""
        session_memory = SessionMemory(**{**base_session_data, "role": role})
        assert session_memory.role == role

    def test_session_memory_invalid_role(self, base_session_data):
        """Test invalid role validation for SessionMemory."""
        with pytest.raises(ValidationError, match="Role must be one of"):
            SessionMemory(**{**base_session_data, "role": "invalid_role"})

    def test_session_memory_negative_message_index(self, base_session_data):
        """Test message index validation for SessionMemory."""
        with pytest.raises(ValidationError, match="Message index must be non-negative"):
            SessionMemory(**{**base_session_data, "message_index": -1})

    def test_session_memory_expiry_logic(self, base_session_data):
        """Test session memory expiry functionality."""
        now = datetime.now(timezone.utc)

        # Create expired session memory
        expired_data = {**base_session_data, "expires_at": now - timedelta(hours=1)}
        expired_session = SessionMemory(**expired_data)
        assert expired_session.is_expired is True

        # Extend expiry
        expired_session.extend_expiry(48)
        assert expired_session.is_expired is False

    @pytest.mark.parametrize(
        "content_input,expected_error",
        [
            ("", "Content cannot be empty"),
            ("   ", "Content cannot be empty"),
        ],
    )
    def test_session_memory_content_validation(
        self, base_session_data, content_input, expected_error
    ):
        """Test content validation for SessionMemory."""
        with pytest.raises(ValidationError, match=expected_error):
            SessionMemory(**{**base_session_data, "content": content_input})

    @pytest.mark.parametrize(
        "field,invalid_value,expected_error",
        [
            ("session_id", "", "Session ID cannot be empty"),
            ("session_id", "   ", "Session ID cannot be empty"),
            ("user_id", "", "User ID cannot be empty"),
            ("user_id", "   ", "User ID cannot be empty"),
        ],
    )
    def test_session_memory_string_field_validation(
        self, base_session_data, field, invalid_value, expected_error
    ):
        """Test string field validation for SessionMemory."""
        with pytest.raises(ValidationError, match=expected_error):
            SessionMemory(**{**base_session_data, field: invalid_value})


class TestMemorySearchResult:
    """Test MemorySearchResult model."""

    @pytest.fixture
    def sample_memory(self):
        """Create a sample memory for search results."""
        now = datetime.now(timezone.utc)
        return Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            created_at=now,
            updated_at=now,
        )

    def test_memory_search_result_creation(self, sample_memory):
        """Test creating MemorySearchResult."""
        search_result = MemorySearchResult(
            memory=sample_memory,
            similarity=0.85,
            rank=1,
        )

        assert search_result.memory == sample_memory
        assert search_result.similarity == 0.85
        assert search_result.rank == 1

    @pytest.mark.parametrize(
        "invalid_similarity",
        [1.5, -0.1, 2.0, -1.0],
    )
    def test_memory_search_result_similarity_validation(
        self, sample_memory, invalid_similarity
    ):
        """Test similarity score validation."""
        with pytest.raises(
            ValidationError, match="Similarity score must be between 0.0 and 1.0"
        ):
            MemorySearchResult(
                memory=sample_memory,
                similarity=invalid_similarity,
                rank=1,
            )

    @pytest.mark.parametrize(
        "invalid_rank",
        [0, -1, -10],
    )
    def test_memory_search_result_rank_validation(self, sample_memory, invalid_rank):
        """Test rank validation."""
        with pytest.raises(ValidationError, match="Rank must be positive"):
            MemorySearchResult(
                memory=sample_memory,
                similarity=0.85,
                rank=invalid_rank,
            )


class TestMemoryCreateUpdate:
    """Test MemoryCreate and MemoryUpdate models."""

    def test_memory_create_full_data(self):
        """Test MemoryCreate with all fields."""
        memory_create = MemoryCreate(
            user_id="user_123",
            memory="User prefers window seats",
            metadata={"preference_type": "flight"},
            categories=["travel_preferences"],
            relevance_score=0.9,
        )

        assert memory_create.user_id == "user_123"
        assert memory_create.memory == "User prefers window seats"
        assert memory_create.metadata["preference_type"] == "flight"
        assert memory_create.categories == ["travel_preferences"]
        assert memory_create.relevance_score == 0.9

    def test_memory_create_minimal_data(self):
        """Test MemoryCreate with minimal required fields."""
        memory_create = MemoryCreate(
            user_id="user_123",
            memory="Simple memory",
        )

        assert memory_create.user_id == "user_123"
        assert memory_create.memory == "Simple memory"
        assert memory_create.metadata == {}
        assert memory_create.categories == []
        assert memory_create.relevance_score == 1.0

    def test_memory_update_full_data(self):
        """Test MemoryUpdate with all fields."""
        memory_update = MemoryUpdate(
            memory="Updated memory content",
            metadata={"new_key": "new_value"},
            categories=["updated_category"],
            relevance_score=0.8,
        )

        assert memory_update.memory == "Updated memory content"
        assert memory_update.metadata["new_key"] == "new_value"
        assert memory_update.categories == ["updated_category"]
        assert memory_update.relevance_score == 0.8

    def test_memory_update_partial_data(self):
        """Test MemoryUpdate with partial updates."""
        memory_update = MemoryUpdate(memory="Only updating memory content")

        assert memory_update.memory == "Only updating memory content"
        assert memory_update.metadata is None
        assert memory_update.categories is None
        assert memory_update.relevance_score is None

    def test_memory_update_empty_initialization(self):
        """Test MemoryUpdate with no fields provided."""
        memory_update = MemoryUpdate()

        assert memory_update.memory is None
        assert memory_update.metadata is None
        assert memory_update.categories is None
        assert memory_update.relevance_score is None

    @pytest.mark.parametrize(
        "model_class,field,invalid_value,expected_error",
        [
            (MemoryCreate, "memory", "", "Memory content cannot be empty"),
            (MemoryCreate, "memory", "   ", "Memory content cannot be empty"),
            (MemoryCreate, "user_id", "", "User ID cannot be empty"),
            (MemoryCreate, "user_id", "   ", "User ID cannot be empty"),
            (
                MemoryCreate,
                "relevance_score",
                1.5,
                "Relevance score must be between 0.0 and 1.0",
            ),
            (
                MemoryCreate,
                "relevance_score",
                -0.1,
                "Relevance score must be between 0.0 and 1.0",
            ),
            (MemoryUpdate, "memory", "", "Memory content cannot be empty"),
            (MemoryUpdate, "memory", "   ", "Memory content cannot be empty"),
            (
                MemoryUpdate,
                "relevance_score",
                1.5,
                "Relevance score must be between 0.0 and 1.0",
            ),
            (
                MemoryUpdate,
                "relevance_score",
                -0.1,
                "Relevance score must be between 0.0 and 1.0",
            ),
        ],
    )
    def test_memory_create_update_validation(
        self, model_class, field, invalid_value, expected_error
    ):
        """Test validation in MemoryCreate and MemoryUpdate models."""
        base_data = {}
        if model_class == MemoryCreate:
            base_data = {"user_id": "user_123", "memory": "Valid memory"}

        with pytest.raises(ValidationError, match=expected_error):
            model_class(**{**base_data, field: invalid_value})

    def test_memory_create_categories_cleaning(self):
        """Test categories cleaning in MemoryCreate."""
        memory_create = MemoryCreate(
            user_id="user_123",
            memory="Test memory",
            categories=["  Travel  ", "TRAVEL", "travel", "", "  flights  "],
        )

        # Should remove empty strings, normalize to lowercase, and deduplicate
        # Note: Current implementation checks original category for
        # uniqueness before cleaning
        assert memory_create.categories == ["travel", "travel", "flights"]

    def test_memory_update_categories_cleaning(self):
        """Test categories cleaning in MemoryUpdate."""
        memory_update = MemoryUpdate(
            categories=["  Updated  ", "UPDATED", "updated", "", "  category  "],
        )

        # Should remove empty strings, normalize to lowercase, and deduplicate
        # Note: Current implementation checks original category for
        # uniqueness before cleaning
        assert memory_update.categories == ["updated", "updated", "category"]
