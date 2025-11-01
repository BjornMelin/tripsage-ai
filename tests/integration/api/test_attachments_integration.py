"""Integration tests for attachments router with DI overrides."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


@dataclass
class _Proc:
    """Processing status stub."""

    value: str


@dataclass
class _File:
    """File metadata stub."""

    id: str
    original_filename: str
    file_size: int
    mime_type: str
    processing_status: _Proc


class _FPS:
    """File processing service stub."""

    def __init__(self) -> None:
        """Initialize file processing service."""
        self.files: dict[str, _File] = {}

    async def get_file(self, file_id: str, user_id: str) -> Any:
        """Get file metadata."""
        if file_id not in self.files:
            return None
        f = self.files[file_id]
        return {
            "file_id": f.id,
            "filename": f.original_filename,
            "file_size": f.file_size,
            "mime_type": f.mime_type,
            "processing_status": f.processing_status.value,
        }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_attachments_metadata_404(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown file id returns 404 metadata error."""
    from tripsage.api.core import dependencies as dep
    from tripsage.api.middlewares.authentication import (
        Principal as RealPrincipal,
    )

    def _provide_principal() -> RealPrincipal:
        """Provide principal instance."""
        return RealPrincipal(
            id=getattr(principal, "id", "user-1"),
            type=getattr(principal, "type", "user"),
            email=getattr(principal, "email", None),
            auth_method=getattr(principal, "auth_method", "jwt"),
            scopes=getattr(principal, "scopes", []),
            metadata=getattr(principal, "metadata", {}),
        )

    svc = _FPS()

    def _provide_fps() -> _FPS:
        """Provide file processing service."""
        return svc

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_file_processing_service] = _provide_fps  # type: ignore[assignment]

    # Tolerant principal id extractor for the actual router module
    from tripsage.api.routers import attachments as attachments_module

    def _principal_id(p: object) -> str:
        """Extract principal ID from object."""
        return str(getattr(p, "id", "user-1"))

    monkeypatch.setattr(
        attachments_module, "get_principal_id", _principal_id, raising=False
    )

    client = async_client_factory(app)
    r = await client.get("/api/attachments/files/unknown")
    assert r.status_code == status.HTTP_404_NOT_FOUND
