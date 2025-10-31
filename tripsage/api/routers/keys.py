"""Vault-backed BYOK endpoints.

This router exposes minimal CRUD endpoints to manage user-provided API keys
for providers: openai, openrouter, anthropic, xai. Secrets are stored in
Supabase Vault; only metadata is stored in ``public.api_keys``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import (
    get_db,
    get_principal_id,
    require_user_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.api_keys import (
    AllowedService,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.supabase_client import get_admin_client


ALLOWED_SERVICES: set[str] = {"openai", "openrouter", "anthropic", "xai"}


router = APIRouter()


def _as_allowed(service: str) -> AllowedService:
    svc = service.lower().strip()
    if svc not in ALLOWED_SERVICES:  # pragma: no cover - defensive
        raise ValueError("unsupported service")
    # Narrow type for response model
    return svc  # type: ignore[return-value]


async def _validate_api_key(service: str, api_key: str) -> tuple[bool, str | None]:
    """Perform a minimal metadata call to verify credentials.

    Returns:
        Tuple of (is_valid, reason)
    """
    svc = service.lower().strip()
    try:
        if svc == "openai":
            from openai import OpenAI  # type: ignore[reportMissingImports]

            client = OpenAI(api_key=api_key)
            _ = client.models.list()
            return True, None
        if svc == "openrouter":
            from openai import OpenAI  # type: ignore[reportMissingImports]

            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            _ = client.models.list()
            return True, None
        if svc == "anthropic":
            from anthropic import Anthropic  # type: ignore[reportMissingImports]

            client = Anthropic(api_key=api_key)
            _ = client.models.list()
            return True, None
        if svc == "xai":
            from openai import OpenAI  # type: ignore[reportMissingImports]

            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            _ = client.models.list()
            return True, None
        return False, "unsupported_service"
    except Exception as exc:  # noqa: BLE001 - surface reason only
        return False, str(exc)


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    principal: Principal = Depends(require_user_principal),
    db: DatabaseService = Depends(get_db),
) -> list[ApiKeyResponse]:
    """Return summary of keys owned by the authenticated user.

    This returns only metadata (no secret material).
    """
    user_id = get_principal_id(principal)
    rows = await db.select(
        "api_keys",
        "service, created_at, last_used",
        filters={"user_id": user_id},
        order_by="service",
        user_id=user_id,
    )
    from datetime import UTC, datetime

    def _as_dt(v: object) -> datetime | None:
        """Convert various datetime representations into a timezone-aware datetime."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:  # pragma: no cover - defensive
                return None
        return None

    resp: list[ApiKeyResponse] = []
    for r in rows:
        service = str(r["service"]).lower().strip()
        # Skip unknown services if any legacy rows exist
        if service not in ALLOWED_SERVICES:
            continue
        resp.append(
            ApiKeyResponse(
                service=_as_allowed(service),
                created_at=_as_dt(r.get("created_at")) or datetime.now(UTC),
                last_used=_as_dt(r.get("last_used")),
            )
        )
    return resp


@router.post("/keys", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_api_key(
    payload: ApiKeyCreateRequest,
    principal: Principal = Depends(require_user_principal),
) -> None:
    """Insert or replace the user's API key for a service.

    Stores the secret in Vault via ``public.insert_user_api_key`` and upserts
    metadata in ``public.api_keys``. Returns 204 on success.
    """
    service = payload.service.lower().strip()
    if service not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail="Unsupported service")

    user_id = get_principal_id(principal)
    admin = await get_admin_client()
    try:
        await admin.rpc(
            "insert_user_api_key",
            {"p_user_id": user_id, "p_service": service, "p_api_key": payload.api_key},
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to store API key") from exc


@router.delete("/keys/{service}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    service: str,
    principal: Principal = Depends(require_user_principal),
) -> None:
    """Delete a user's API key and its Vault secret."""
    svc = service.lower().strip()
    if svc not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail="Unsupported service")
    user_id = get_principal_id(principal)
    admin = await get_admin_client()
    try:
        await admin.rpc(
            "delete_user_api_key", {"p_user_id": user_id, "p_service": svc}
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to delete API key") from exc


@router.post("/keys/validate", response_model=ApiKeyValidateResponse)
async def validate_api_key_endpoint(
    payload: ApiKeyValidateRequest,
) -> ApiKeyValidateResponse:
    """Validate a provider API key by calling provider metadata."""
    ok, reason = await _validate_api_key(payload.service, payload.api_key)
    return ApiKeyValidateResponse(is_valid=ok, reason=reason)
