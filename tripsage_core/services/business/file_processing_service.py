"""
File processing service for comprehensive file management operations.

This service consolidates file-related business logic including file upload,
validation, storage, metadata extraction, security scanning, and AI analysis.
It provides clean abstractions over storage providers while maintaining proper
security and data relationships.
"""

import asyncio
import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import Field

from tripsage_core.exceptions import (
    CoreAuthorizationError as PermissionError,
)
from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """File type enumeration."""

    IMAGE = "image"
    DOCUMENT = "document"
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    ARCHIVE = "archive"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """File processing status enumeration."""

    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class StorageProvider(str, Enum):
    """Storage provider enumeration."""

    LOCAL = "local"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"


class FileVisibility(str, Enum):
    """File visibility enumeration."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class FileValidationResult(TripSageModel):
    """File validation result model."""

    is_valid: bool = Field(..., description="Whether file passed validation")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    file_size: int = Field(..., description="File size in bytes")
    detected_mime_type: Optional[str] = Field(None, description="Detected MIME type")
    file_hash: Optional[str] = Field(None, description="SHA256 hash of file content")
    security_warnings: List[str] = Field(default_factory=list, description="Security warnings")


class FileMetadata(TripSageModel):
    """File metadata model."""

    dimensions: Optional[Dict[str, int]] = Field(None, description="Image/video dimensions")
    duration: Optional[float] = Field(None, description="Audio/video duration in seconds")
    page_count: Optional[int] = Field(None, description="Document page count")
    word_count: Optional[int] = Field(None, description="Text word count")
    character_count: Optional[int] = Field(None, description="Text character count")
    encoding: Optional[str] = Field(None, description="Text encoding")
    creation_date: Optional[datetime] = Field(None, description="File creation date")
    modification_date: Optional[datetime] = Field(None, description="File modification date")
    author: Optional[str] = Field(None, description="Document author")
    title: Optional[str] = Field(None, description="Document title")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    language: Optional[str] = Field(None, description="Detected language")


class FileAnalysisResult(TripSageModel):
    """AI analysis result for file content."""

    content_summary: Optional[str] = Field(None, description="AI-generated content summary")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    entities: List[str] = Field(default_factory=list, description="Detected entities")
    categories: List[str] = Field(default_factory=list, description="Content categories")
    sentiment: Optional[float] = Field(None, ge=-1, le=1, description="Sentiment score (-1 to 1)")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Analysis confidence")
    language_detected: Optional[str] = Field(None, description="Detected language")
    travel_related: bool = Field(default=False, description="Whether content is travel-related")
    travel_context: Optional[Dict[str, Any]] = Field(None, description="Travel-specific context")


class ProcessedFile(TripSageModel):
    """Processed file model."""

    id: str = Field(..., description="File ID")
    user_id: str = Field(..., description="Owner user ID")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")

    original_filename: str = Field(..., description="Original filename")
    stored_filename: str = Field(..., description="Storage filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: FileType = Field(..., description="File type category")
    mime_type: str = Field(..., description="MIME type")
    file_hash: str = Field(..., description="SHA256 hash")

    storage_provider: StorageProvider = Field(..., description="Storage provider")
    storage_path: str = Field(..., description="Storage path")
    storage_url: Optional[str] = Field(None, description="Storage URL")

    processing_status: ProcessingStatus = Field(..., description="Processing status")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")
    processed_timestamp: Optional[datetime] = Field(None, description="Processing completion timestamp")

    metadata: Optional[FileMetadata] = Field(None, description="File metadata")
    analysis_result: Optional[FileAnalysisResult] = Field(None, description="AI analysis result")

    visibility: FileVisibility = Field(default=FileVisibility.PRIVATE, description="File visibility")
    shared_with: List[str] = Field(default_factory=list, description="User IDs with access")
    tags: List[str] = Field(default_factory=list, description="File tags")

    version: int = Field(default=1, description="File version")
    parent_file_id: Optional[str] = Field(None, description="Parent file ID for versions")

    # Usage tracking
    download_count: int = Field(default=0, description="Download count")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")


class FileUploadRequest(TripSageModel):
    """File upload request model."""

    filename: str = Field(..., description="Original filename")
    content: bytes = Field(..., description="File content")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    tags: List[str] = Field(default_factory=list, description="File tags")
    visibility: FileVisibility = Field(default=FileVisibility.PRIVATE, description="File visibility")
    auto_analyze: bool = Field(default=True, description="Whether to perform AI analysis")


class FileBatchUploadRequest(TripSageModel):
    """Batch file upload request model."""

    files: List[FileUploadRequest] = Field(..., description="Files to upload")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    max_total_size: int = Field(default=50 * 1024 * 1024, description="Maximum total size in bytes")


class FileSearchRequest(TripSageModel):
    """File search request model."""

    query: Optional[str] = Field(None, description="Search query")
    file_types: Optional[List[FileType]] = Field(None, description="File type filters")
    trip_id: Optional[str] = Field(None, description="Trip ID filter")
    tags: Optional[List[str]] = Field(None, description="Tag filters")
    date_from: Optional[datetime] = Field(None, description="Date range start")
    date_to: Optional[datetime] = Field(None, description="Date range end")
    min_size: Optional[int] = Field(None, description="Minimum file size")
    max_size: Optional[int] = Field(None, description="Maximum file size")
    shared_only: bool = Field(default=False, description="Only shared files")
    limit: int = Field(default=20, ge=1, le=100, description="Result limit")
    offset: int = Field(default=0, ge=0, description="Result offset")


class FileUsageStats(TripSageModel):
    """File usage statistics model."""

    total_files: int = Field(..., description="Total number of files")
    total_size: int = Field(..., description="Total storage used in bytes")
    files_by_type: Dict[str, int] = Field(..., description="File count by type")
    storage_by_type: Dict[str, int] = Field(..., description="Storage used by type")
    recent_uploads: int = Field(..., description="Files uploaded in last 7 days")
    most_accessed: List[str] = Field(..., description="Most accessed file IDs")


class FileProcessingService:
    """
    Comprehensive file processing service for upload, storage, and analysis.

    This service handles:
    - File upload and validation with security checks
    - Multiple storage provider support (local, cloud)
    - File metadata extraction and analysis
    - AI-powered content analysis and categorization
    - File versioning and deduplication
    - File sharing and permission management
    - File search and indexing
    - Batch processing capabilities
    - Usage analytics and optimization
    """

    def __init__(
        self,
        database_service=None,
        storage_service=None,
        ai_analysis_service=None,
        virus_scanner=None,
        storage_root: str = "uploads",
        max_file_size: int = 10 * 1024 * 1024,
        max_session_size: int = 50 * 1024 * 1024,
    ):
        """
        Initialize the file processing service.

        Args:
            database_service: Database service for persistence
            storage_service: File storage service
            ai_analysis_service: AI analysis service for content processing
            virus_scanner: Virus scanning service
            storage_root: Root directory for local storage
            max_file_size: Maximum individual file size
            max_session_size: Maximum total session size
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        if storage_service is None:
            try:
                from tripsage_core.services.external_apis.storage_service import (
                    StorageService,
                )

                storage_service = StorageService()
            except ImportError:
                logger.warning("External storage service not available, using local storage")
                storage_service = None

        if ai_analysis_service is None:
            try:
                from tripsage_core.services.external_apis.document_analyzer import (
                    DocumentAnalyzer as AIAnalysisService,
                )

                ai_analysis_service = AIAnalysisService()
            except ImportError:
                logger.warning("AI analysis service not available")
                ai_analysis_service = None

        if virus_scanner is None:
            try:
                from tripsage_core.services.external_apis.virus_scanner import (
                    VirusScanner,
                )

                virus_scanner = VirusScanner()
            except ImportError:
                logger.warning("Virus scanner not available")
                virus_scanner = None

        self.db = database_service
        self.storage_service = storage_service
        self.ai_analysis_service = ai_analysis_service
        self.virus_scanner = virus_scanner

        self.storage_root = Path(storage_root)
        self.max_file_size = max_file_size
        self.max_session_size = max_session_size

        # Create storage directories
        self._ensure_storage_structure()

        # Configuration
        self.allowed_mime_types = {
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
            "video/mp4",
            "audio/mpeg",
        }

        self.allowed_extensions = {
            ".pdf",
            ".txt",
            ".csv",
            ".json",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".docx",
            ".zip",
            ".mp4",
            ".mp3",
        }

        self.suspicious_patterns = {
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

    def _ensure_storage_structure(self) -> None:
        """Ensure storage directory structure exists."""
        self.storage_root.mkdir(exist_ok=True)
        (self.storage_root / "files").mkdir(exist_ok=True)
        (self.storage_root / "temp").mkdir(exist_ok=True)
        (self.storage_root / "processed").mkdir(exist_ok=True)
        (self.storage_root / "thumbnails").mkdir(exist_ok=True)

    async def upload_file(self, user_id: str, upload_request: FileUploadRequest) -> ProcessedFile:
        """
        Upload and process a single file.

        Args:
            user_id: User ID
            upload_request: File upload request

        Returns:
            Processed file information

        Raises:
            ValidationError: If file validation fails
            ServiceError: If processing fails
        """
        try:
            # Validate file
            validation_result = await self._validate_file_content(upload_request.filename, upload_request.content)

            if not validation_result.is_valid:
                raise ValidationError(validation_result.error_message)

            # Security scan
            if self.virus_scanner:
                scan_result = await self.virus_scanner.scan_content(upload_request.content)
                if scan_result.threats_detected:
                    raise ValidationError("File contains malicious content")

            # Generate file ID and metadata
            file_id = str(uuid4())
            file_hash = validation_result.file_hash

            # Check for duplicate files
            existing_file = await self._check_duplicate(user_id, file_hash)
            if existing_file:
                logger.info(
                    "Duplicate file detected, linking to existing",
                    extra={
                        "file_id": file_id,
                        "existing_file_id": existing_file.id,
                        "user_id": user_id,
                    },
                )
                # Create new reference to existing file
                return await self._create_file_reference(existing_file, upload_request, user_id)

            # Store file
            storage_result = await self._store_file(file_id, user_id, upload_request.filename, upload_request.content)

            # Extract file metadata
            metadata = await self._extract_metadata(
                upload_request.content,
                validation_result.detected_mime_type,
                upload_request.filename,
            )

            # Create processed file record
            processed_file = ProcessedFile(
                id=file_id,
                user_id=user_id,
                trip_id=upload_request.trip_id,
                original_filename=upload_request.filename,
                stored_filename=storage_result["stored_filename"],
                file_size=validation_result.file_size,
                file_type=self._get_file_type(validation_result.detected_mime_type),
                mime_type=validation_result.detected_mime_type,
                file_hash=file_hash,
                storage_provider=storage_result["provider"],
                storage_path=storage_result["path"],
                storage_url=storage_result.get("url"),
                processing_status=ProcessingStatus.PROCESSING,
                upload_timestamp=datetime.now(timezone.utc),
                metadata=metadata,
                visibility=upload_request.visibility,
                tags=upload_request.tags,
            )

            # Store in database
            await self._store_file_record(processed_file)

            # Schedule AI analysis if requested
            if upload_request.auto_analyze and self.ai_analysis_service:
                asyncio.create_task(self._analyze_file_content(processed_file))
            else:
                # Mark as completed if no analysis needed
                processed_file.processing_status = ProcessingStatus.COMPLETED
                processed_file.processed_timestamp = datetime.now(timezone.utc)
                await self._update_file_record(processed_file)

            logger.info(
                "File uploaded successfully",
                extra={
                    "file_id": file_id,
                    "user_id": user_id,
                    "filename": upload_request.filename,
                    "size": validation_result.file_size,
                },
            )

            return processed_file

        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(
                "File upload failed",
                extra={
                    "user_id": user_id,
                    "filename": upload_request.filename,
                    "error": str(e),
                },
            )
            raise ServiceError(f"File upload failed: {str(e)}") from e

    async def upload_batch(self, user_id: str, batch_request: FileBatchUploadRequest) -> List[ProcessedFile]:
        """
        Upload multiple files in batch.

        Args:
            user_id: User ID
            batch_request: Batch upload request

        Returns:
            List of processed files

        Raises:
            ValidationError: If batch validation fails
            ServiceError: If processing fails
        """
        try:
            # Validate batch size
            total_size = sum(len(file.content) for file in batch_request.files)
            if total_size > batch_request.max_total_size:
                raise ValidationError(f"Batch size {total_size} exceeds limit {batch_request.max_total_size}")

            # Process files concurrently
            tasks = []
            for file_request in batch_request.files:
                if batch_request.trip_id and not file_request.trip_id:
                    file_request.trip_id = batch_request.trip_id

                task = self.upload_file(user_id, file_request)
                tasks.append(task)

            # Wait for all uploads to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_files = []
            errors = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    errors.append(f"File {batch_request.files[i].filename}: {str(result)}")
                else:
                    processed_files.append(result)

            if errors and not processed_files:
                raise ServiceError(f"All files failed: {'; '.join(errors)}")

            logger.info(
                "Batch upload completed",
                extra={
                    "user_id": user_id,
                    "total_files": len(batch_request.files),
                    "successful": len(processed_files),
                    "failed": len(errors),
                },
            )

            return processed_files

        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error("Batch upload failed", extra={"user_id": user_id, "error": str(e)})
            raise ServiceError(f"Batch upload failed: {str(e)}") from e

    async def get_file(self, file_id: str, user_id: str, check_access: bool = True) -> Optional[ProcessedFile]:
        """
        Get file information by ID.

        Args:
            file_id: File ID
            user_id: User ID for access control
            check_access: Whether to check access permissions

        Returns:
            File information or None if not found
        """
        try:
            file_data = await self.db.get_file(file_id)
            if not file_data:
                return None

            processed_file = ProcessedFile(**file_data)

            # Check access permissions
            if check_access and not await self._check_file_access(processed_file, user_id):
                raise PermissionError("Access denied to file")

            # Update last accessed timestamp
            processed_file.last_accessed = datetime.now(timezone.utc)
            await self._update_file_record(processed_file)

            return processed_file

        except PermissionError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get file",
                extra={"file_id": file_id, "user_id": user_id, "error": str(e)},
            )
            return None

    async def get_file_content(self, file_id: str, user_id: str) -> Optional[bytes]:
        """
        Get file content by ID.

        Args:
            file_id: File ID
            user_id: User ID for access control

        Returns:
            File content bytes or None if not found
        """
        try:
            processed_file = await self.get_file(file_id, user_id)
            if not processed_file:
                return None

            # Get content from storage
            if self.storage_service:
                content = await self.storage_service.get_file_content(processed_file.storage_path)
            else:
                # Local storage fallback
                file_path = self.storage_root / processed_file.storage_path
                if file_path.exists():
                    content = file_path.read_bytes()
                else:
                    content = None

            if content:
                # Update download count
                processed_file.download_count += 1
                await self._update_file_record(processed_file)

            return content

        except Exception as e:
            logger.error(
                "Failed to get file content",
                extra={"file_id": file_id, "user_id": user_id, "error": str(e)},
            )
            return None

    async def search_files(self, user_id: str, search_request: FileSearchRequest) -> List[ProcessedFile]:
        """
        Search files for a user.

        Args:
            user_id: User ID
            search_request: Search parameters

        Returns:
            List of matching files
        """
        try:
            filters = {"user_id": user_id}

            if search_request.file_types:
                filters["file_types"] = [ft.value for ft in search_request.file_types]

            if search_request.trip_id:
                filters["trip_id"] = search_request.trip_id

            if search_request.tags:
                filters["tags"] = search_request.tags

            if search_request.date_from:
                filters["date_from"] = search_request.date_from

            if search_request.date_to:
                filters["date_to"] = search_request.date_to

            if search_request.min_size:
                filters["min_size"] = search_request.min_size

            if search_request.max_size:
                filters["max_size"] = search_request.max_size

            if search_request.shared_only:
                filters["shared_only"] = True

            results = await self.db.search_files(
                filters,
                search_request.query,
                search_request.limit,
                search_request.offset,
            )

            processed_files = []
            for result in results:
                processed_files.append(ProcessedFile(**result))

            return processed_files

        except Exception as e:
            logger.error("File search failed", extra={"user_id": user_id, "error": str(e)})
            return []

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        Delete a file and its content.

        Args:
            file_id: File ID
            user_id: User ID for access control

        Returns:
            True if deleted successfully
        """
        try:
            processed_file = await self.get_file(file_id, user_id)
            if not processed_file:
                raise NotFoundError("File not found")

            # Check ownership or edit permissions
            if processed_file.user_id != user_id:
                raise PermissionError("Only file owner can delete")

            # Delete from storage
            if self.storage_service:
                await self.storage_service.delete_file(processed_file.storage_path)
            else:
                # Local storage fallback
                file_path = self.storage_root / processed_file.storage_path
                if file_path.exists():
                    file_path.unlink()

            # Delete from database
            success = await self.db.delete_file(file_id)

            if success:
                logger.info(
                    "File deleted successfully",
                    extra={"file_id": file_id, "user_id": user_id},
                )

            return success

        except (NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete file",
                extra={"file_id": file_id, "user_id": user_id, "error": str(e)},
            )
            return False

    async def get_usage_stats(self, user_id: str) -> FileUsageStats:
        """
        Get file usage statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Usage statistics
        """
        try:
            stats_data = await self.db.get_file_usage_stats(user_id)
            return FileUsageStats(**stats_data)

        except Exception as e:
            logger.error(
                "Failed to get usage stats",
                extra={"user_id": user_id, "error": str(e)},
            )
            return FileUsageStats(
                total_files=0,
                total_size=0,
                files_by_type={},
                storage_by_type={},
                recent_uploads=0,
                most_accessed=[],
            )

    async def _validate_file_content(self, filename: str, content: bytes) -> FileValidationResult:
        """Validate file content and metadata."""
        file_size = len(content)
        file_hash = hashlib.sha256(content).hexdigest()
        security_warnings = []

        # Size validation
        if file_size == 0:
            return FileValidationResult(is_valid=False, error_message="File is empty", file_size=file_size)

        if file_size > self.max_file_size:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File size {file_size} exceeds max {self.max_file_size}",
                file_size=file_size,
            )

        # Filename validation
        if not filename:
            return FileValidationResult(
                is_valid=False,
                error_message="Filename is required",
                file_size=file_size,
            )

        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern in filename.lower():
                security_warnings.append(f"Filename contains suspicious pattern: {pattern}")

        # Extension validation
        file_path = Path(filename)
        if file_path.suffix.lower() not in self.allowed_extensions:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File extension '{file_path.suffix}' is not allowed",
                file_size=file_size,
            )

        # MIME type detection and validation
        detected_mime_type = self._detect_mime_type(filename, content)

        if detected_mime_type not in self.allowed_mime_types:
            return FileValidationResult(
                is_valid=False,
                error_message=f"File type '{detected_mime_type}' is not allowed",
                file_size=file_size,
                detected_mime_type=detected_mime_type,
            )

        # Content validation
        content_valid, content_error = self._validate_file_format(content, detected_mime_type)
        if not content_valid:
            return FileValidationResult(
                is_valid=False,
                error_message=content_error,
                file_size=file_size,
                detected_mime_type=detected_mime_type,
            )

        return FileValidationResult(
            is_valid=True,
            file_size=file_size,
            detected_mime_type=detected_mime_type,
            file_hash=file_hash,
            security_warnings=security_warnings,
        )

    def _detect_mime_type(self, filename: str, content: bytes) -> str:
        """Detect MIME type using filename and content analysis."""
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
            # ZIP-based formats
            if filename.lower().endswith(".docx"):
                return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # noqa: E501

        return "application/octet-stream"

    def _validate_file_format(self, content: bytes, mime_type: str) -> Tuple[bool, Optional[str]]:
        """Validate file format consistency."""
        if mime_type.startswith("image/"):
            return self._validate_image_format(content, mime_type)
        elif mime_type == "application/pdf":
            return self._validate_pdf_format(content)
        elif mime_type in ["text/plain", "text/csv", "application/json"]:
            return self._validate_text_format(content)

        return True, None

    def _validate_image_format(self, content: bytes, mime_type: str) -> Tuple[bool, Optional[str]]:
        """Validate image format."""
        if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
            return False, "Invalid JPEG header"
        elif mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Invalid PNG header"
        elif mime_type == "image/gif" and not (content.startswith(b"GIF87a") or content.startswith(b"GIF89a")):
            return False, "Invalid GIF header"

        return True, None

    def _validate_pdf_format(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """Validate PDF format."""
        if not content.startswith(b"%PDF-"):
            return False, "Invalid PDF header"

        if b"%%EOF" not in content[-1024:]:
            return False, "Invalid PDF structure"

        return True, None

    def _validate_text_format(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """Validate text format."""
        try:
            content.decode("utf-8")
            return True, None
        except UnicodeDecodeError:
            return False, "Text file is not valid UTF-8"

    def _get_file_type(self, mime_type: str) -> FileType:
        """Get file type category from MIME type."""
        if mime_type.startswith("image/"):
            return FileType.IMAGE
        elif mime_type.startswith("video/"):
            return FileType.VIDEO
        elif mime_type.startswith("audio/"):
            return FileType.AUDIO
        elif mime_type in [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            return FileType.DOCUMENT
        elif mime_type in ["text/csv"]:
            return FileType.SPREADSHEET
        elif mime_type in ["text/plain", "text/csv", "application/json"]:
            return FileType.TEXT
        elif mime_type in ["application/zip"]:
            return FileType.ARCHIVE
        else:
            return FileType.OTHER

    async def _check_duplicate(self, user_id: str, file_hash: str) -> Optional[ProcessedFile]:
        """Check for duplicate files by hash."""
        try:
            duplicate_data = await self.db.get_file_by_hash(user_id, file_hash)
            if duplicate_data:
                return ProcessedFile(**duplicate_data)
            return None
        except Exception:
            return None

    async def _create_file_reference(
        self,
        existing_file: ProcessedFile,
        upload_request: FileUploadRequest,
        user_id: str,
    ) -> ProcessedFile:
        """Create a new reference to an existing file."""
        new_file = ProcessedFile(**existing_file.model_dump())
        new_file.id = str(uuid4())
        new_file.user_id = user_id
        new_file.trip_id = upload_request.trip_id
        new_file.tags = upload_request.tags
        new_file.visibility = upload_request.visibility
        new_file.upload_timestamp = datetime.now(timezone.utc)
        new_file.parent_file_id = existing_file.id

        await self._store_file_record(new_file)
        return new_file

    async def _store_file(self, file_id: str, user_id: str, filename: str, content: bytes) -> Dict[str, Any]:
        """Store file content to storage provider."""
        if self.storage_service:
            # Use external storage service
            storage_result = await self.storage_service.store_file(file_id, user_id, filename, content)
            return {
                "provider": StorageProvider.AWS_S3,  # or detect from service
                "path": storage_result["path"],
                "url": storage_result.get("url"),
                "stored_filename": storage_result["filename"],
            }
        else:
            # Local storage fallback
            user_dir = self.storage_root / "files" / user_id
            user_dir.mkdir(parents=True, exist_ok=True)

            file_path = Path(filename)
            stored_filename = f"{file_id}{file_path.suffix.lower()}"
            storage_path = user_dir / stored_filename

            storage_path.write_bytes(content)

            return {
                "provider": StorageProvider.LOCAL,
                "path": str(storage_path.relative_to(self.storage_root)),
                "url": None,
                "stored_filename": stored_filename,
            }

    async def _extract_metadata(self, content: bytes, mime_type: str, filename: str) -> FileMetadata:
        """Extract file metadata."""
        metadata = FileMetadata()

        try:
            # Basic file info
            metadata.creation_date = datetime.now(timezone.utc)

            # Type-specific metadata extraction
            if mime_type.startswith("text/"):
                try:
                    text_content = content.decode("utf-8")
                    metadata.character_count = len(text_content)
                    metadata.word_count = len(text_content.split())
                    metadata.encoding = "utf-8"

                    # Extract keywords (simple approach)
                    words = text_content.lower().split()
                    word_freq = {}
                    for word in words:
                        if len(word) > 3:  # Only consider words longer than 3 chars
                            word_freq[word] = word_freq.get(word, 0) + 1

                    # Get top 10 most frequent words as keywords
                    metadata.keywords = sorted(word_freq.keys(), key=word_freq.get, reverse=True)[:10]

                except UnicodeDecodeError:
                    pass

            elif mime_type == "application/pdf":
                # For PDF, we'd use a library like PyPDF2 here
                # For now, just set basic info
                metadata.title = Path(filename).stem

        except Exception as e:
            logger.warning("Failed to extract metadata", extra={"error": str(e)})

        return metadata

    async def _analyze_file_content(self, processed_file: ProcessedFile) -> None:
        """Perform AI analysis on file content."""
        try:
            if not self.ai_analysis_service:
                return

            # Get file content
            if self.storage_service:
                content = await self.storage_service.get_file_content(processed_file.storage_path)
            else:
                file_path = self.storage_root / processed_file.storage_path
                content = file_path.read_bytes()

            if not content:
                return

            # Perform AI analysis
            analysis_result = await self.ai_analysis_service.analyze_file(
                content, processed_file.mime_type, processed_file.original_filename
            )

            # Update file with analysis results
            processed_file.analysis_result = FileAnalysisResult(**analysis_result)
            processed_file.processing_status = ProcessingStatus.COMPLETED
            processed_file.processed_timestamp = datetime.now(timezone.utc)

            await self._update_file_record(processed_file)

            logger.info(
                "File analysis completed",
                extra={
                    "file_id": processed_file.id,
                    "confidence": analysis_result.get("confidence_score"),
                },
            )

        except Exception as e:
            logger.error(
                "File analysis failed",
                extra={"file_id": processed_file.id, "error": str(e)},
            )

            # Mark as failed
            processed_file.processing_status = ProcessingStatus.FAILED
            await self._update_file_record(processed_file)

    async def _check_file_access(self, processed_file: ProcessedFile, user_id: str) -> bool:
        """Check if user has access to file."""
        # Owner always has access
        if processed_file.user_id == user_id:
            return True

        # Check if shared with user
        if user_id in processed_file.shared_with:
            return True

        # Check if public
        if processed_file.visibility == FileVisibility.PUBLIC:
            return True

        return False

    async def _store_file_record(self, processed_file: ProcessedFile) -> None:
        """Store file record in database."""
        try:
            file_data = processed_file.model_dump()
            await self.db.store_file(file_data)
        except Exception as e:
            logger.error(
                "Failed to store file record",
                extra={"file_id": processed_file.id, "error": str(e)},
            )
            raise

    async def _update_file_record(self, processed_file: ProcessedFile) -> None:
        """Update file record in database."""
        try:
            file_data = processed_file.model_dump()
            await self.db.update_file(processed_file.id, file_data)
        except Exception as e:
            logger.error(
                "Failed to update file record",
                extra={"file_id": processed_file.id, "error": str(e)},
            )


# Dependency function for FastAPI
async def get_file_processing_service() -> FileProcessingService:
    """
    Get file processing service instance for dependency injection.

    Returns:
        FileProcessingService instance
    """
    return FileProcessingService()
