"""Async Supabase client utilities.

This module centralizes creation of Supabase async clients and common
authentication helpers. It enables claims-first JWT verification using the
Supabase JWKS (preferred over per-request get_user calls) and offers an
optional PostgREST client configured with a user's bearer token for RLS-aware
server-side operations.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

from postgrest import AsyncPostgrestClient
from supabase.lib.client_options import (
    AsyncClientOptions,  # pylint: disable=no-name-in-module
)

from supabase import (  # pylint: disable=no-name-in-module
    AsyncClient as SupabaseAsyncClient,
    acreate_client,
)
from tripsage_core.config import get_settings


_admin_client: SupabaseAsyncClient | None = None
_public_client: SupabaseAsyncClient | None = None


async def get_admin_client() -> SupabaseAsyncClient:
    """Create or return a cached Supabase admin async client.

    The admin client uses the service role key and must only be used on the
    server for privileged operations (auth.admin.*, management tasks).

    Returns:
        AsyncClient: Configured Supabase admin client.
    """
    global _admin_client  # pylint: disable=global-statement
    if _admin_client is not None:
        return _admin_client

    settings = get_settings()
    _admin_client = await acreate_client(
        str(settings.database_url),
        # pylint: disable=no-member
        settings.database_service_key.get_secret_value(),
        options=AsyncClientOptions(auto_refresh_token=False, persist_session=False),
    )
    return _admin_client


async def get_public_client() -> SupabaseAsyncClient:
    """Create or return a cached Supabase public (anon) async client.

    The public client is sufficient for verifying JWT claims using the
    Supabase project's JWKS via ``auth.get_claims``.

    Returns:
        AsyncClient: Configured Supabase public client.
    """
    global _public_client  # pylint: disable=global-statement
    if _public_client is not None:
        return _public_client

    settings = get_settings()
    _public_client = await acreate_client(
        str(settings.database_url),
        # pylint: disable=no-member
        settings.database_public_key.get_secret_value(),
        options=AsyncClientOptions(auto_refresh_token=False, persist_session=False),
    )
    return _public_client


async def verify_and_get_claims(jwt: str) -> dict[str, Any]:
    """Verify a Supabase access token and return its claims.

    This method uses the project's JWKS (cached by Supabase) and avoids a
    network call to the auth server on every request.

    Args:
        jwt: Access token issued by Supabase Auth.

    Returns:
        Dict of verified JWT claims (e.g., ``sub``, ``email``, ``aud``, ``role``).

    Raises:
        Exception: When verification fails or the token is invalid.
    """
    client = await get_public_client()
    claims_resp = await client.auth.get_claims(jwt=jwt)
    claims = cast(dict[str, Any], claims_resp)
    if not claims.get("sub"):
        raise ValueError("Invalid claims returned by Supabase")
    return claims


def postgrest_for_user(token: str) -> AsyncPostgrestClient:
    """Create an AsyncPostgrestClient authorized as the given user.

    Use this client for server-side queries that must respect Row Level
    Security (RLS) under the user's identity. Callers are responsible for
    managing the lifecycle of the returned client.

    Args:
        token: User's Supabase access token.

    Returns:
        AsyncPostgrestClient configured with ``Authorization: Bearer <token>``.
    """
    rest_url = supabase_rest_url()
    client = AsyncPostgrestClient(rest_url)
    client.auth(token)
    return client


@lru_cache
def supabase_rest_url() -> str:
    """Return the project's REST endpoint base URL.

    Returns:
        REST base URL for PostgREST operations.
    """
    settings = get_settings()
    database_url = str(settings.database_url)
    return database_url.rstrip("/") + "/rest/v1"
