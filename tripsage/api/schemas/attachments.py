"""Attachment API schemas (feature-first)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response after a single file upload."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    processing_status: str = Field(..., description="Processing status")
    upload_status: str = Field(..., description="Upload status")
    message: str = Field(default="Upload successful", description="Status message")


class BatchUploadResponse(BaseModel):
    """Response for a batch file upload operation."""

    files: list[FileUploadResponse] = Field(..., description="Processed files")
    total_files: int = Field(..., description="Total files processed")
    total_size: int = Field(..., description="Total size in bytes")


class FileMetadataResponse(BaseModel):
    """Metadata for an uploaded file."""

    file_id: str
    filename: str
    file_size: int
    mime_type: str
    processing_status: str
    created_at: str | None = None
    analysis_summary: dict[str, Any] | None = None


class FileListResponse(BaseModel):
    """Paginated list of file metadata."""

    files: list[FileMetadataResponse]
    limit: int
    offset: int
    total: int


class DeleteFileResponse(BaseModel):
    """Confirmation for a deletion request."""

    message: str
    file_id: str
