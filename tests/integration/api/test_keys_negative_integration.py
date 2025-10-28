"""Integration tests for keys negative branches (400/429/500)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage_core.services.business.api_key_service import ValidationStatus


class _ValidateResult:
    """Validation result stub."""

    def __init__(self, status_val: ValidationStatus, message: str) -> None:
        """Initialize validation result."""
        self.is_valid = False
        self.status = status_val
        self.message = message


class _KeySvc:
    """Key service stub."""

    def __init__(self, result: _ValidateResult) -> None:
        """Initialize key service."""
        self._result = result

    async def validate_key(self, key: str, service: str, user_id: str | None = None):
        """Return a canned validation result used to drive negative branches."""
        return self._result


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_val,expected",
    [
        (ValidationStatus.INVALID, status.HTTP_400_BAD_REQUEST),
        (ValidationStatus.RATE_LIMITED, status.HTTP_429_TOO_MANY_REQUESTS),
        (ValidationStatus.SERVICE_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
async def test_keys_create_negative(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
    status_val: ValidationStatus,
    expected: int,
) -> None:
    """Create returns 400/429/500 based on validation status."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal for DI."""
        return principal

    def _provide_key_service() -> _KeySvc:
        """Provide key service for DI."""
        return _KeySvc(_ValidateResult(status_val, "bad key"))

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_api_key_service] = _provide_key_service  # type: ignore[assignment]

    client = async_client_factory(app)
    payload = {"name": "test", "key": "sk_test", "service": "openai"}
    r = await client.post("/api/keys", json=payload)
    assert r.status_code == expected
