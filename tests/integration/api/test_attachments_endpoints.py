"""Integration tests for attachment upload endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tripsage.api.core.dependencies import require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers.attachments import get_file_processing_service
from tripsage_core.services.business.file_processing_service import (
    FileUploadRequest,
    ProcessingStatus,
)


class FileProcessingServiceStub:
    """Stub service emulating successful file uploads."""

    def __init__(self) -> None:
        """Initialize the stubbed service state."""
        self.upload_calls: list[tuple[str, FileUploadRequest]] = []

    async def upload_file(
        self, user_id: str, upload_request: FileUploadRequest
    ) -> SimpleNamespace:
        """Record invocation and return a processed file namespace."""
        self.upload_calls.append((user_id, upload_request))
        return SimpleNamespace(
            id="file-123",
            original_filename=upload_request.filename,
            file_size=len(upload_request.content),
            mime_type="text/plain",
            processing_status=ProcessingStatus.COMPLETED,
        )


def _principal_stub() -> Principal:
    return Principal(
        id="user-456",
        type="user",
        email="tester@example.com",
        auth_method="jwt",
        scopes=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_upload_file_returns_processed_metadata(
    app: FastAPI, async_client: AsyncClient
) -> None:
    """POST /attachments/upload should validate and persist files."""
    stub = FileProcessingServiceStub()

    async def _principal_override() -> Principal:
        return _principal_stub()

    async def _service_override() -> FileProcessingServiceStub:
        return stub

    app.dependency_overrides[require_principal] = _principal_override
    app.dependency_overrides[get_file_processing_service] = _service_override

    files: dict[str, tuple[str, bytes, str]] = {
        "file": ("itinerary.txt", b"Kyoto itinerary", "text/plain")
    }

    try:
        response = await async_client.post("/api/attachments/upload", files=files)
    finally:
        app.dependency_overrides.pop(require_principal, None)
        app.dependency_overrides.pop(get_file_processing_service, None)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["file_id"] == "file-123"
    assert data["processing_status"] == ProcessingStatus.COMPLETED.value
    assert stub.upload_calls
