"""Performance smoke tests for API key service operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService


class _PerfDb:
    def __init__(self, result: dict[str, Any]):
        """Initialize the performance database."""
        self._result = result

    def transaction(self):
        """Create a new transaction."""

        class _Tx:
            def __init__(self, row: dict[str, Any]):
                """Initialize the transaction."""
                self.row = row

            async def __aenter__(self):
                """Enter the transaction."""
                return self

            async def __aexit__(self, exc_type, exc, tb):
                """Exit the transaction."""
                return False

            def insert(self, *_args, **_kwargs):
                """Record an insert operation."""
                return

            async def execute(self):
                """Execute the transaction."""
                return [[self.row]]

        return _Tx(self._result)

    async def get_user_api_keys(self, *_args, **_kwargs):
        """Get user keys."""
        return []

    async def get_api_key_for_service(self, *_args, **_kwargs):
        """Get API key for service."""
        return

    async def update_api_key_last_used(self, *_args, **_kwargs):
        """Update API key last used."""
        return


@pytest.mark.performance
@pytest.mark.perf
@pytest.mark.timeout(0.5)
@pytest.mark.asyncio
async def test_create_api_key_completes_within_latency_budget(test_settings):
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
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as service:
        validation = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="ok",
        )

        async def _validate(*_args: Any, **_kwargs: Any) -> ValidationResult:
            """Validate API key."""
            return validation

        service.validate_api_key = _validate  # type: ignore[assignment]

        start = datetime.now(UTC)
        await service.create_api_key("perf-user", request)
        elapsed = (datetime.now(UTC) - start).total_seconds()

    assert elapsed < 0.25
