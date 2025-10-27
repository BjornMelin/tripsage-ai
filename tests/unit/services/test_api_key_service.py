"""Unit tests for :mod:`tripsage_core.services.business.api_key_service`."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)
from tripsage_core.services.infrastructure.cache_service import CacheService
from tripsage_core.services.infrastructure.database_service import DatabaseService


def _db_row(**overrides: Any) -> dict[str, Any]:
    """Get a database row for a test API key."""
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "id": str(uuid4()),
        "name": "Test Key",
        "service": ServiceType.OPENAI.value,
        "description": "Key created in tests",
        "is_valid": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": None,
        "last_used": None,
        "last_validated": now.isoformat(),
        "usage_count": 0,
    }
    base.update(overrides)
    return base


def _default_inserts() -> list[tuple[str, dict[str, Any]]]:
    """Return a fresh inserts list for transaction stubs."""
    return []


@dataclass
class _Transaction:
    """Transaction context manager for testing database operations."""

    result: dict[str, Any]
    inserts: list[tuple[str, dict[str, Any]]] = field(default_factory=_default_inserts)

    async def __aenter__(self) -> _Transaction:
        """Enter the transaction context."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        """Exit the transaction context."""
        return

    def insert(self, table: str, data: dict[str, Any]) -> None:
        """Record an insert operation."""
        self.inserts.append((table, data))

    async def execute(self) -> list[list[dict[str, Any]]]:
        """Execute the transaction."""
        return [[self.result]]


class _StubDatabase:
    def __init__(self, transaction_result: dict[str, Any]):
        """Initialize the stub database."""
        self._transaction_result = transaction_result
        self.transaction_log: list[tuple[str, dict[str, Any]]] = []
        self.last_used_updates: list[str] = []

        async def _default_list(_user_id: str) -> list[dict[str, Any]]:
            """Default list operation."""
            return []

        async def _default_lookup(*_args: Any, **_kwargs: Any) -> dict[str, Any] | None:
            """Default lookup operation."""
            return None

        async def _update_last_used(key_id: str) -> None:
            """Record last-used updates invoked by the service."""
            self.last_used_updates.append(key_id)

        self.get_user_api_keys = _default_list  # type: ignore[assignment]
        self.get_api_key_by_id = _default_lookup  # type: ignore[assignment]
        self.get_api_key_for_service = _default_lookup  # type: ignore[assignment]
        self.update_api_key_last_used = _update_last_used  # type: ignore[assignment]

    def transaction(self) -> _Transaction:
        """Create a new transaction."""
        tx = _Transaction(self._transaction_result)

        def _record(table: str, data: dict[str, Any]) -> None:
            """Record an insert operation."""
            self.transaction_log.append((table, data))
            tx.inserts.append((table, data))

        tx.insert = _record  # type: ignore[assignment]
        return tx


class _StubCache:
    """In-memory async cache stub compatible with the service contract."""

    def __init__(self) -> None:
        self.storage: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, dict[str, Any]]] = []

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def set(self, key: str, value: str, **kwargs: Any) -> None:
        self.storage[key] = value
        self.set_calls.append((key, value, kwargs))


@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip(test_settings: Settings) -> None:
    """Round-trip encryption should recover the original key value."""
    db = _StubDatabase(transaction_result=_db_row())
    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        secret = "sk-test-key"
        encrypted = service._encrypt_api_key(secret)  # pyright: ignore[reportPrivateUsage]
        assert encrypted != secret
        assert service._decrypt_api_key(encrypted) == secret  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_create_api_key_persists_record(test_settings: Settings) -> None:
    """Successful creation should persist audit and key records."""
    db_row = _db_row(name="Example Key")
    db = _StubDatabase(transaction_result=db_row)
    request = ApiKeyCreateRequest(
        name="Example Key",
        service=ServiceType.OPENAI,
        key="sk-example-123456789",
        description="Integration key",
    )

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        validation = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="valid",
        )

        async def _audit(*_args: Any, **_kwargs: Any) -> None:
            """Audit key creation."""
            return

        cast(Any, service)._audit_key_creation = _audit

        async def _validate(*_args: Any, **_kwargs: Any) -> ValidationResult:
            """Validate API key."""
            return validation

        service.validate_api_key = _validate  # type: ignore[assignment]

        result = await service.create_api_key("user-123", request)

    assert isinstance(result, ApiKeyResponse)
    assert result.name == "Example Key"
    assert result.service == ServiceType.OPENAI
    # Ensure transaction recorded inserts into expected tables
    inserted_tables = {table for table, _ in db.transaction_log}
    assert inserted_tables == {"api_keys", "api_key_usage_logs"}


@pytest.mark.asyncio
async def test_get_key_for_service_handles_expiration(test_settings: Settings) -> None:
    """Expired keys must return ``None`` without raising errors."""
    db = _StubDatabase(transaction_result=_db_row())
    expired = _db_row(
        encrypted_key="placeholder",
        expires_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
    )

    async def _expired(*_args: Any, **_kwargs: Any) -> dict[str, Any] | None:
        """Get expired key."""
        return expired

    db.get_api_key_for_service = _expired  # type: ignore[assignment]

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        decrypted = await service.get_key_for_service("user", ServiceType.OPENAI)

    assert decrypted is None


@pytest.mark.asyncio
async def test_list_user_keys_coerces_db_results(test_settings: Settings) -> None:
    """Database rows should be coerced into response models when listed."""
    items = [_db_row(id=str(uuid4()), name=f"Key {i}") for i in range(2)]
    db = _StubDatabase(transaction_result=_db_row())

    async def _list(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        """List user keys."""
        return items

    db.get_user_api_keys = _list  # type: ignore[assignment]

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        results = await service.list_user_keys("user-123")

    assert [item.name for item in results] == ["Key 0", "Key 1"]


@pytest.mark.asyncio
async def test_get_key_for_service_returns_decrypted_value_and_tracks_usage(
    test_settings: Settings,
) -> None:
    """Fetching a service key should decrypt it and record last-used metadata."""
    db_row = _db_row()
    db = _StubDatabase(transaction_result=db_row)

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        encrypted = service._encrypt_api_key("sk-live-secret")  # pyright: ignore[reportPrivateUsage]

        async def _lookup(*_args: Any, **_kwargs: Any) -> dict[str, Any] | None:
            return _db_row(id=db_row["id"], encrypted_key=encrypted)

        db.get_api_key_for_service = _lookup  # type: ignore[assignment]

        decrypted = await service.get_key_for_service("user-123", ServiceType.OPENAI)
        await asyncio.sleep(0)

    assert decrypted == "sk-live-secret"
    assert db.last_used_updates == [db_row["id"]]


@pytest.mark.asyncio
async def test_get_service_value_accepts_strings(test_settings: Settings) -> None:
    """The helper should normalize both enum inputs and plain strings."""
    db = _StubDatabase(transaction_result=_db_row())

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        assert cast(Any, service)._get_service_value(ServiceType.OPENAI) == "openai"
        assert (
            cast(Any, service)._get_service_value("custom-service") == "custom-service"
        )


@pytest.mark.asyncio
async def test_validate_api_key_returns_cached_result(test_settings: Settings) -> None:
    """Cached validation results should short-circuit external validation."""
    cache = _StubCache()
    api_key = "sk-cached-xyz"
    cache_hash = hashlib.sha256(f"openai:{api_key}".encode()).hexdigest()
    cache.storage[f"api_validation:v3:{cache_hash}"] = ValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        service=ServiceType.OPENAI,
        message="cached",
    ).model_dump_json()

    db = _StubDatabase(transaction_result=_db_row())

    async with ApiKeyService(
        db=cast(DatabaseService, db),
        cache=cast(CacheService, cache),
        settings=test_settings,
    ) as service:

        async def _fail(*_args: Any, **_kwargs: Any) -> ValidationResult:
            raise AssertionError("Validation should use cached data")

        cast(Any, service)._validate_openai_key = _fail

        result = await service.validate_api_key(ServiceType.OPENAI, api_key)

    assert ValidationStatus(result.status) is ValidationStatus.VALID
    assert result.message == "cached"


@pytest.mark.asyncio
async def test_validate_api_key_caches_successful_result(
    test_settings: Settings,
) -> None:
    """Successful validation responses should be cached for reuse."""
    cache = _StubCache()
    db = _StubDatabase(transaction_result=_db_row())
    api_key = "sk-cache-me"

    async with ApiKeyService(
        db=cast(DatabaseService, db),
        cache=cast(CacheService, cache),
        settings=test_settings,
    ) as service:
        validation = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="ok",
        )

        async def _validate(*_args: Any, **_kwargs: Any) -> ValidationResult:
            return validation

        cast(Any, service)._validate_openai_key = _validate

        await service.validate_api_key(ServiceType.OPENAI, api_key)

    expected_hash = hashlib.sha256(f"openai:{api_key}".encode()).hexdigest()
    cache_key = f"api_validation:v3:{expected_hash}"
    assert cache_key in cache.storage
    assert "ok" in cache.storage[cache_key]
