"""Unit tests for the modern API key service core module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace, TracebackType
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from tripsage_core.exceptions import CoreServiceError as ServiceError
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyService,
    ApiValidationResult,
    ServiceHealthStatus,
    ServiceType,
    ValidationStatus,
    get_api_key_service,
)


if TYPE_CHECKING:
    from tripsage_core.config import Settings
    from tripsage_core.services.infrastructure.cache_service import CacheService
    from tripsage_core.services.infrastructure.database_service import DatabaseService


class TransactionRecorder:
    """Record database transaction operations for assertions."""

    def __init__(self) -> None:
        """Initialise buffers for captured operations."""
        self.inserts: list[tuple[str, dict[str, Any]]] = []
        self.deletes: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> TransactionRecorder:
        """Enter the async transaction context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async transaction context."""
        return

    def insert(self, table: str, payload: dict[str, Any]) -> None:
        """Capture an insert executed during the transaction."""
        self.inserts.append((table, payload))

    def delete(self, table: str, criteria: dict[str, Any]) -> None:
        """Capture a delete executed during the transaction."""
        self.deletes.append((table, criteria))

    async def execute(self) -> list[list[dict[str, Any]]]:
        """Return synthetic database results for assertions."""
        if self.inserts:
            return [[self.inserts[-1][1]]]
        return [[{}]]


@pytest.fixture
def stub_settings() -> SimpleNamespace:
    """Provide deterministic settings for the service."""
    secret = Mock()
    secret.get_secret_value.return_value = "unit-test-secret"
    return SimpleNamespace(secret_key=secret, enable_api_key_caching=True)


@pytest.fixture
def stub_cache() -> SimpleNamespace:
    """In-memory cache double."""
    return SimpleNamespace(
        get_json=AsyncMock(return_value=None),
        set_json=AsyncMock(),
        delete_pattern=AsyncMock(),
    )


@pytest.fixture
def stub_db() -> SimpleNamespace:
    """Database double that records transactional operations."""
    db = SimpleNamespace()

    def make_transaction() -> TransactionRecorder:
        recorder = TransactionRecorder()
        db.last_transaction = recorder
        return recorder

    db.transaction = Mock(side_effect=make_transaction)
    db.get_user_api_keys = AsyncMock()
    db.get_api_key_by_id = AsyncMock()
    db.get_api_key_for_service = AsyncMock()
    db.update_api_key_last_used = AsyncMock()
    return db


@pytest.fixture
def api_key_service(
    stub_db: SimpleNamespace,
    stub_cache: SimpleNamespace,
    stub_settings: SimpleNamespace,
) -> ApiKeyService:
    """Instantiate the service under test."""
    service = ApiKeyService(
        db=cast("DatabaseService", stub_db),
        cache=cast("CacheService", stub_cache),
        settings=cast("Settings", stub_settings),
    )
    service.client = cast(
        httpx.AsyncClient,
        SimpleNamespace(get=AsyncMock(), aclose=AsyncMock()),
    )
    return service


@pytest.fixture
def create_request() -> ApiKeyCreateRequest:
    """Build a valid creation payload."""
    return ApiKeyCreateRequest(
        name="OpenAI",
        service=ServiceType.OPENAI,
        key="sk-live-token",
        description="Primary key",
    )


def _db_row(**overrides: Any) -> dict[str, Any]:
    """Create a canonical database row for assertions."""
    now = datetime.now(UTC)
    row = {
        "id": "key-1",
        "name": "OpenAI",
        "service": "openai",
        "description": "Primary key",
        "is_valid": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
        "last_used": None,
        "last_validated": now.isoformat(),
        "usage_count": 0,
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_create_api_key_success_triggers_audit_and_cache_invalidation(
    api_key_service: ApiKeyService,
    stub_db: SimpleNamespace,
    stub_cache: SimpleNamespace,
    create_request: ApiKeyCreateRequest,
) -> None:
    """Ensure key creation validates inputs and emits side effects."""
    validation = ApiValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        service=ServiceType.OPENAI,
        message="ok",
        validated_at=datetime.now(UTC),
    )

    validate_mock = AsyncMock(return_value=validation)
    encrypt_mock = Mock(return_value="encrypted-value")

    with (
        patch.object(api_key_service, "validate_api_key", validate_mock),
        patch.object(api_key_service, "_encrypt_api_key", encrypt_mock),
        patch(
            "tripsage_core.services.business.api_key_service.asyncio.create_task"
        ) as create_task,
        patch.object(
            api_key_service,
            "_db_result_to_response",
            return_value=ApiKeyResponse(**_db_row()),
        ) as response_mock,
    ):
        result = await api_key_service.create_api_key("user-1", create_request)

    assert isinstance(result, ApiKeyResponse)
    validate_mock.assert_awaited_once_with(ServiceType.OPENAI, "sk-live-token")
    assert stub_db.last_transaction.inserts[0][0] == "api_keys"
    assert stub_db.last_transaction.inserts[0][1]["encrypted_key"] == "encrypted-value"
    stub_cache.delete_pattern.assert_awaited_once_with("api_validation:v3:*")
    create_task.assert_called_once()
    response_mock.assert_called_once()


@pytest.mark.asyncio
async def test_create_api_key_wraps_recoverable_error(
    api_key_service: ApiKeyService, create_request: ApiKeyCreateRequest
) -> None:
    """Service should convert recoverable errors into `ServiceError`."""
    with (
        patch.object(
            api_key_service,
            "validate_api_key",
            AsyncMock(side_effect=httpx.HTTPError("boom")),
        ),
        pytest.raises(ServiceError),
    ):
        await api_key_service.create_api_key("user-1", create_request)


@pytest.mark.asyncio
async def test_list_user_keys_formats_responses(
    api_key_service: ApiKeyService, stub_db: SimpleNamespace
) -> None:
    """List endpoint returns serialised response models."""
    stub_db.get_user_api_keys.return_value = [_db_row()]

    result = await api_key_service.list_user_keys("user-1")

    assert len(result) == 1
    response = result[0]
    assert isinstance(response, ApiKeyResponse)
    assert ServiceType(response.service) is ServiceType.OPENAI
    assert response.is_expired is False


@pytest.mark.asyncio
async def test_get_key_for_service_skips_expired(
    api_key_service: ApiKeyService, stub_db: SimpleNamespace
) -> None:
    """Expired keys are ignored before decryption."""
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    stub_db.get_api_key_for_service.return_value = {
        "id": "key-1",
        "service": "openai",
        "encrypted_key": "cipher",
        "expires_at": past,
    }

    with patch.object(
        api_key_service,
        "_decrypt_api_key",
        side_effect=AssertionError("should not run"),
    ):
        assert (
            await api_key_service.get_key_for_service("user-1", ServiceType.OPENAI)
            is None
        )


@pytest.mark.asyncio
async def test_get_key_for_service_returns_decrypted_value(
    api_key_service: ApiKeyService,
    stub_db: SimpleNamespace,
) -> None:
    """Fresh keys are decrypted and usage updates scheduled."""
    stub_db.get_api_key_for_service.return_value = {
        "id": "key-1",
        "service": "openai",
        "encrypted_key": "cipher",
        "expires_at": None,
    }

    with (
        patch.object(api_key_service, "_decrypt_api_key", return_value="plain-key"),
        patch(
            "tripsage_core.services.business.api_key_service.asyncio.create_task"
        ) as create_task,
    ):
        value = await api_key_service.get_key_for_service("user-1", ServiceType.OPENAI)

    assert value == "plain-key"
    assert stub_db.update_api_key_last_used.call_args.args == ("key-1",)
    stub_db.update_api_key_last_used.assert_not_awaited()
    create_task.assert_called_once()


@pytest.mark.asyncio
async def test_validate_api_key_returns_cached_result(
    api_key_service: ApiKeyService,
    stub_cache: SimpleNamespace,
) -> None:
    """Cached validation responses should be reused."""
    now = datetime.now(UTC)
    stub_cache.get_json.return_value = {
        "is_valid": True,
        "status": "valid",
        "service": "openai",
        "message": "cached",
        "details": {},
        "latency_ms": 1.2,
        "validated_at": now.isoformat(),
    }

    result = await api_key_service.validate_api_key(ServiceType.OPENAI, "sk-live-token")

    assert result.is_valid is True
    assert ValidationStatus(result.status) is ValidationStatus.VALID
    assert ServiceType(result.service) is ServiceType.OPENAI
    stub_cache.set_json.assert_not_called()


@pytest.mark.asyncio
async def test_validate_api_key_caches_success(
    api_key_service: ApiKeyService, stub_cache: SimpleNamespace
) -> None:
    """Successful validations should be persisted to cache."""
    stub_cache.get_json.return_value = None
    validation = ApiValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        service=ServiceType.OPENAI,
        message="fresh",
        validated_at=datetime.now(UTC),
    )

    with patch.object(
        api_key_service, "_validate_api_key", AsyncMock(return_value=validation)
    ):
        await api_key_service.validate_api_key(ServiceType.OPENAI, "sk-live-token")

    assert stub_cache.set_json.await_args is not None
    _, kwargs = stub_cache.set_json.await_args
    assert kwargs["ttl"] == 300


@pytest.mark.asyncio
async def test_validate_api_key_handles_recoverable_error(
    api_key_service: ApiKeyService,
) -> None:
    """Recoverable validation failures default to service error outputs."""
    with patch.object(
        api_key_service, "_validate_api_key", AsyncMock(side_effect=ValueError("oops"))
    ):
        result = await api_key_service.validate_api_key(
            ServiceType.OPENAI, "sk-live-token"
        )

    assert result.is_valid is False
    assert ValidationStatus(result.status) is ValidationStatus.SERVICE_ERROR


def test_encrypt_decrypt_roundtrip(api_key_service: ApiKeyService) -> None:
    """Round-trip encryption must recover plaintext."""
    ciphertext = api_key_service._encrypt_api_key("plaintext")  # pyright: ignore[reportPrivateUsage]
    assert (
        api_key_service._decrypt_api_key(ciphertext)  # pyright: ignore[reportPrivateUsage]
        == "plaintext"
    )


def test_encrypt_api_key_rejects_empty(api_key_service: ApiKeyService) -> None:
    """Reject empty API key values during encryption."""
    with pytest.raises(ServiceError):
        api_key_service._encrypt_api_key("")  # pyright: ignore[reportPrivateUsage]


def test_decrypt_api_key_invalid_format(api_key_service: ApiKeyService) -> None:
    """Reject malformed ciphertext payloads."""
    with pytest.raises(ServiceError):
        api_key_service._decrypt_api_key("invalid-format")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_delete_api_key_success(
    api_key_service: ApiKeyService,
    stub_db: SimpleNamespace,
    stub_cache: SimpleNamespace,
) -> None:
    """Deleting a key removes records and triggers audits/cache invalidation."""
    stub_db.get_api_key_by_id.return_value = {
        "id": "key-1",
        "user_id": "user-1",
        "service": "openai",
    }

    with patch(
        "tripsage_core.services.business.api_key_service.asyncio.create_task"
    ) as create_task:
        assert await api_key_service.delete_api_key("key-1", "user-1") is True

    assert stub_db.last_transaction.deletes[0][0] == "api_keys"
    stub_cache.delete_pattern.assert_awaited_once_with("api_validation:v3:*")
    create_task.assert_called_once()


@pytest.mark.asyncio
async def test_delete_api_key_missing_returns_false(
    api_key_service: ApiKeyService, stub_db: SimpleNamespace
) -> None:
    """Return False without performing work when the key is absent."""
    stub_db.get_api_key_by_id.return_value = None

    assert await api_key_service.delete_api_key("key-1", "user-1") is False


@pytest.mark.asyncio
async def test_check_service_health_handles_exception(
    api_key_service: ApiKeyService,
) -> None:
    """Map exceptions during health checks to an unhealthy response."""
    with patch.object(
        api_key_service,
        "_check_service_health_generic",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await api_key_service.check_service_health(ServiceType.OPENAI)

    assert ServiceHealthStatus(result.health_status) is ServiceHealthStatus.UNHEALTHY
    assert result.is_valid is None


@pytest.mark.asyncio
async def test_check_all_services_health_collects_errors(
    api_key_service: ApiKeyService,
) -> None:
    """Aggregate per-service health results and downgrade failures."""
    healthy = ApiValidationResult(
        is_valid=None,
        status=None,
        health_status=ServiceHealthStatus.HEALTHY,
        service=ServiceType.OPENAI,
        message="ok",
    )
    degraded = ApiValidationResult(
        is_valid=None,
        status=None,
        health_status=ServiceHealthStatus.DEGRADED,
        service=ServiceType.GOOGLEMAPS,
        message="slow",
    )

    async def side_effect(service: ServiceType) -> ApiValidationResult:
        """Side effect for health check testing."""
        if service is ServiceType.OPENAI:
            return healthy
        if service is ServiceType.WEATHER:
            raise RuntimeError("boom")
        return degraded

    with patch.object(api_key_service, "check_service_health", side_effect=side_effect):
        results = await api_key_service.check_all_services_health()

    assert (
        ServiceHealthStatus(results[ServiceType.OPENAI].health_status)
        is ServiceHealthStatus.HEALTHY
    )
    assert (
        ServiceHealthStatus(results[ServiceType.WEATHER].health_status)
        is ServiceHealthStatus.UNHEALTHY
    )
    assert (
        ServiceHealthStatus(results[ServiceType.GOOGLEMAPS].health_status)
        is ServiceHealthStatus.DEGRADED
    )


@pytest.mark.asyncio
async def test_get_api_key_service_dependency_returns_instance(
    stub_db: SimpleNamespace, stub_cache: SimpleNamespace
) -> None:
    """Dependency factory should supply a configured service instance."""
    service = await get_api_key_service(
        cast("DatabaseService", stub_db),
        cast("CacheService", stub_cache),
    )
    assert isinstance(service, ApiKeyService)
    assert service.db is stub_db
    assert service.cache is stub_cache


def test_validate_request_enforces_min_length() -> None:
    """Enforce minimum key-length validation in the request model."""
    with pytest.raises(ValueError):
        ApiKeyCreateRequest(
            name="too short",
            service=ServiceType.OPENAI,
            key="short",
        )
