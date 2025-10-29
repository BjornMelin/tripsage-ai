"""Performance smoke tests for API key service operations."""

from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Any, cast

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyDatabaseProtocol,
    ApiKeyService,
    ApiValidationResult,
    ServiceType,
    ValidationStatus,
)


class _TransactionContext:
    """Async context manager representing a database transaction."""

    def __init__(self, row: dict[str, Any]):
        """Initialize the transaction context."""
        self.row = row

    async def __aenter__(self) -> object:
        """Enter the transaction context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the transaction context."""
        return

    def insert(self, *_args: Any, **_kwargs: Any) -> None:
        """Record an insert operation."""
        return

    def delete(self, *_args: Any, **_kwargs: Any) -> None:
        """Record a delete operation."""
        return

    async def execute(self) -> list[list[dict[str, Any]]]:
        """Execute the transaction and return rows."""
        return [[self.row]]


class _PerfDb:
    """In-memory database stub for performance testing."""

    def __init__(self, result: dict[str, Any]):
        """Initialize the performance database."""
        self._result = result

    def transaction(self, user_id: str | None = None) -> object:
        """Create a new transaction context."""
        return _TransactionContext(self._result)

    async def get_user_api_keys(
        self, *_args: Any, **_kwargs: Any
    ) -> list[dict[str, Any]]:
        """Get user keys."""
        return []

    async def get_api_key_by_id(
        self, *_args: Any, **_kwargs: Any
    ) -> dict[str, Any] | None:
        """Get API key by id for a user."""
        return self._result

    async def get_api_key_for_service(
        self, *_args: Any, **_kwargs: Any
    ) -> dict[str, Any] | None:
        """Get API key for service."""
        return None

    async def update_api_key_last_used(self, *_args: Any, **_kwargs: Any) -> None:
        """Update API key last used."""
        return


@pytest.mark.performance
@pytest.mark.perf
@pytest.mark.timeout(0.5)
@pytest.mark.asyncio
async def test_create_api_key_completes_within_latency_budget(
    test_settings: Settings,
) -> None:
    """Assert API key creation stays within the sub-250ms latency budget."""
    now = datetime.now(UTC).isoformat()
    db_result = {
        "id": "perf-key",
        "name": "Perf Key",
        "service": ServiceType.OPENAI.value,
        "description": "",
        "is_valid": True,
        "created_at": now,
        "updated_at": now,
        "expires_at": None,
        "last_used": None,
        "last_validated": now,
        "usage_count": 0,
    }
    db = _PerfDb(db_result)

    request = ApiKeyCreateRequest(
        name="Perf Key",
        service=ServiceType.OPENAI,
        key="sk-perf-1234567890",
    )

    async with ApiKeyService(
        db=cast(ApiKeyDatabaseProtocol, db), cache=None, settings=test_settings
    ) as service:
        validation = ApiValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="ok",
        )

        async def _validate(*_args: Any, **_kwargs: Any) -> ApiValidationResult:
            """Validate API key."""
            return validation

        service.validate_api_key = _validate  # type: ignore[assignment]

        start = datetime.now(UTC)
        await service.create_api_key("perf-user", request)
        elapsed = (datetime.now(UTC) - start).total_seconds()

    assert elapsed < 0.25
