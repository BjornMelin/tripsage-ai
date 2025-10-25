"""Security-focused tests for authentication helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException, status as http_status

from tripsage.api.core.auth import get_current_user_id


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_requires_bearer_header() -> None:
    """Reject requests missing the required Bearer token header."""
    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(authorization=None)

    assert exc.value.status_code == http_status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_validates_signature(test_settings) -> None:
    """Ensure invalid signatures raise authentication errors."""
    token = jwt.encode(
        {
            "sub": "user-xyz",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "different-secret",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException):
        await get_current_user_id(authorization=f"Bearer {token}")


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_returns_subject(test_settings) -> None:
    """Return the subject claim when the token is valid."""
    token = jwt.encode(
        {
            "sub": "user-123",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        test_settings.database_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )

    user_id = await get_current_user_id(authorization=f"Bearer {token}")
    assert user_id == "user-123"
