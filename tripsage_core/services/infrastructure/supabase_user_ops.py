"""Supabase user operations for TripSage.

This module centralises helper utilities for interacting with Supabase Auth
users via the official Python SDK. By funnelling all lookups and metadata
updates through these helpers we avoid bespoke service layers (e.g.
``UserService``) and rely on Supabase's managed functionality instead.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from tripsage_core.services.infrastructure.supabase_client import get_admin_client


def _normalise_user(user: Any) -> dict[str, Any]:
    """Convert Supabase user object into a plain dictionary."""
    return {
        "id": str(getattr(user, "id", "")),
        "email": getattr(user, "email", None),
        "user_metadata": getattr(user, "user_metadata", {}) or {},
    }


def _coerce_mapping(value: Any) -> dict[str, Any]:
    """Return a shallow dict copy when the value is mapping-like."""
    if isinstance(value, Mapping):
        return dict(cast(Mapping[str, Any], value))
    return {}


async def fetch_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetch a Supabase user by identifier."""
    client = await get_admin_client()
    response = await client.auth.admin.get_user_by_id(user_id)  # type: ignore[attr-defined]
    user = getattr(response, "user", None)
    if not user:
        return None
    return _normalise_user(user)


async def fetch_user_by_email(email: str) -> dict[str, Any] | None:
    """Fetch a Supabase user by email address."""
    client = await get_admin_client()
    response = await client.auth.admin.list_users({"email": email})  # type: ignore[attr-defined]
    users_raw = getattr(response, "users", None)
    users: list[Any] = list(users_raw or [])
    for user in users:
        user_email = getattr(user, "email", None)
        if isinstance(user_email, str) and user_email.lower() == email.lower():
            return _normalise_user(user)
    return None


async def get_user_preferences(user_id: str) -> dict[str, Any]:
    """Retrieve stored user preferences from Supabase user metadata."""
    user = await fetch_user_by_id(user_id)
    metadata = _coerce_mapping(user.get("user_metadata")) if user else {}
    prefs = metadata.get("preferences", {})
    if isinstance(prefs, Mapping):
        return dict(cast(Mapping[str, Any], prefs))
    return {}


async def update_user_preferences(
    user_id: str, *, new_preferences: Mapping[str, Any]
) -> dict[str, Any]:
    """Merge and persist user preferences in Supabase user metadata."""
    user = await fetch_user_by_id(user_id)
    existing_metadata: dict[str, Any] = (
        _coerce_mapping(user.get("user_metadata")) if user else {}
    )
    existing_preferences = existing_metadata.get("preferences", {})
    preferences_mapping: Mapping[str, Any]
    if isinstance(existing_preferences, Mapping):
        preferences_mapping = cast(Mapping[str, Any], existing_preferences)
    else:
        preferences_mapping = {}

    merged_preferences: dict[str, Any] = dict(preferences_mapping)
    merged_preferences.update(dict(new_preferences))

    updated_metadata: dict[str, Any] = {
        **existing_metadata,
        "preferences": merged_preferences,
    }

    client = await get_admin_client()
    admin_client = cast(Any, client.auth.admin)
    response = await admin_client.update_user_by_id(  # type: ignore[call-arg]
        user_id,
        user_metadata=updated_metadata,
    )
    updated_user = getattr(response, "user", None)
    if not updated_user:
        return merged_preferences
    normalised = _normalise_user(updated_user)
    metadata = _coerce_mapping(normalised.get("user_metadata", {}))
    prefs = metadata.get("preferences", {})
    if isinstance(prefs, Mapping):
        return dict(cast(Mapping[str, Any], prefs))
    return merged_preferences
