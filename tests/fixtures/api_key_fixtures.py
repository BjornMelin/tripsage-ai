"""Modern reusable fixtures for API key testing.

This module provides fixtures following 2025 best practices
for async testing, property-based testing, and dependency injection.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import strategies as st

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.api_keys import (
    ApiKeyCreate,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
)
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)
from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
)


# Hypothesis strategies for property-based testing
API_KEY_STRATEGIES = {
    "openai": st.text(min_size=20, max_size=100).map(lambda x: f"sk-{x}"),
    "google": st.text(min_size=20, max_size=100).map(lambda x: f"AIza{x}"),
    "weather": st.text(min_size=20, max_size=100),
    "generic": st.text(min_size=10, max_size=200),
}

SERVICE_TYPES = st.sampled_from(list(ServiceType))
USER_IDS = st.uuids().map(str)
KEY_NAMES = st.text(min_size=1, max_size=100).filter(str.strip)
DESCRIPTIONS = st.text(min_size=0, max_size=500)
TIMESTAMPS = st.datetimes(
    min_value=datetime(2020, 1, 1, tzinfo=UTC),
    max_value=datetime(2030, 12, 31, tzinfo=UTC),
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_key_id():
    """Generate a sample key ID."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_principal():
    """Create mock authenticated principal."""
    return Principal(
        id="test_user_123",
        type="user",
        email="test@tripsage.com",
        auth_method="jwt",
    )


@pytest.fixture
def multiple_principals():
    """Create multiple principals for concurrent testing."""
    return [
        Principal(
            id=f"user_{i}",
            type="user",
            email=f"user{i}@tripsage.com",
            auth_method="jwt",
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_api_key_create():
    """Create sample API key creation request."""
    return ApiKeyCreate(
        service="openai",
        key="sk-test_key_for_unit_testing_12345",
        name="Test OpenAI Key",
        description="Test key for unit testing",
    )


@pytest.fixture
def sample_api_key_create_request():
    """Create sample API key creation request for service layer."""
    return ApiKeyCreateRequest(
        name="Test OpenAI Key",
        service=ServiceType.OPENAI,
        key_value="sk-test_key_for_unit_testing_12345",
        description="Test key for unit testing",
    )


@pytest.fixture
def sample_api_key_response():
    """Create sample API key response."""
    return ApiKeyResponse(
        id=str(uuid.uuid4()),
        name="Test OpenAI Key",
        service=ServiceType.OPENAI,
        description="Test key for unit testing",
        is_valid=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=365),
        last_used=None,
        last_validated=datetime.now(UTC),
        usage_count=0,
    )


@pytest.fixture
def multiple_api_key_responses():
    """Create multiple API key responses for bulk testing."""
    base_time = datetime.now(UTC)
    return [
        ApiKeyResponse(
            id=str(uuid.uuid4()),
            name=f"Test Key {i}",
            service=ServiceType.OPENAI,
            description=f"Test key {i} for bulk testing",
            is_valid=i % 2 == 0,  # Alternate valid/invalid
            created_at=base_time + timedelta(hours=i),
            updated_at=base_time + timedelta(hours=i),
            expires_at=base_time + timedelta(days=365),
            last_used=None if i % 3 == 0 else base_time + timedelta(hours=i),
            last_validated=base_time + timedelta(hours=i),
            usage_count=i * 10,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_validation_result():
    """Create sample validation result."""
    return ValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        service=ServiceType.OPENAI,
        message="Key validation successful",
    )


@pytest.fixture
def validation_results_various():
    """Create various validation results for testing."""
    return {
        "valid": ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="Key is valid and functional",
        ),
        "invalid": ValidationResult(
            is_valid=False,
            status=ValidationStatus.INVALID,
            service=ServiceType.OPENAI,
            message="Invalid API key format or credentials",
        ),
        "format_error": ValidationResult(
            is_valid=False,
            status=ValidationStatus.FORMAT_ERROR,
            service=ServiceType.OPENAI,
            message="Key format does not match expected pattern",
        ),
        "rate_limited": ValidationResult(
            is_valid=False,
            status=ValidationStatus.RATE_LIMITED,
            service=ServiceType.OPENAI,
            message="Rate limit exceeded for validation requests",
        ),
        "service_error": ValidationResult(
            is_valid=False,
            status=ValidationStatus.SERVICE_ERROR,
            service=ServiceType.OPENAI,
            message="External service unavailable for validation",
        ),
    }


@pytest.fixture
def sample_db_result():
    """Create sample database result."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": "test_user_123",
        "name": "Test OpenAI Key",
        "service": "openai",
        "encrypted_key": "encrypted_test_key_data",
        "description": "Test key for unit testing",
        "is_valid": True,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
        "last_used": None,
        "last_validated": datetime.now(UTC).isoformat(),
        "usage_count": 0,
    }


@pytest.fixture
def multiple_db_results():
    """Create multiple database results for bulk testing."""
    base_time = datetime.now(UTC)
    return [
        {
            "id": str(uuid.uuid4()),
            "user_id": "test_user_123",
            "name": f"Test Key {i}",
            "service": "openai",
            "encrypted_key": f"encrypted_test_key_data_{i}",
            "description": f"Test key {i} for bulk testing",
            "is_valid": i % 2 == 0,
            "created_at": (base_time + timedelta(hours=i)).isoformat(),
            "updated_at": (base_time + timedelta(hours=i)).isoformat(),
            "expires_at": (base_time + timedelta(days=365)).isoformat(),
            "last_used": None
            if i % 3 == 0
            else (base_time + timedelta(hours=i)).isoformat(),
            "last_validated": (base_time + timedelta(hours=i)).isoformat(),
            "usage_count": i * 10,
        }
        for i in range(1, 6)
    ]


@pytest.fixture
async def mock_api_key_service():
    """Create mock API key service."""
    service = MagicMock(spec=ApiKeyService)

    # Configure async methods
    service.initialize = AsyncMock()
    service.create_key = AsyncMock()
    service.get_key = AsyncMock()
    service.list_user_keys = AsyncMock(return_value=[])
    service.delete_key = AsyncMock(return_value=True)
    service.validate_api_key = AsyncMock()
    service.rotate_key = AsyncMock()
    service.check_health = AsyncMock()
    service.bulk_health_check = AsyncMock(return_value=[])
    service.monitor_key = AsyncMock(return_value={})

    # Configure internal methods
    service._encrypt_key = MagicMock(return_value="encrypted_data")
    service._decrypt_key = MagicMock(return_value="decrypted_key")
    service._is_rate_limited = AsyncMock(return_value=False)
    service._log_usage = AsyncMock()
    service._cache_validation_result = AsyncMock()
    service._get_cached_validation = AsyncMock(return_value=None)

    await service.initialize()
    return service


@pytest.fixture
async def mock_key_monitoring_service():
    """Create mock key monitoring service."""
    service = MagicMock(spec=KeyMonitoringService)

    # Configure async methods
    service.get_audit_log = AsyncMock(return_value=[])
    service.get_metrics = AsyncMock(return_value={})
    service.track_usage = AsyncMock()
    service.track_validation = AsyncMock()
    service.get_health_status = AsyncMock(return_value="healthy")

    return service


@pytest.fixture
def mock_database_service():
    """Create mock database service for testing."""
    db = AsyncMock()

    # Configure common database operations
    db.create_api_key = AsyncMock()
    db.get_api_key = AsyncMock(return_value=None)
    db.list_user_keys = AsyncMock(return_value=[])
    db.update_api_key = AsyncMock()
    db.delete_api_key = AsyncMock(return_value=True)
    db.log_api_key_usage = AsyncMock()

    return db


@pytest.fixture
def mock_cache_service():
    """Create mock cache service for testing."""
    cache = AsyncMock()

    # Configure common cache operations
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.get_json = AsyncMock(return_value=None)
    cache.set_json = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=False)
    cache.expire = AsyncMock(return_value=True)

    return cache


@pytest.fixture
def mock_audit_service():
    """Create mock audit service for testing."""
    audit = AsyncMock()

    # Configure audit operations
    audit.log_operation = AsyncMock()
    audit.log_access = AsyncMock()
    audit.log_error = AsyncMock()
    audit.get_logs = AsyncMock(return_value=[])

    return audit


@pytest.fixture
async def api_key_service_with_mocks(
    mock_database_service,
    mock_cache_service,
    mock_audit_service,
):
    """Create API key service with all mocked dependencies."""
    service = ApiKeyService()
    service.db = mock_database_service
    service.cache = mock_cache_service
    service.audit = mock_audit_service

    await service.initialize()
    return service


@pytest.fixture
def sample_rotate_request():
    """Create sample key rotation request."""
    return ApiKeyRotateRequest(new_key="sk-rotated_key_for_testing_67890")


@pytest.fixture
def sample_validate_request():
    """Create sample key validation request."""
    return ApiKeyValidateRequest(
        service="openai",
        key="sk-validate_test_key_12345",
        save=False,
    )


@pytest.fixture
def monitoring_data_samples():
    """Create sample monitoring data."""
    base_time = datetime.now(UTC)
    return {
        "healthy": {
            "last_check": base_time.isoformat(),
            "status": "healthy",
            "response_time": 120,
            "success_rate": 0.98,
            "error_count": 1,
            "total_requests": 50,
        },
        "unhealthy": {
            "last_check": base_time.isoformat(),
            "status": "unhealthy",
            "response_time": 5000,
            "success_rate": 0.45,
            "error_count": 25,
            "total_requests": 50,
        },
        "unknown": {
            "last_check": (base_time - timedelta(hours=24)).isoformat(),
            "status": "unknown",
            "response_time": None,
            "success_rate": None,
            "error_count": 0,
            "total_requests": 0,
        },
    }


@pytest.fixture
def audit_log_samples():
    """Create sample audit log entries."""
    base_time = datetime.now(UTC)
    return [
        {
            "id": str(uuid.uuid4()),
            "timestamp": (base_time - timedelta(hours=i)).isoformat(),
            "user_id": "test_user_123",
            "action": action,
            "resource_type": "api_key",
            "resource_id": str(uuid.uuid4()),
            "details": {"service": "openai", "operation": action},
            "success": True,
        }
        for i, action in enumerate(
            [
                "key_created",
                "key_validated",
                "key_rotated",
                "key_deleted",
                "key_health_checked",
            ]
        )
    ]


@pytest.fixture
def error_scenarios():
    """Create various error scenarios for testing."""
    return {
        "network_timeout": TimeoutError("Network request timeout"),
        "connection_error": ConnectionError("Failed to connect to external service"),
        "http_error": Exception("HTTP 500 Internal Server Error"),
        "validation_error": ValueError("Invalid key format"),
        "database_error": Exception("Database connection failed"),
        "cache_error": Exception("Redis connection timeout"),
        "rate_limit_error": Exception("Rate limit exceeded"),
    }


@pytest.fixture
def performance_test_data():
    """Create data for performance testing."""
    return {
        "small_batch": [f"sk-test_key_{i}" for i in range(10)],
        "medium_batch": [f"sk-test_key_{i}" for i in range(100)],
        "large_batch": [f"sk-test_key_{i}" for i in range(1000)],
        "concurrent_users": [f"user_{i}" for i in range(20)],
    }


@pytest.fixture
def security_test_inputs():
    """Create inputs for security testing."""
    return {
        "sql_injection": "'; DROP TABLE api_keys; --",
        "xss_script": "<script>alert('xss')</script>",
        "path_traversal": "../../etc/passwd",
        "null_bytes": "test\x00key",
        "unicode_normalization": "\u0041\u0301",  # À using combining character
        "very_long_input": "x" * 10000,
        "binary_data": b"\x00\x01\x02\x03\x04",
        "emoji_unicode": "🔑🚀🌟💫",
    }


# Property-based testing strategies as fixtures
@pytest.fixture
def api_key_strategies():
    """Provide Hypothesis strategies for API keys."""
    return API_KEY_STRATEGIES


@pytest.fixture
def service_type_strategy():
    """Provide Hypothesis strategy for service types."""
    return SERVICE_TYPES


@pytest.fixture
def user_id_strategy():
    """Provide Hypothesis strategy for user IDs."""
    return USER_IDS


@pytest.fixture
def key_name_strategy():
    """Provide Hypothesis strategy for key names."""
    return KEY_NAMES


@pytest.fixture
def description_strategy():
    """Provide Hypothesis strategy for descriptions."""
    return DESCRIPTIONS


@pytest.fixture
def timestamp_strategy():
    """Provide Hypothesis strategy for timestamps."""
    return TIMESTAMPS
