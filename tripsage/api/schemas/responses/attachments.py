"""Attachment API response schemas.

Defines Pydantic response models for file uploads and batch operations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for file upload.

    Attributes:
        file_id: Unique file identifier.
        filename: Original filename.
        file_size: File size in bytes.
        mime_type: MIME type.
        processing_status: Processing status value string.
        upload_status: Upload status string.
        message: Optional status message.
    """

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    processing_status: str = Field(..., description="Processing status")
    upload_status: str = Field(..., description="Upload status")
    message: str = Field(default="Upload successful", description="Status message")


class BatchUploadResponse(BaseModel):
    """Response model for batch file upload.

    Attributes:
        files: Processed file responses.
        total_files: Total files processed.
        total_size: Total size in bytes.
    """

    files: list[FileUploadResponse] = Field(..., description="Processed files")
    total_files: int = Field(..., description="Total files processed")
    total_size: int = Field(..., description="Total size in bytes")
