"""
Pydantic models for file attachments and document processing.

This module defines models for file uploads, metadata, and AI analysis results
following the established patterns in the codebase.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class FileType(str, Enum):
    """Supported file types for upload."""

    IMAGE = "image"
    DOCUMENT = "document"
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"


class ProcessingStatus(str, Enum):
    """File processing status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STORED = "stored"


class AttachmentBase(BaseModel):
    """Base model for file attachments."""

    original_filename: str = Field(
        ..., min_length=1, max_length=255, description="Original uploaded filename"
    )
    file_size: int = Field(..., ge=1, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    file_type: FileType = Field(..., description="Categorized file type")


class AttachmentCreate(AttachmentBase):
    """Model for creating new attachments."""

    content_hash: str = Field(..., description="SHA256 hash of file content")

    @validator("mime_type")
    def validate_mime_type(cls, v):
        """Validate MIME type format."""
        if not v or "/" not in v:
            raise ValueError("Invalid MIME type format")
        return v.lower()


class AttachmentUpdate(BaseModel):
    """Model for updating attachment metadata."""

    processing_status: Optional[ProcessingStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None


class AttachmentDB(AttachmentBase):
    """Database model for file attachments."""

    id: UUID = Field(..., description="Unique attachment identifier")
    user_id: UUID = Field(..., description="ID of the user who uploaded the file")
    chat_session_id: Optional[UUID] = Field(
        None, description="Associated chat session ID"
    )

    stored_filename: str = Field(..., description="Filename used for storage")
    storage_path: str = Field(..., description="Relative path to stored file")
    content_hash: str = Field(..., description="SHA256 hash for deduplication")

    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING, description="Current processing status"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    analysis_results: Optional[Dict[str, Any]] = Field(
        None, description="AI analysis results"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class AttachmentResponse(AttachmentDB):
    """Response model for attachment API endpoints."""

    download_url: Optional[str] = Field(None, description="Temporary download URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL for images")


# Request/Response models for API endpoints


class FileUploadResponse(BaseModel):
    """Response model for file upload endpoints."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="Detected MIME type")
    upload_status: str = Field(..., description="Upload status")
    processing_status: ProcessingStatus = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")


class BatchUploadResponse(BaseModel):
    """Response model for batch file upload."""

    successful_uploads: List[FileUploadResponse] = Field(
        default_factory=list, description="Successfully uploaded files"
    )
    failed_uploads: List[Dict[str, str]] = Field(
        default_factory=list, description="Failed uploads with error messages"
    )
    total_files: int = Field(..., description="Total number of files in batch")
    successful_count: int = Field(..., description="Number of successful uploads")
    failed_count: int = Field(..., description="Number of failed uploads")


class FileMetadataResponse(BaseModel):
    """Response model for file metadata retrieval."""

    file_id: str = Field(..., description="Unique file identifier")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    file_type: FileType = Field(..., description="Categorized file type")
    upload_date: datetime = Field(..., description="Upload timestamp")
    processing_status: ProcessingStatus = Field(
        ..., description="Current processing status"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    analysis_summary: Optional[Dict[str, Any]] = Field(
        None, description="Summarized analysis results"
    )


class UserFileListResponse(BaseModel):
    """Response model for user file listing."""

    files: List[FileMetadataResponse] = Field(
        default_factory=list, description="List of user files"
    )
    total_count: int = Field(..., description="Total number of files")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of files per page")
    has_more: bool = Field(..., description="Whether more files are available")


class StorageStatsResponse(BaseModel):
    """Response model for storage statistics."""

    total_files: int = Field(..., description="Total number of files")
    total_size_bytes: int = Field(..., description="Total storage used in bytes")
    total_size_human: str = Field(..., description="Human-readable storage size")
    files_by_type: Dict[str, int] = Field(
        default_factory=dict, description="File count by type"
    )
    storage_limit_bytes: Optional[int] = Field(
        None, description="Storage limit in bytes"
    )
    usage_percentage: Optional[float] = Field(
        None, description="Storage usage percentage"
    )


# AI Analysis Models


class DocumentAnalysisRequest(BaseModel):
    """Request model for document AI analysis."""

    file_id: str = Field(..., description="File ID to analyze")
    analysis_type: str = Field(
        default="general", description="Type of analysis to perform"
    )
    context: Optional[str] = Field(None, description="Additional context for analysis")


class DocumentAnalysisResult(BaseModel):
    """Model for AI document analysis results."""

    file_id: str = Field(..., description="Analyzed file ID")
    analysis_type: str = Field(..., description="Type of analysis performed")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    key_information: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted key information"
    )
    travel_relevance: Optional[Dict[str, Any]] = Field(
        None, description="Travel-related information"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Analysis confidence score"
    )
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )


class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis endpoints."""

    analysis_id: str = Field(..., description="Unique analysis identifier")
    file_id: str = Field(..., description="Analyzed file ID")
    status: str = Field(..., description="Analysis status")
    results: Optional[DocumentAnalysisResult] = Field(
        None, description="Analysis results if completed"
    )
    message: str = Field(..., description="Status message")


# Error Models


class FileValidationError(BaseModel):
    """Model for file validation errors."""

    filename: str = Field(..., description="Name of the problematic file")
    error_type: str = Field(..., description="Type of validation error")
    error_message: str = Field(..., description="Detailed error message")
    file_size: Optional[int] = Field(None, description="File size if available")


class FileProcessingError(BaseModel):
    """Model for file processing errors."""

    file_id: Optional[str] = Field(None, description="File ID if available")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error description")
    retry_possible: bool = Field(
        default=False, description="Whether operation can be retried"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )


# Chat Integration Models


class ChatAttachment(BaseModel):
    """Model for attachments within chat messages."""

    attachment_id: str = Field(..., description="Reference to attachment record")
    filename: str = Field(..., description="Display filename")
    file_type: FileType = Field(..., description="File type for UI rendering")
    file_size: int = Field(..., description="File size for display")
    processing_status: ProcessingStatus = Field(..., description="Processing status")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL if available")
    analysis_summary: Optional[str] = Field(None, description="Brief analysis summary")


class MessageWithAttachments(BaseModel):
    """Extended message model including attachments."""

    message_id: str = Field(..., description="Message identifier")
    content: str = Field(..., description="Message text content")
    attachments: List[ChatAttachment] = Field(
        default_factory=list, description="Message attachments"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
