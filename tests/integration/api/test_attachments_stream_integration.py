"""Integration tests for attachments download endpoint."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


@dataclass
class _FileInfo:
    """Minimal file info object used by the router for downloads."""

    id: str
    original_filename: str
    mime_type: str


class _FPSvc:
    """File processing service stub supporting download flows."""

    def __init__(self) -> None:
        """Initialize in-memory stores for metadata and content."""
        self.files: dict[str, _FileInfo] = {}
        self.contents: dict[str, bytes] = {}

    async def get_file(self, file_id: str, user_id: str) -> _FileInfo | None:
        """Return file metadata for a given user if present."""
        return self.files.get(file_id)

    async def get_file_content(self, file_id: str, user_id: str) -> bytes | None:
        """Return file content for a given user if present."""
        return self.contents.get(file_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_attachments_download_and_404(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Download returns content and headers; unknown file yields 404."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    svc = _FPSvc()
    svc.files["f1"] = _FileInfo(
        id="f1", original_filename="doc.txt", mime_type="text/plain"
    )
    svc.contents["f1"] = b"hello"

    def _provide_fps() -> _FPSvc:
        """Provide file processing service stub for DI."""
        return svc

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_file_processing_service] = _provide_fps  # type: ignore[assignment]

    # Tolerant principal id extractor for the actual router module
    from tripsage.api.routers import attachments as attachments_module

    def _principal_id(p: object) -> str:
        """Extract principal ID from object for tests."""
        return str(getattr(p, "id", "user-1"))

    monkeypatch.setattr(
        attachments_module, "get_principal_id", _principal_id, raising=False
    )

    client = async_client_factory(app)
    # Happy download
    r = await client.get("/api/attachments/files/f1/download")
    assert r.status_code == status.HTTP_200_OK
    assert r.headers.get("Content-Type") == "text/plain"
    assert 'attachment; filename="doc.txt"' in r.headers.get("Content-Disposition", "")
    assert r.content == b"hello"

    # 404 when file missing
    r = await client.get("/api/attachments/files/missing/download")
    assert r.status_code == status.HTTP_404_NOT_FOUND
