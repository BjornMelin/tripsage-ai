"""Tests for consolidated database models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.models.db import (
    ApiKeyDB,
    ChatMessageDB,
    ChatSessionDB,
    Memory,
    Trip,
    TripStatus,
    TripType,
    User,
    UserRole,
)


class TestConsolidatedModelsImport:
    """Test that all models can be imported from the consolidated location."""

    def test_import_all_models(self):
        """Test that all models can be imported successfully."""
        # Test user models
        assert User is not None
        assert UserRole is not None

        # Test trip models
        assert Trip is not None
        assert TripStatus is not None
        assert TripType is not None

        # Test API key models
        assert ApiKeyDB is not None

        # Test chat models
        assert ChatSessionDB is not None
        assert ChatMessageDB is not None

        # Test memory models
        assert Memory is not None

    def test_user_model_functionality(self):
        """Test User model basic functionality."""
        user = User(
            id=1,
            name="Test User",
            email="test@example.com",
            role=UserRole.USER,
            is_admin=False,
            is_disabled=False,
        )

        assert user.id == 1
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.display_name == "Test User"

    def test_user_preferences(self):
        """Test User preferences functionality."""
        user = User(
            id=1,
            name="Test User",
            email="test@example.com",
        )

        # Test default preferences
        prefs = user.full_preferences
        assert prefs["theme"] == "light"
        assert prefs["currency"] == "USD"
        assert prefs["notifications_enabled"] is True

        # Test updating preferences
        user.update_preferences({"theme": "dark", "currency": "EUR"})
        updated_prefs = user.full_preferences
        assert updated_prefs["theme"] == "dark"
        assert updated_prefs["currency"] == "EUR"

    def test_trip_model_functionality(self):
        """Test Trip model basic functionality."""
        trip = Trip(
            id=1,
            name="Paris Vacation",
            start_date="2025-06-01",
            end_date="2025-06-10",
            destination="Paris, France",
            budget=2000.0,
            travelers=2,
            status=TripStatus.PLANNING,
            trip_type=TripType.LEISURE,
        )

        assert trip.id == 1
        assert trip.name == "Paris Vacation"
        assert trip.destination == "Paris, France"
        assert trip.budget == 2000.0
        assert trip.travelers == 2
        assert trip.status == TripStatus.PLANNING

    def test_api_key_model_functionality(self):
        """Test ApiKey model basic functionality."""
        now = datetime.now()
        api_key = ApiKeyDB(
            id=uuid4(),
            user_id=1,
            name="OpenAI API Key",
            service="openai",
            encrypted_key="encrypted_key_value",
            description="API key for OpenAI services",
            created_at=now,
            updated_at=now,
            is_active=True,
        )

        assert api_key.user_id == 1
        assert api_key.name == "OpenAI API Key"
        assert api_key.service == "openai"
        assert api_key.is_usable() is True  # Active and not expired

    def test_chat_models_functionality(self):
        """Test Chat models basic functionality."""
        now = datetime.now()

        # Test ChatSession
        session = ChatSessionDB(
            id=uuid4(),
            user_id=1,
            created_at=now,
            updated_at=now,
            metadata={"context": "travel_planning"},
        )

        assert session.user_id == 1
        assert session.metadata["context"] == "travel_planning"

        # Test ChatMessage
        message = ChatMessageDB(
            id=1,
            session_id=session.id,
            role="user",
            content="I want to plan a trip to Japan",
            created_at=now,
            metadata={"intent": "trip_planning"},
        )

        assert message.session_id == session.id
        assert message.role == "user"
        assert message.content == "I want to plan a trip to Japan"

    def test_memory_model_functionality(self):
        """Test Memory model basic functionality."""
        now = datetime.now()
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="User prefers flights with window seats",
            metadata={"preference_type": "flight", "category": "seating"},
            categories=["travel_preferences", "flights"],
            created_at=now,
            updated_at=now,
            relevance_score=0.9,
        )

        assert memory.user_id == "user_123"
        assert memory.memory == "User prefers flights with window seats"
        assert memory.relevance_score == 0.9
        assert memory.is_active is True
        assert "travel_preferences" in memory.categories


class TestModelValidation:
    """Test validation across consolidated models."""

    def test_user_email_validation(self):
        """Test User email validation."""
        # Valid email
        user = User(email="test@example.com")
        assert user.email == "test@example.com"

        # Email should be lowercased
        user_upper = User(email="TEST@EXAMPLE.COM")
        assert user_upper.email == "test@example.com"

    def test_api_key_service_validation(self):
        """Test ApiKey service validation."""
        now = datetime.now()

        # Valid service name
        api_key = ApiKeyDB(
            id=uuid4(),
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_key",
            created_at=now,
            updated_at=now,
        )
        assert api_key.service == "openai"

        # Invalid service name with spaces
        with pytest.raises(ValidationError) as exc_info:
            ApiKeyDB(
                id=uuid4(),
                user_id=1,
                name="Test Key",
                service="open ai",  # Invalid: contains space
                encrypted_key="encrypted_key",
                created_at=now,
                updated_at=now,
            )
        assert "must contain only lowercase letters" in str(exc_info.value)

    def test_chat_message_validation(self):
        """Test ChatMessage validation."""
        now = datetime.now()
        session_id = uuid4()

        # Valid message
        message = ChatMessageDB(
            id=1,
            session_id=session_id,
            role="user",
            content="Hello",
            created_at=now,
        )
        assert message.role == "user"

        # Invalid role
        with pytest.raises(ValidationError) as exc_info:
            ChatMessageDB(
                id=1,
                session_id=session_id,
                role="invalid_role",
                content="Hello",
                created_at=now,
            )
        assert "Role must be one of" in str(exc_info.value)

        # Content too long (32KB limit)
        with pytest.raises(ValidationError) as exc_info:
            ChatMessageDB(
                id=1,
                session_id=session_id,
                role="user",
                content="x" * 32769,  # Exceeds 32KB limit
                created_at=now,
            )
        assert "exceeds 32KB limit" in str(exc_info.value)

    def test_memory_validation(self):
        """Test Memory model validation."""
        now = datetime.now()

        # Valid memory
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Valid memory content",
            created_at=now,
            updated_at=now,
        )
        assert memory.memory == "Valid memory content"

        # Empty memory content
        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="user_123",
                memory="",  # Empty content
                created_at=now,
                updated_at=now,
            )
        assert "Memory content cannot be empty" in str(exc_info.value)

        # Invalid relevance score
        with pytest.raises(ValidationError) as exc_info:
            Memory(
                id=uuid4(),
                user_id="user_123",
                memory="Valid content",
                relevance_score=1.5,  # > 1.0
                created_at=now,
                updated_at=now,
            )
        assert "Relevance score must be between 0.0 and 1.0" in str(exc_info.value)


class TestModelBehavior:
    """Test specific model behaviors and business logic."""

    def test_user_display_name_logic(self):
        """Test User display name logic."""
        # With name
        user_with_name = User(name="John Doe", email="john@example.com")
        assert user_with_name.display_name == "John Doe"

        # Without name but with email
        user_no_name = User(email="jane@example.com")
        assert user_no_name.display_name == "jane@example.com"

        # Without name or email
        user_empty = User()
        assert user_empty.display_name == "Unknown User"

    def test_api_key_expiry_logic(self):
        """Test ApiKey expiry logic."""
        now = datetime.now()

        # Non-expiring key
        key_no_expiry = ApiKeyDB(
            id=uuid4(),
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_key",
            created_at=now,
            updated_at=now,
            expires_at=None,
        )
        assert key_no_expiry.is_expired() is False
        assert key_no_expiry.is_usable() is True

        # Future expiry
        from datetime import timedelta

        key_future_expiry = ApiKeyDB(
            id=uuid4(),
            user_id=1,
            name="Test Key",
            service="openai",
            encrypted_key="encrypted_key",
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=30),
        )
        assert key_future_expiry.is_expired() is False
        assert key_future_expiry.is_usable() is True

    def test_memory_categories_management(self):
        """Test Memory categories management."""
        now = datetime.now()
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            categories=["travel"],
            created_at=now,
            updated_at=now,
        )

        # Add category
        memory.add_category("flights")
        assert "flights" in memory.categories

        # Add duplicate category (should not duplicate)
        memory.add_category("flights")
        assert memory.categories.count("flights") == 1

        # Remove category
        memory.remove_category("travel")
        assert "travel" not in memory.categories
        assert "flights" in memory.categories

    def test_metadata_handling(self):
        """Test metadata handling across models."""
        now = datetime.now()

        # Memory metadata
        memory = Memory(
            id=uuid4(),
            user_id="user_123",
            memory="Test memory",
            metadata={"key1": "value1"},
            created_at=now,
            updated_at=now,
        )

        memory.update_metadata({"key2": "value2"})
        assert memory.metadata["key1"] == "value1"
        assert memory.metadata["key2"] == "value2"

        # Chat session metadata
        session = ChatSessionDB(
            id=uuid4(),
            user_id=1,
            created_at=now,
            updated_at=now,
            metadata=None,  # Should default to empty dict
        )
        assert session.metadata == {}
