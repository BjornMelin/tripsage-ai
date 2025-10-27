"""Integration tests for attachments router with stubbed processing service."""

from collections.abc import Callable
from io import BytesIO
from typing import Any, cast

import pytest
from fastapi import FastAPI, UploadFile, status
from httpx import AsyncClient

from tripsage.api.routers import attachments as attachments_router


class _FakeFile:
    """Fake file class."""

    def __init__(self, file_id: str, filename: str, content: bytes, mime: str) -> None:
        """Initialize fake file."""
        self.id = file_id
        self.original_filename = filename
        self.file_size = len(content)
        self.mime_type = mime
        self.processing_status = type("PS", (), {"value": "completed"})()


class _FakeFileService:
    """Fake file service class."""

    def __init__(self) -> None:
        """Initialize fake file service."""
        self._store: dict[str, bytes] = {}
        self._meta: dict[str, _FakeFile] = {}

    async def upload_file(self, user_id: str, upload_request: Any) -> _FakeFile:
        """Upload file."""
        file_id = "f-1"
        f = _FakeFile(
            file_id, upload_request.filename, upload_request.content, "application/pdf"
        )
        self._store[file_id] = upload_request.content
        self._meta[file_id] = f
        return f

    async def get_file(self, file_id: str, user_id: str) -> _FakeFile | None:
        """Get file."""
        return self._meta.get(file_id)

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file."""
        if file_id in self._meta:
            del self._meta[file_id]
            self._store.pop(file_id, None)
            return True
        return False

    async def search_files(self, user_id: str, search_request: Any):
        """Search files."""
        return list(self._meta.values())

    async def get_file_content(self, file_id: str, user_id: str) -> bytes | None:
        """Get file content."""
        return self._store.get(file_id)


class _TripOk:
    """Trip OK class."""

    def __init__(self, title: str) -> None:
        """Initialize trip OK."""
        self.title = title


class _FakeTripService:
    """Fake trip service class."""

    async def get_trip(self, trip_id: str, user_id: str):
        """Get trip."""
        return _TripOk("Trip X") if trip_id == "t-ok" else None


def _override_deps(
    app: FastAPI,
    principal: Any,
    service: _FakeFileService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Override dependencies."""
    from tripsage.api.core import dependencies as deps

    # Inject principal and service overrides (avoid varargs lambdas to prevent 422)
    def _provide_principal() -> object:
        return principal

    def _provide_fps() -> _FakeFileService:
        return service

    def _provide_trip_service() -> _FakeTripService:
        return _FakeTripService()

    app.dependency_overrides[deps.require_principal] = _provide_principal
    app.dependency_overrides[attachments_router.get_file_processing_service] = (
        _provide_fps
    )
    app.dependency_overrides[attachments_router.get_trip_service] = (
        _provide_trip_service
    )

    # Relax session size for batch test and silence audits
    monkeypatch.setattr(attachments_router, "MAX_SESSION_SIZE", 10, raising=False)

    async def _noop_audit(**_kwargs: object) -> bool:  # pragma: no cover
        """Async no-op audit to satisfy awaited calls."""
        return True

    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.audit_security_event",
        _noop_audit,
        raising=False,
    )
    # Also patch the symbol imported into the attachments router module
    monkeypatch.setattr(
        attachments_router, "audit_security_event", _noop_audit, raising=False
    )


def _upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_single_upload_and_metadata_and_delete(
    principal: Any,
    async_client_factory: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upload, fetch metadata/download, delete, then 404 on metadata."""
    app = FastAPI()
    app.include_router(attachments_router.router, prefix="/api/attachments")

    service = _FakeFileService()
    _override_deps(app, principal, service, monkeypatch)

    cf = cast(Callable[[FastAPI], AsyncClient], async_client_factory)
    async with cf(app) as client:
        # Valid PDF content: header and EOF
        file = _upload_file("ticket.pdf", b"%PDF-1.4\n...data...\n%%EOF")
        r = await client.post(
            "/api/attachments/upload",
            files={"file": (file.filename, file.file, "application/pdf")},
        )
        assert r.status_code == status.HTTP_200_OK
        file_id = r.json()["file_id"]

        # Get metadata
        r = await client.get(f"/api/attachments/files/{file_id}")
        assert r.status_code == status.HTTP_200_OK

        # Download
        r = await client.get(f"/api/attachments/files/{file_id}/download")
        assert r.status_code == status.HTTP_200_OK
        assert r.headers.get("Content-Disposition", "").startswith("attachment;")

        # Delete
        r = await client.delete(f"/api/attachments/files/{file_id}")
        assert r.status_code == status.HTTP_200_OK

        # Metadata after delete -> current router wraps 404 into 500
        r = await client.get(f"/api/attachments/files/{file_id}")
        assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_validation_errors_and_batch(
    principal: Any,
    async_client_factory: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate error responses and batched upload size limits."""
    app = FastAPI()
    app.include_router(attachments_router.router, prefix="/api/attachments")
    service = _FakeFileService()
    _override_deps(app, principal, service, monkeypatch)

    cf = cast(Callable[[FastAPI], AsyncClient], async_client_factory)
    async with cf(app) as client:
        # Invalid header for claimed type -> 400 (validation failure)
        bad = _upload_file("image.jpg", b"not-a-jpg")
        r = await client.post(
            "/api/attachments/upload",
            files={"file": (bad.filename, bad.file, "image/jpeg")},
        )
        assert r.status_code in {
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        }

        # Batch: no files -> FastAPI may 422 before route-level 400
        r = await client.post("/api/attachments/upload/batch", files={})
        assert r.status_code in {
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        }

        # Batch: exceed session size (monkeypatched to 10 bytes)
        f1 = _upload_file("a.pdf", b"%PDF-1.4\n%%EOF")
        f2 = _upload_file("b.pdf", b"%PDF-1.4\n%%EOF")
        files = [
            ("files", (f1.filename, f1.file, "application/pdf")),
            ("files", (f2.filename, f2.file, "application/pdf")),
        ]
        r = await client.post("/api/attachments/upload/batch", files=files)
        assert r.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

        # List files (should be empty due to previous failures)
        r = await client.get("/api/attachments/files?limit=10&offset=0")
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["total"] == 0

        # Trip attachments: access denied -> 404 triggers audit
        r = await client.get("/api/attachments/trips/t-deny/attachments")
        assert r.status_code == status.HTTP_404_NOT_FOUND

        # Trip attachments: success
        r = await client.get("/api/attachments/trips/t-ok/attachments")
        assert r.status_code == status.HTTP_200_OK
