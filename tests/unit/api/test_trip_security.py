"""Unit tests for TripSage trip security helpers and dependencies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from tripsage.api.core import trip_security as trip_security_mod
from tripsage.api.core.trip_security import (
    TripAccessLevel,
    TripAccessPermission,
    TripAccessResult,
    check_trip_collaboration,
    check_trip_ownership,
    get_user_trip_permissions,
    require_trip_access,
    verify_trip_access,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError,
    CoreSecurityError,
)
from tripsage_core.models.schemas_common.enums import TripVisibility
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditSeverity,
)
from tripsage_core.services.business.trip_service import TripService


DepCallable = Callable[[Request, Principal, TripService], Awaitable[TripAccessResult]]
DepFactory = Callable[[TripAccessLevel, TripAccessPermission | None, str], DepCallable]
create_dep: DepFactory = cast(
    DepFactory, trip_security_mod.create_trip_access_dependency
)


@dataclass
class _Ctx:
    """Lightweight context to bypass Pydantic enum coercion in tests."""

    trip_id: str
    principal_id: str
    required_level: TripAccessLevel
    required_permission: TripAccessPermission | None
    operation: str
    ip_address: str | None = None
    user_agent: str | None = None


def _empty_collab_list() -> list[dict[str, Any]]:
    """Return an empty collaborator list with precise typing."""
    return []


@dataclass
class _FakeDB:
    """Fake DB with typed collaborator list."""

    trip: dict[str, Any] | None = None
    collaborators: list[dict[str, Any]] = field(default_factory=_empty_collab_list)

    async def get_trip_by_id(self, trip_id: str) -> dict[str, Any] | None:
        """Get trip by ID."""
        return self.trip

    async def get_trip_collaborators(self, trip_id: str) -> list[dict[str, Any]]:
        """Get trip collaborators."""
        return self.collaborators


@dataclass
class _FakeTripService:
    """Fake trip service class."""

    db: _FakeDB
    allow_basic_access: bool = True

    async def _check_trip_access(
        self, *, trip_id: str, user_id: str, require_owner: bool
    ) -> bool:
        """Check trip access."""
        return self.allow_basic_access


def _principal(user_id: str = "user-1") -> Principal:
    """Construct a minimal Principal for test calls."""
    return Principal(id=user_id, type="user", email="u@example.com", auth_method="jwt")


@pytest.mark.asyncio
async def test_verify_denied_when_basic_access_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Access denied when basic TripService check returns False; audits event."""
    calls: list[dict[str, Any]] = []

    async def fake_audit(**kwargs: Any) -> None:
        """Fake audit."""
        calls.append(kwargs)

    monkeypatch.setattr(
        "tripsage.api.core.trip_security.audit_security_event",
        fake_audit,
        raising=False,
    )

    service = _FakeTripService(db=_FakeDB(), allow_basic_access=False)
    ctx = _Ctx(
        trip_id="abc",
        principal_id="user-1",
        required_level=TripAccessLevel.READ,
        required_permission=None,
        operation="GET /api/trips/abc",
    )
    result = await verify_trip_access(ctx, service)  # type: ignore[arg-type]
    assert result.is_authorized is False
    assert result.denial_reason == "Insufficient permissions for read access"

    assert calls and calls[-1]["event_type"] == AuditEventType.ACCESS_DENIED
    assert calls[-1]["severity"] == AuditSeverity.MEDIUM


@pytest.mark.asyncio
async def test_verify_raises_when_trip_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise CoreResourceNotFoundError when trip record is missing."""
    service = _FakeTripService(db=_FakeDB(trip=None))
    ctx = _Ctx(
        trip_id="abc",
        principal_id="user-1",
        required_level=TripAccessLevel.READ,
        required_permission=None,
        operation="GET /api/trips/abc",
    )

    with pytest.raises(CoreResourceNotFoundError):
        await verify_trip_access(ctx, service)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_verify_owner_success_and_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Owners receive MANAGE permission and ACCESS_GRANTED audit is emitted."""
    calls: list[dict[str, Any]] = []

    async def fake_audit(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(
        "tripsage.api.core.trip_security.audit_security_event",
        fake_audit,
        raising=False,
    )

    trip = {"id": "abc", "user_id": "user-1", "visibility": TripVisibility.PUBLIC.value}
    service = _FakeTripService(db=_FakeDB(trip=trip))
    ctx = _Ctx(
        trip_id="abc",
        principal_id="user-1",
        required_level=TripAccessLevel.READ,
        required_permission=None,
        operation="GET /api/trips/abc",
    )
    result = await verify_trip_access(ctx, service)  # type: ignore[arg-type]
    assert result.is_authorized is True
    assert result.is_owner is True
    assert result.access_level == TripAccessLevel.OWNER
    assert result.permission_granted == TripAccessPermission.MANAGE
    assert result.trip_visibility == TripVisibility.PUBLIC

    assert calls and calls[-1]["event_type"] == AuditEventType.ACCESS_GRANTED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("collab_perm", "expected"),
    [
        ("view", TripAccessPermission.VIEW),
        ("edit", TripAccessPermission.EDIT),
        ("manage", TripAccessPermission.MANAGE),
        ("unknown", TripAccessPermission.VIEW),  # default fallback
    ],
)
async def test_verify_collaborator_permission_mapping(
    collab_perm: str, expected: TripAccessPermission
) -> None:
    """Map collaborator string permission values to enum with safe fallback."""
    trip = {
        "id": "abc",
        "user_id": "owner-1",
        "visibility": TripVisibility.PRIVATE.value,
    }
    collabs = [{"user_id": "user-2", "permission": collab_perm}]
    service = _FakeTripService(db=_FakeDB(trip=trip, collaborators=collabs))
    ctx = _Ctx(
        trip_id="abc",
        principal_id="user-2",
        required_level=TripAccessLevel.READ,
        required_permission=None,
        operation="GET /api/trips/abc",
    )
    result = await verify_trip_access(ctx, service)  # type: ignore[arg-type]
    assert result.is_authorized is True
    assert result.is_owner is False
    assert result.is_collaborator is True
    assert result.permission_granted == expected
    assert result.access_level in {TripAccessLevel.COLLABORATOR, TripAccessLevel.READ}


@pytest.mark.asyncio
async def test_verify_denied_on_insufficient_collab_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deny when granted permission is below required (view vs edit)."""
    calls: list[dict[str, Any]] = []

    async def fake_audit(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(
        "tripsage.api.core.trip_security.audit_security_event",
        fake_audit,
        raising=False,
    )

    trip = {
        "id": "abc",
        "user_id": "owner-1",
        "visibility": TripVisibility.SHARED.value,
    }
    collabs = [{"user_id": "user-2", "permission": "view"}]
    service = _FakeTripService(db=_FakeDB(trip=trip, collaborators=collabs))
    ctx = _Ctx(
        trip_id="abc",
        principal_id="user-2",
        required_level=TripAccessLevel.COLLABORATOR,
        required_permission=TripAccessPermission.EDIT,
        operation="PUT /api/trips/abc",
    )
    result = await verify_trip_access(ctx, service)  # type: ignore[arg-type]
    assert result.is_authorized is False
    assert result.denial_reason and "requires edit permission" in result.denial_reason
    assert calls and calls[-1]["event_type"] == AuditEventType.ACCESS_DENIED


@pytest.mark.asyncio
async def test_verify_unexpected_error_logs_and_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected error path audits suspicious activity and raises CoreSecurityError."""
    calls: list[dict[str, Any]] = []

    async def fake_audit(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(
        "tripsage.api.core.trip_security.audit_security_event",
        fake_audit,
        raising=False,
    )

    # Invalid visibility triggers enum conversion failure -> CoreSecurityError path
    trip = {"id": "abc", "user_id": "owner-1", "visibility": "invalid-visibility"}
    service = _FakeTripService(db=_FakeDB(trip=trip))
    ctx = _Ctx(
        trip_id="abc",
        principal_id="owner-1",
        required_level=TripAccessLevel.READ,
        required_permission=None,
        operation="GET /api/trips/abc",
    )
    with pytest.raises(CoreSecurityError):
        await verify_trip_access(ctx, service)  # type: ignore[arg-type]

    assert (
        calls and calls[-1]["event_type"] == AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY
    )


def _request_with_path(path: str, headers: dict[str, str] | None = None) -> Request:
    """Create a Request with trip_id in scope path_params and UA header."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "path_params": {"trip_id": path.split("/")[-1]},
        "headers": [
            (b"user-agent", (headers or {}).get("User-Agent", "pytest").encode())
        ],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_create_trip_access_dependency_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dependency returns TripAccessResult on successful authorization."""
    dep_typed = create_dep(TripAccessLevel.READ, None, "trip_id")

    service = _FakeTripService(
        db=_FakeDB(trip={"id": "t1", "user_id": "u1", "visibility": "public"})
    )
    req = _request_with_path("/api/trips/t1")
    result = await dep_typed(req, _principal("u1"), cast(TripService, service))
    assert isinstance(result, TripAccessResult)
    assert result.is_authorized is True


@pytest.mark.asyncio
async def test_create_trip_access_dependency_missing_trip_id() -> None:
    """Dependency raises HTTP 400 when trip_id param is missing from path."""
    dep_typed = create_dep(TripAccessLevel.READ, None, "trip_id")
    # Build request without path params
    scope = {"type": "http", "method": "GET", "path": "/api/trips"}
    req = Request(scope)
    with pytest.raises(HTTPException) as ei:
        await dep_typed(
            req, _principal("u1"), cast(TripService, _FakeTripService(db=_FakeDB()))
        )
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_create_trip_access_dependency_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dependency raises 403 when user lacks required OWNER access."""
    # Ensure enum objects survive inside context by replacing the model
    monkeypatch.setattr(
        "tripsage.api.core.trip_security.TripAccessContext", _Ctx, raising=False
    )
    dep_typed = create_dep(TripAccessLevel.OWNER, None, "trip_id")
    service = _FakeTripService(
        db=_FakeDB(trip={"id": "t1", "user_id": "other", "visibility": "private"}),
        allow_basic_access=False,
    )
    req = _request_with_path("/api/trips/t1")
    with pytest.raises(HTTPException) as ei:
        await dep_typed(req, _principal("u1"), cast(TripService, service))
    assert ei.value.status_code == 403


def test_require_trip_access_decorator_adds_annotation() -> None:
    """Decorator injects DI annotation used by FastAPI for access check."""

    @require_trip_access(TripAccessLevel.READ)
    async def handler(trip_id: str) -> str:
        return f"ok:{trip_id}"

    ann = getattr(handler, "__annotations__", {})
    assert "_trip_access_verification" in ann


@pytest.mark.asyncio
async def test_check_helpers_and_permission_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise ownership helper, collab error guard, and summary fallback.

    Ensures wrappers around verify_trip_access handle errors and report the
    default, non-authorized summary when underlying calls fail.
    """
    trip = {"id": "t2", "user_id": "u1", "visibility": "shared"}
    service = _FakeTripService(db=_FakeDB(trip=trip))

    assert await check_trip_ownership("t2", _principal("u1"), service) is True  # type: ignore[arg-type]

    # collaboration false path: patch verify_trip_access to raise TimeoutError
    async def _raise_timeout(*_a: Any, **_k: Any) -> Any:
        raise TimeoutError("db stalled")

    monkeypatch.setattr(
        "tripsage.api.core.trip_security.verify_trip_access",
        _raise_timeout,
        raising=False,
    )
    ok = await check_trip_collaboration(
        "t2",
        _principal("u1"),
        cast(TripService, service),
        TripAccessPermission.EDIT,  # type: ignore[arg-type]
    )
    assert ok is False

    # permission summary (fallback path due to error)
    summary = await get_user_trip_permissions("t2", _principal("u1"), service)  # type: ignore[arg-type]
    assert summary["is_authorized"] is False
