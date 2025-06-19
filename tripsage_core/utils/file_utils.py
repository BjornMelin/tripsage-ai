"""
File handling utilities for TripSage Core.

This module combines file validation and configuration functionality,
implementing comprehensive file validation including type checking,
size limits, and security scanning following KISS principles.
"""

import hashlib
import mimetypes
from pathlib import Path

from fastapi import UploadFile
from pydantic import BaseModel, Field

# ===== File Configuration Constants =====

# File size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES_PER_REQUEST = 5
MAX_SESSION_SIZE = 50 * 1024 * 1024  # 50MB total per session

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".csv",
    ".json",  # Documents
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",  # Images
    ".docx",  # Office documents
    ".zip",  # Archives
}

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
}

# File type categorization
FILE_TYPE_MAPPING = {
    # Images
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    # Documents
    "application/pdf": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        "document"
    ),
    # Text files
    "text/plain": "text",
    "text/csv": "spreadsheet",
    "application/json": "text",
    # Archives
    "application/zip": "archive",
}

# Storage configuration
DEFAULT_STORAGE_ROOT = "uploads"
TEMP_UPLOAD_DIR = "temp"
PROCESSED_DIR = "processed"

# Security patterns to detect in filenames
SUSPICIOUS_PATTERNS = {
    "..",
    "/",
    "\\",
    "<",
    ">",
    ":",
    '"',
    "|",
    "?",
    "*",
    ".exe",
    ".bat",
    ".cmd",
    ".scr",
    ".pif",
    ".jar",
}

# ===== File Validation Classes and Functions =====


class ValidationResult(BaseModel):
    """Result of file validation."""

    is_valid: bool = Field(..., description="Whether the file passed validation")
    error_message: str | None = Field(
        None, description="Error message if validation failed"
    )
    file_size: int = Field(..., description="File size in bytes")
    detected_type: str | None = Field(None, description="Detected MIME type")
    file_hash: str | None = Field(None, description="SHA256 hash of file content")


async def validate_file(
    file: UploadFile, max_size: int = MAX_FILE_SIZE
) -> ValidationResult:
    """
    Validate uploaded file for security and format compliance.

    Args:
        file: FastAPI UploadFile object
        max_size: Maximum allowed file size in bytes

    Returns:
        ValidationResult with validation status and metadata
    """
    # Read file content for validation
    content = await file.read()
    await file.seek(0)  # Reset file pointer

    file_size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()

    # Size validation
    if file_size == 0:
        return ValidationResult(
            is_valid=False, error_message="File is empty", file_size=file_size
        )

    if file_size > max_size:
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"File size ({file_size} bytes) exceeds maximum allowed size "
                f"({max_size} bytes)"
            ),
            file_size=file_size,
        )

    # Filename security validation
    if not file.filename:
        return ValidationResult(
            is_valid=False, error_message="Filename is required", file_size=file_size
        )

    filename_result = _validate_filename(file.filename)
    if not filename_result[0]:
        return ValidationResult(
            is_valid=False, error_message=filename_result[1], file_size=file_size
        )

    # MIME type validation
    detected_type = _detect_mime_type(file.filename, content)

    if detected_type not in ALLOWED_MIME_TYPES:
        return ValidationResult(
            is_valid=False,
            error_message=f"File type '{detected_type}' is not allowed",
            file_size=file_size,
            detected_type=detected_type,
        )

    # Content-based validation
    content_result = _validate_file_content(content, detected_type)
    if not content_result[0]:
        return ValidationResult(
            is_valid=False,
            error_message=content_result[1],
            file_size=file_size,
            detected_type=detected_type,
        )

    return ValidationResult(
        is_valid=True,
        file_size=file_size,
        detected_type=detected_type,
        file_hash=file_hash,
    )


def _validate_filename(filename: str) -> tuple[bool, str | None]:
    """
    Validate filename for security issues.

    Args:
        filename: Original filename from upload

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in filename.lower():
            return False, f"Filename contains suspicious pattern: {pattern}"

    # Check file extension
    file_path = Path(filename)
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{file_path.suffix}' is not allowed"

    # Length check
    if len(filename) > 255:
        return False, "Filename is too long (max 255 characters)"

    return True, None


def _detect_mime_type(filename: str, content: bytes) -> str:
    """
    Detect MIME type using both filename and content analysis.

    Args:
        filename: Original filename
        content: File content bytes

    Returns:
        Detected MIME type string
    """
    # Try filename-based detection first
    mime_type, _ = mimetypes.guess_type(filename)

    if mime_type:
        return mime_type

    # Content-based detection for common formats
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "image/gif"
    elif content.startswith(b"%PDF-"):
        return "application/pdf"
    elif content.startswith(b"PK\x03\x04"):
        # ZIP-based formats (Office documents)
        if filename.lower().endswith(".docx"):
            return (
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            )
        elif filename.lower().endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.lower().endswith(".pptx"):
            return (
                "application/vnd.openxmlformats-officedocument"
                ".presentationml.presentation"
            )

    # Default to octet-stream for unknown types
    return "application/octet-stream"


def _validate_file_content(content: bytes, mime_type: str) -> tuple[bool, str | None]:
    """
    Validate file content for format consistency and security.

    Args:
        content: File content bytes
        mime_type: Detected MIME type

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic content validation based on type
    if mime_type.startswith("image/"):
        return _validate_image_content(content, mime_type)
    elif mime_type == "application/pdf":
        return _validate_pdf_content(content)
    elif mime_type in ["text/plain", "text/csv", "application/json"]:
        return _validate_text_content(content)

    # For other types, basic validation passed
    return True, None


def _validate_image_content(content: bytes, mime_type: str) -> tuple[bool, str | None]:
    """Validate image file content."""
    # Check for basic image headers
    if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        return False, "Invalid JPEG header"
    elif mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        return False, "Invalid PNG header"
    elif mime_type == "image/gif" and not (
        content.startswith(b"GIF87a") or content.startswith(b"GIF89a")
    ):
        return False, "Invalid GIF header"

    return True, None


def _validate_pdf_content(content: bytes) -> tuple[bool, str | None]:
    """Validate PDF file content."""
    if not content.startswith(b"%PDF-"):
        return False, "Invalid PDF header"

    # Check for PDF trailer
    if b"%%EOF" not in content[-1024:]:
        return False, "Invalid PDF structure - missing EOF marker"

    return True, None


def _validate_text_content(content: bytes) -> tuple[bool, str | None]:
    """Validate text file content."""
    try:
        # Attempt to decode as UTF-8
        content.decode("utf-8")
        return True, None
    except UnicodeDecodeError:
        return False, "Text file is not valid UTF-8"


async def validate_batch_upload(
    files: list[UploadFile], max_total_size: int = MAX_SESSION_SIZE
) -> ValidationResult:
    """
    Validate a batch of files for upload.

    Args:
        files: List of UploadFile objects
        max_total_size: Maximum total size for all files

    Returns:
        ValidationResult for the batch operation
    """
    if not files:
        return ValidationResult(
            is_valid=False, error_message="No files provided", file_size=0
        )

    total_size = 0

    # Pre-calculate total size
    for file in files:
        content = await file.read()
        await file.seek(0)
        total_size += len(content)

    if total_size > max_total_size:
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"Total batch size ({total_size} bytes) exceeds maximum "
                f"({max_total_size} bytes)"
            ),
            file_size=total_size,
        )

    # Validate individual files
    for file in files:
        result = await validate_file(file)
        if not result.is_valid:
            return ValidationResult(
                is_valid=False,
                error_message=f"File '{file.filename}': {result.error_message}",
                file_size=total_size,
            )

    return ValidationResult(is_valid=True, file_size=total_size)


def generate_safe_filename(original_filename: str, user_id: str) -> str:
    """
    Generate a safe filename for storage.

    Args:
        original_filename: Original uploaded filename
        user_id: User ID for isolation

    Returns:
        Safe filename string
    """
    # Extract extension
    file_path = Path(original_filename)
    extension = file_path.suffix.lower()

    # Create hash of original filename for uniqueness
    filename_hash = hashlib.md5(
        original_filename.encode(), usedforsecurity=False
    ).hexdigest()[:8]

    # Generate safe filename with user isolation
    safe_name = f"{user_id}_{filename_hash}{extension}"

    return safe_name


__all__ = [
    # Configuration constants
    "MAX_FILE_SIZE",
    "MAX_FILES_PER_REQUEST",
    "MAX_SESSION_SIZE",
    "ALLOWED_EXTENSIONS",
    "ALLOWED_MIME_TYPES",
    "FILE_TYPE_MAPPING",
    "DEFAULT_STORAGE_ROOT",
    "TEMP_UPLOAD_DIR",
    "PROCESSED_DIR",
    # Validation functions and classes
    "ValidationResult",
    "validate_file",
    "validate_batch_upload",
    "generate_safe_filename",
]
