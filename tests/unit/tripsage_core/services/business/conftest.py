"""Common fixtures for business service tests.

This module provides shared fixtures and utilities for testing business services.
Updated for Pydantic v2 and modern testing patterns.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


@pytest.fixture
def mock_database_service():
    """Mock database service for tests."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()

    # Add specific methods used by services
    db.execute_query = AsyncMock()
    db.get_accommodation_listing = AsyncMock()
    db.store_accommodation_search = AsyncMock()
    db.store_accommodation_listing = AsyncMock()
    db.store_accommodation_booking = AsyncMock()
    db.get_accommodation_booking = AsyncMock()
    db.get_accommodation_bookings = AsyncMock()
    db.update_accommodation_booking = AsyncMock()

    db.get_flight_offer = AsyncMock()
    db.store_flight_search = AsyncMock()
    db.store_flight_booking = AsyncMock()
    db.get_flight_booking = AsyncMock()
    db.get_flight_bookings = AsyncMock()
    db.update_flight_booking = AsyncMock()

    db.get_user_by_id = AsyncMock()
    db.get_user_by_email = AsyncMock()
    db.get_user_by_username = AsyncMock()
    db.create_user = AsyncMock()
    db.update_user = AsyncMock()
    db.get_user_with_password = AsyncMock()
    db.get_user_with_password_by_email = AsyncMock()
    db.update_user_password = AsyncMock()

    db.get_file_by_hash = AsyncMock()
    db.store_file = AsyncMock()
    db.get_file = AsyncMock()
    db.update_file = AsyncMock()
    db.delete_file = AsyncMock()
    db.search_files = AsyncMock()
    db.get_file_usage_stats = AsyncMock()

    return db


@pytest.fixture
def mock_cache_service():
    """Mock cache service for tests."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=False)
    cache.ping = AsyncMock(return_value=True)
    cache.connect = AsyncMock()
    cache.disconnect = AsyncMock()
    cache._connected = True
    return cache


@pytest.fixture
def mock_storage_service():
    """Mock storage service for tests."""
    storage = AsyncMock()
    storage.store_file = AsyncMock()
    storage.get_file_content = AsyncMock()
    storage.delete_file = AsyncMock()
    storage.file_exists = AsyncMock(return_value=True)
    return storage


@pytest.fixture
def mock_ai_analysis_service():
    """Mock AI analysis service for tests."""
    ai = AsyncMock()
    ai.analyze_file = AsyncMock()
    ai.extract_text = AsyncMock()
    ai.analyze_image = AsyncMock()
    return ai


@pytest.fixture
def mock_virus_scanner():
    """Mock virus scanner service for tests."""
    scanner = AsyncMock()
    scanner.scan_content = AsyncMock()
    scanner.scan_file = AsyncMock()
    return scanner


@pytest.fixture
def sample_user_id() -> str:
    """Generate a sample user ID."""
    return str(uuid4())


@pytest.fixture
def sample_trip_id() -> str:
    """Generate a sample trip ID."""
    return str(uuid4())


@pytest.fixture
def sample_timestamp() -> datetime:
    """Generate a sample timestamp."""
    return datetime.now(UTC)


@pytest.fixture
def sample_user_data(sample_user_id: str, sample_timestamp: datetime) -> dict[str, Any]:
    """Create sample user data."""
    return {
        "id": sample_user_id,
        "email": "test@example.com",
        "full_name": "Test User",
        "username": "testuser",
        "is_active": True,
        "is_verified": False,
        "created_at": sample_timestamp.isoformat(),
        "updated_at": sample_timestamp.isoformat(),
        "preferences": {},
    }
