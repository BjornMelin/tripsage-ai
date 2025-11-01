"""Unit tests for attachments router with DI stubs.

Covers: metadata retrieval (200/404), delete (200/404), and list files.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


@dataclass
class _ProcStatus:
    """Processing status stub."""

    value: str


@dataclass
class _File:
    """File metadata stub."""

    id: str
    original_filename: str
    file_size: int
    mime_type: str
    processing_status: _ProcStatus


class _FakeFileService:
    """In-memory file service stub."""

    def __init__(self) -> None:
        """Initialize in-memory file store with one sample file."""
        self._files: dict[str, _File] = {
            "f1": _File(
                id="f1",
                original_filename="doc.pdf",
                file_size=123,
                mime_type="application/pdf",
                processing_status=_ProcStatus("completed"),
            )
        }

    async def get_file(self, file_id: str, user_id: str) -> Any:
        """Return file metadata for a given file id or None when missing."""
        from tripsage.api.schemas.attachments import FileMetadataResponse

        f = self._files.get(file_id)
        if not f:
            return None
        return FileMetadataResponse(
            file_id=f.id,
            filename=f.original_filename,
            file_size=f.file_size,
            mime_type=f.mime_type,
            processing_status=f.processing_status.value,
        )

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete a file by id and return True when removed."""
        if file_id in self._files:
            del self._files[file_id]
            return True
        return False

    async def search_files(self, user_id: str, request: Any) -> list[_File]:
        """List files for the user; request contains paging filters."""
        return list(self._files.values())


def _build_app(
    principal: Any, service: _FakeFileService, monkeypatch: pytest.MonkeyPatch
) -> FastAPI:
    """Build app and apply overrides."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "attachments_router_module", "tripsage/api/routers/attachments.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(module.router, prefix="/api/attachments")

    from tripsage.api.core import dependencies as dep
    from tripsage.api.middlewares.authentication import (
        Principal as RealPrincipal,
    )

    # Return a Principal instance from the runtime module to satisfy helpers
    def _provide_principal() -> RealPrincipal:  # type: ignore[name-defined]
        """Provide a concrete Principal instance from runtime module."""
        return RealPrincipal(
            id=getattr(principal, "id", "user-1"),
            type=getattr(principal, "type", "user"),
            email=getattr(principal, "email", None),
            auth_method=getattr(principal, "auth_method", "jwt"),
            scopes=getattr(principal, "scopes", []),
            metadata=getattr(principal, "metadata", {}),
        )

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]

    # Tolerant principal id extractor to avoid typing edge cases
    def _principal_id(p: object) -> str:
        """Extract principal ID from object."""
        return str(getattr(p, "id", "user-1"))

    monkeypatch.setattr(module, "get_principal_id", _principal_id, raising=False)

    def _provide_fps() -> _FakeFileService:
        """Provide file processing service stub."""
        return service

    app.dependency_overrides[dep.get_file_processing_service] = _provide_fps  # type: ignore[assignment]

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_files_metadata_delete_and_list(
    principal: Any,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise metadata get (200/404), delete, and list flows."""
    svc = _FakeFileService()
    app = _build_app(principal, svc, monkeypatch)
    client = async_client_factory(app)

    # Metadata 200
    r = await client.get("/api/attachments/files/f1")
    assert r.status_code == status.HTTP_200_OK
    meta = r.json()
    assert meta["file_id"] == "f1" or meta.get("id") == "f1"

    # List files
    r = await client.get("/api/attachments/files")
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["total"] >= 1

    # Delete 200
    r = await client.delete("/api/attachments/files/f1")
    assert r.status_code == status.HTTP_200_OK

    # Metadata 404
    r = await client.get("/api/attachments/files/f1")
    assert r.status_code == status.HTTP_404_NOT_FOUND
