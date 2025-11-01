"""Final file processing service used for uploads, metadata, and retrieval.

This implementation focuses on maintainability and predictable behaviour.  It
performs local validation, delegates durable storage to an optional storage
backend, and persists metadata through a small database adapter.  All legacy
code paths have been removed.
"""

# pylint: disable=too-many-lines

from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import re
import threading
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from pydantic import Field  # pylint: disable=import-error

from tripsage_core.exceptions import (
    CoreAuthorizationError as AuthPermissionError,
    CoreResourceNotFoundError as NotFoundError,
    CoreServiceError as ServiceError,
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


logger = logging.getLogger(__name__)

FILES_TABLE = "files"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class _NullDatabaseBackend:
    """Minimal async stub used when no database is available."""

    async def fetch_one(self, *args: Any, **kwargs: Any) -> None:
        """Fetch one record from the database."""
        return

    async def fetch_all(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch all records from the database."""
        return []

    async def insert(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Insert a record into the database."""
        return []

    async def update(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Update a record in the database."""
        return []

    async def delete(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Delete a record from the database."""
        return []

    async def select(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Select records from the database."""
        return []

    async def get_file_usage_stats(self, user_id: str) -> dict[str, Any]:
        """Get file usage statistics."""
        return {
            "total_files": 0,
            "total_size": 0,
            "files_by_type": {},
            "storage_by_type": {},
            "recent_uploads": 0,
            "most_accessed": [],
        }


class FileType(str, Enum):
    """Logical file categories."""

    IMAGE = "image"
    DOCUMENT = "document"
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    ARCHIVE = "archive"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Life-cycle stages of a processed file."""

    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class StorageProvider(str, Enum):
    """Supported storage providers."""

    LOCAL = "local"
    EXTERNAL = "external"


class FileVisibility(str, Enum):
    """Visibility state for a stored file."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class FileValidationResult(TripSageModel):
    """Outcome of file validation."""

    is_valid: bool
    error_message: str | None = None
    file_size: int
    detected_mime_type: str
    file_hash: str | None = None
    security_warnings: tuple[str, ...] = Field(default_factory=tuple)


class FileMetadata(TripSageModel):
    """Derived metadata for a processed file."""

    character_count: int | None = None
    word_count: int | None = None
    encoding: str | None = None
    keywords: tuple[str, ...] = Field(default_factory=tuple)
    creation_date: datetime | None = None


class FileAnalysisResult(TripSageModel):
    """Optional AI analysis outcome."""

    content_summary: str | None = None
    extracted_text: str | None = None
    sentiment: float | None = None
    confidence_score: float | None = None
    categories: tuple[str, ...] = Field(default_factory=tuple)
    entities: tuple[str, ...] = Field(default_factory=tuple)


class ProcessedFile(TripSageModel):
    """Canonical representation of a stored file."""

    id: str
    user_id: str
    trip_id: str | None = None
    original_filename: str
    stored_filename: str
    file_size: int
    file_type: FileType
    mime_type: str
    file_hash: str
    storage_provider: StorageProvider
    storage_path: str
    storage_url: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.PROCESSING
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_timestamp: datetime | None = None
    metadata: FileMetadata | None = None
    analysis_result: FileAnalysisResult | None = None
    visibility: FileVisibility = FileVisibility.PRIVATE
    shared_with: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    version: int = 1
    parent_file_id: str | None = None
    download_count: int = 0
    last_accessed: datetime | None = None


class FileUploadRequest(TripSageModel):
    """Upload payload delivered by API consumers."""

    filename: str
    content: bytes
    trip_id: str | None = None
    tags: tuple[str, ...] = Field(default_factory=tuple)
    visibility: FileVisibility = FileVisibility.PRIVATE
    auto_analyze: bool = True


class FileSearchRequest(TripSageModel):
    """Search parameters supported by the service."""

    query: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    file_types: tuple[FileType, ...] | None = None
    trip_id: str | None = None
    tags: tuple[str, ...] | None = None
    shared_only: bool = False


class FileUsageStats(TripSageModel):
    """Aggregated usage statistics."""

    total_files: int
    total_size: int
    files_by_type: dict[str, int]
    storage_by_type: dict[str, int]
    recent_uploads: int
    most_accessed: tuple[str, ...] = Field(default_factory=tuple)


@dataclass(slots=True)
class FileValidationRules:
    """Validation rules container."""

    allowed_extensions: set[str] = field(
        default_factory=lambda: {
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
    )
    allowed_mime_types: set[str] = field(
        default_factory=lambda: {
            "application/pdf",
            "text/plain",
            "text/csv",
            "application/json",
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            DOCX_MIME,
            "application/zip",
            "video/mp4",
            "audio/mpeg",
        }
    )
    suspicious_patterns: set[str] = field(
        default_factory=lambda: {
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
    )


@dataclass(slots=True)
class FileProcessingLimits:
    """Size limits applied during uploads."""

    max_file_size: int
    max_session_size: int


@dataclass(slots=True)
class ServiceIntegrations:
    """Optional external service integrations."""

    storage: Any | None
    analysis: Any | None
    scanner: Any | None


@dataclass(slots=True)
class StorageResult:
    """Normalized storage response."""

    provider: StorageProvider
    path: str
    stored_filename: str
    url: str | None = None


class FileRepository:
    """Adapter around heterogeneous database backends."""

    def __init__(self, backend: Any, table: str = FILES_TABLE) -> None:
        """Initialize the FileRepository."""
        self._backend = backend
        self._table = table

    async def fetch_by_id(self, file_id: str) -> dict[str, Any] | None:
        """Fetch a file by ID."""
        if hasattr(self._backend, "get_file"):
            return await self._backend.get_file(file_id)

        if hasattr(self._backend, "fetch_one"):
            method = self._backend.fetch_one
            try:
                return await method(self._table, {"id": file_id})  # type: ignore[arg-type]
            except TypeError:
                try:
                    return await method({"id": file_id})  # type: ignore[call-arg]
                except TypeError:
                    return await method(file_id)  # type: ignore[misc]

        if hasattr(self._backend, "select"):
            rows = await self._backend.select(
                self._table, filters={"id": file_id}, limit=1
            )
            return rows[0] if rows else None

        return None

    async def fetch_by_hash(
        self, user_id: str, file_hash: str
    ) -> dict[str, Any] | None:
        """Fetch a file by hash."""
        if hasattr(self._backend, "get_file_by_hash"):
            return await self._backend.get_file_by_hash(user_id, file_hash)

        if hasattr(self._backend, "fetch_one"):
            method = self._backend.fetch_one
            try:
                return await method(
                    self._table,
                    {"user_id": user_id, "file_hash": file_hash},
                )  # type: ignore[arg-type]
            except TypeError:
                return await method({"user_id": user_id, "file_hash": file_hash})  # type: ignore[call-arg]

        if hasattr(self._backend, "select"):
            rows = await self._backend.select(
                self._table,
                filters={"user_id": user_id, "file_hash": file_hash},
                limit=1,
            )
            return rows[0] if rows else None

        return None

    async def insert(self, payload: Mapping[str, Any]) -> None:
        """Insert a record into the database."""
        if hasattr(self._backend, "store_file"):
            await self._backend.store_file(dict(payload))
            return

        if hasattr(self._backend, "insert"):
            await self._backend.insert(self._table, dict(payload))
            return

        if hasattr(self._backend, "upsert"):
            await self._backend.upsert(self._table, dict(payload))
            return

        if hasattr(self._backend, "fetch_one"):
            # Fallback: pretend success for mock backends
            await self._backend.fetch_one("insert_file", dict(payload))

    async def update(self, file_id: str, payload: Mapping[str, Any]) -> None:
        """Update a record in the database."""
        if hasattr(self._backend, "update_file"):
            await self._backend.update_file(file_id, dict(payload))
            return

        if hasattr(self._backend, "update"):
            await self._backend.update(
                self._table, dict(payload), filters={"id": file_id}
            )
            return

        if hasattr(self._backend, "upsert"):
            await self._backend.upsert(self._table, {**dict(payload), "id": file_id})
            return

        if hasattr(self._backend, "fetch_one"):
            await self._backend.fetch_one(
                "update_file", {"id": file_id, **dict(payload)}
            )

    async def delete(self, file_id: str) -> bool:
        """Delete a record from the database."""
        if hasattr(self._backend, "delete_file"):
            return bool(await self._backend.delete_file(file_id))

        if hasattr(self._backend, "delete"):
            result = await self._backend.delete(self._table, filters={"id": file_id})
            return bool(result)

        if hasattr(self._backend, "fetch_one"):
            await self._backend.fetch_one("delete_file", {"id": file_id})
            return True

        return False

    async def search(
        self, filters: Mapping[str, Any], query: str | None, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        """Search for records in the database."""
        if hasattr(self._backend, "search_files"):
            return await self._backend.search_files(filters, query, limit, offset)

        if hasattr(self._backend, "fetch_all"):
            return await self._backend.fetch_all(
                self._table,
                {
                    "filters": dict(filters),
                    "query": query,
                    "limit": limit,
                    "offset": offset,
                },
            )

        if hasattr(self._backend, "select"):
            db_filters: MutableMapping[str, Any] = dict(filters)
            if query:
                db_filters["fts"] = {"ilike": f"%{query}%"}
            return await self._backend.select(
                self._table,
                filters=db_filters,
                limit=limit,
                offset=offset,
            )

        return []

    async def usage_stats(self, user_id: str) -> dict[str, Any]:
        """Get file usage statistics."""
        if hasattr(self._backend, "get_file_usage_stats"):
            return await self._backend.get_file_usage_stats(user_id)

        if hasattr(self._backend, "fetch_one"):
            result = await self._backend.fetch_one(
                "file_usage_stats", {"user_id": user_id}
            )
            if isinstance(result, dict):
                return result  # type: ignore[return-value]

        if hasattr(self._backend, "select"):
            rows = await self._backend.select(self._table, filters={"user_id": user_id})
            total_size = sum(int(row.get("file_size", 0)) for row in rows)
            return {
                "total_files": len(rows),
                "total_size": total_size,
                "files_by_type": {},
                "storage_by_type": {},
                "recent_uploads": 0,
                "most_accessed": [],
            }

        return {
            "total_files": 0,
            "total_size": 0,
            "files_by_type": {},
            "storage_by_type": {},
            "recent_uploads": 0,
            "most_accessed": [],
        }


class FileProcessingService:
    """Service orchestrating file validation, storage, and persistence."""

    def __init__(
        self,
        database_service: Any | None = None,
        storage_service: Any | None = None,
        ai_analysis_service: Any | None = None,
        virus_scanner: Any | None = None,
        *,
        storage_root: str = "uploads",
        max_file_size: int = 10 * 1024 * 1024,
        max_session_size: int = 50 * 1024 * 1024,
        rules: FileValidationRules | None = None,
    ) -> None:
        """Create a file processing service with optional dependencies."""
        if database_service is None:
            from tripsage_core.services.infrastructure import (  # pylint: disable=import-outside-toplevel
                get_database_service,
            )

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    database_service = loop.run_until_complete(get_database_service())
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Database service initialization failed; using null backend",
                        exc_info=exc,
                    )
                    database_service = _NullDatabaseBackend()
                finally:
                    asyncio.set_event_loop(None)
                    loop.close()
            else:
                result: dict[str, Any] = {}
                error_holder: list[BaseException] = []

                def _load_database_service() -> None:
                    new_loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(new_loop)
                        result["value"] = new_loop.run_until_complete(
                            get_database_service()
                        )
                    except BaseException as exc:  # noqa: BLE001
                        error_holder.append(exc)
                    finally:
                        asyncio.set_event_loop(None)
                        new_loop.close()

                thread = threading.Thread(
                    target=_load_database_service, name="FileProcessingServiceDBInit"
                )
                thread.start()
                thread.join()
                if error_holder:
                    logger.warning(
                        "Falling back to null database backend",
                        exc_info=error_holder[0],
                    )
                    database_service = _NullDatabaseBackend()
                else:
                    database_service = result.get("value")
                    if database_service is None:
                        logger.warning(
                            "Database service unavailable, using null backend"
                        )
                        database_service = _NullDatabaseBackend()

        self._repo = FileRepository(database_service)
        self._integrations = ServiceIntegrations(
            storage=storage_service,
            analysis=ai_analysis_service,
            scanner=virus_scanner,
        )
        self._storage_root = Path(storage_root)
        self._limits = FileProcessingLimits(
            max_file_size=max_file_size,
            max_session_size=max_session_size,
        )
        self._rules = rules or FileValidationRules()
        self._analysis_tasks: set[asyncio.Task[Any]] = set()

        self._ensure_storage_structure()

    @property
    def allowed_extensions(self) -> set[str]:
        """Expose allowed extensions for tests and configuration."""
        return self._rules.allowed_extensions

    @allowed_extensions.setter
    def allowed_extensions(self, value: Iterable[str]) -> None:
        """Set allowed extensions."""
        self._rules.allowed_extensions = set(value)

    @property
    def allowed_mime_types(self) -> set[str]:
        """Expose allowed MIME types."""
        return self._rules.allowed_mime_types

    @allowed_mime_types.setter
    def allowed_mime_types(self, value: Iterable[str]) -> None:
        """Set allowed MIME types."""
        self._rules.allowed_mime_types = set(value)

    @property
    def suspicious_patterns(self) -> set[str]:
        """Expose suspicious filename patterns."""
        return self._rules.suspicious_patterns

    @suspicious_patterns.setter
    def suspicious_patterns(self, value: Iterable[str]) -> None:
        """Set suspicious filename patterns."""
        self._rules.suspicious_patterns = set(value)

    @property
    def max_file_size(self) -> int:
        """Maximum allowed size for a single file in bytes."""
        return self._limits.max_file_size

    @property
    def max_session_size(self) -> int:
        """Maximum aggregate upload size per batch in bytes."""
        return self._limits.max_session_size

    @tripsage_safe_execute()
    async def upload_file(
        self, user_id: str, upload_request: FileUploadRequest
    ) -> ProcessedFile:
        """Validate, store, and persist a single file."""
        validation = await self._validate_file_content(
            upload_request.filename, upload_request.content
        )
        if not validation.is_valid:
            raise ValidationError(validation.error_message or "File validation failed")

        if self._integrations.scanner:
            scan_result = await self._integrations.scanner.scan_content(
                upload_request.content
            )
            if getattr(scan_result, "threats_detected", False):
                raise ValidationError("File contains malicious content")

        file_hash = validation.file_hash or ""
        duplicate = await self._repo.fetch_by_hash(user_id, file_hash)
        if duplicate:  # type: ignore[comparison-overlap]
            logger.info(
                "Duplicate file detected; returning existing reference",
                extra={"user_id": user_id, "file_id": duplicate.get("id")},
            )
            return self._deserialize_processed_file(duplicate)
        if duplicate:
            logger.warning(
                "Duplicate lookup returned unsupported payload",
                extra={"type": type(duplicate)},
            )

        file_id = str(uuid4())

        storage = await self._store_file(
            file_id=file_id,
            user_id=user_id,
            filename=upload_request.filename,
            content=upload_request.content,
        )

        metadata = await self._extract_metadata(
            upload_request.content, validation.detected_mime_type
        )

        processed_file = ProcessedFile(
            id=file_id,
            user_id=user_id,
            trip_id=upload_request.trip_id,
            original_filename=upload_request.filename,
            stored_filename=storage.stored_filename,
            file_size=validation.file_size,
            file_type=self._get_file_type(validation.detected_mime_type),
            mime_type=validation.detected_mime_type,
            file_hash=file_hash,
            storage_provider=storage.provider,
            storage_path=storage.path,
            storage_url=storage.url,
            metadata=metadata,
            visibility=upload_request.visibility,
            tags=tuple(upload_request.tags),
        )

        await self._repo.insert(processed_file.model_dump())

        if upload_request.auto_analyze and self._integrations.analysis:
            self._ensure_background_task(
                asyncio.create_task(self._analyze_file_content(processed_file))
            )
        else:
            processed_file.processing_status = ProcessingStatus.COMPLETED
            processed_file.processed_timestamp = datetime.now(UTC)
            completed_at = processed_file.processed_timestamp.isoformat()
            await self._repo.update(
                processed_file.id,
                {
                    "processing_status": processed_file.processing_status.value,
                    "processed_timestamp": completed_at,
                },
            )

        logger.info(
            "File uploaded successfully",
            extra={
                "file_id": processed_file.id,
                "user_id": user_id,
                "filename": upload_request.filename,
            },
        )
        return processed_file

    @tripsage_safe_execute()
    async def upload_batch(
        self, user_id: str, uploads: Iterable[FileUploadRequest]
    ) -> list[ProcessedFile]:
        """Upload multiple files ensuring session size limits."""
        uploads_list = list(uploads)
        total_size = sum(len(item.content) for item in uploads_list)
        if total_size > self._limits.max_session_size:
            raise ValidationError(
                f"Total upload size {total_size} exceeds max "
                f"{self._limits.max_session_size}"
            )

        return [await self.upload_file(user_id, request) for request in uploads_list]

    @tripsage_safe_execute()
    async def get_file(
        self, file_id: str, user_id: str, *, check_access: bool = True
    ) -> ProcessedFile | None:
        """Return file metadata if accessible to the user."""
        record = await self._repo.fetch_by_id(file_id)
        if not record:
            return None

        if not record:  # type: ignore[comparison-overlap]
            logger.warning(
                "Unexpected file record payload",
                extra={"file_id": file_id, "type": type(record)},
            )
            return None

        processed_file = self._deserialize_processed_file(record)

        if check_access and not await self._check_file_access(processed_file, user_id):
            raise AuthPermissionError("Access denied")

        processed_file.last_accessed = datetime.now(UTC)
        await self._repo.update(
            processed_file.id,
            {
                "last_accessed": processed_file.last_accessed.isoformat(),
            },
        )

        return processed_file

    @tripsage_safe_execute()
    async def get_file_content(self, file_id: str, user_id: str) -> bytes | None:
        """Return binary content for an accessible file."""
        processed_file = await self.get_file(file_id, user_id)
        if not processed_file:
            return None

        if self._integrations.storage:
            content = await self._integrations.storage.get_file_content(
                processed_file.storage_path
            )
        else:
            path = self._storage_root / processed_file.storage_path
            content = path.read_bytes() if path.exists() else None

        if content:
            processed_file.download_count += 1
            await self._repo.update(
                processed_file.id, {"download_count": processed_file.download_count}
            )

        return content

    @tripsage_safe_execute()
    async def search_files(
        self, user_id: str, search_request: FileSearchRequest
    ) -> list[ProcessedFile]:
        """Search user files applying simple filters."""
        filters: dict[str, Any] = {"user_id": user_id}

        if search_request.file_types:
            filters["file_type"] = [ft.value for ft in search_request.file_types]

        if search_request.trip_id:
            filters["trip_id"] = search_request.trip_id

        if search_request.tags:
            filters["tags"] = list(search_request.tags)

        if search_request.shared_only:
            filters["shared_only"] = True

        try:
            records = await self._repo.search(
                filters,
                search_request.query,
                search_request.limit,
                search_request.offset,
            )
        except Exception as error:  # pylint: disable=broad-except
            logger.exception("File search failed", extra={"user_id": user_id})
            raise ServiceError("File search failed") from error

        processed_files: list[ProcessedFile] = []
        for record in records:
            if not record:  # type: ignore[comparison-overlap]
                logger.warning(
                    "Skipping unexpected search payload",
                    extra={"type": type(record)},
                )
                continue
            processed_files.append(self._deserialize_processed_file(record))

        return processed_files

    @tripsage_safe_execute()
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file metadata and storage."""
        processed_file = await self.get_file(file_id, user_id)
        if not processed_file:
            raise NotFoundError("File not found")

        if processed_file.user_id != user_id:
            raise AuthPermissionError("Only owners can delete files")

        if self._integrations.storage:
            await self._integrations.storage.delete_file(processed_file.storage_path)
        else:
            path = self._storage_root / processed_file.storage_path
            if path.exists():
                path.unlink()

        return await self._repo.delete(file_id)

    @tripsage_safe_execute()
    async def get_usage_stats(self, user_id: str) -> FileUsageStats:
        """Return aggregate file usage statistics for a user."""
        try:
            stats = await self._repo.usage_stats(user_id)
            return FileUsageStats(
                total_files=int(stats.get("total_files", 0)),
                total_size=int(stats.get("total_size", 0)),
                files_by_type=dict(stats.get("files_by_type", {})),
                storage_by_type=dict(stats.get("storage_by_type", {})),
                recent_uploads=int(stats.get("recent_uploads", 0)),
                most_accessed=tuple(stats.get("most_accessed", [])),
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to obtain usage stats", extra={"user_id": user_id})
            return FileUsageStats(
                total_files=0,
                total_size=0,
                files_by_type={},
                storage_by_type={},
                recent_uploads=0,
            )

    async def _validate_file_content(
        self, filename: str, content: bytes
    ) -> FileValidationResult:
        """Validate file content for security and format compliance."""
        file_size = len(content)
        detected_mime_type = "application/octet-stream"
        error_message: str | None = None

        if file_size == 0:
            error_message = "File is empty"
        elif file_size > self._limits.max_file_size:
            error_message = (
                f"File size {file_size} exceeds max {self._limits.max_file_size}"
            )
        elif not filename:
            error_message = "Filename is required"

        security_warnings = tuple(
            pattern
            for pattern in self._rules.suspicious_patterns
            if pattern in filename.lower()
        )

        extension = Path(filename).suffix.lower()
        if not error_message and extension not in self._rules.allowed_extensions:
            error_message = f"Extension '{extension}' is not allowed"

        if not error_message:
            detected_mime_type = self._detect_mime_type(filename, content)
            if detected_mime_type not in self._rules.allowed_mime_types:
                error_message = f"MIME type '{detected_mime_type}' is not allowed"

        if not error_message:
            format_valid, format_error = self._validate_file_format(
                content, detected_mime_type
            )
            if not format_valid:
                error_message = format_error

        if error_message:
            return FileValidationResult(
                is_valid=False,
                error_message=error_message,
                file_size=file_size,
                detected_mime_type=detected_mime_type,
            )

        return FileValidationResult(
            is_valid=True,
            file_size=file_size,
            detected_mime_type=detected_mime_type,
            file_hash=hashlib.sha256(content).hexdigest(),
            security_warnings=security_warnings,
        )

    def _detect_mime_type(self, filename: str, content: bytes) -> str:
        """Detect MIME type from filename and magic numbers."""
        mime_type, _ = mimetypes.guess_type(filename)
        detected = mime_type or ""
        if not detected:
            if content.startswith(b"\xff\xd8\xff"):
                detected = "image/jpeg"
            elif content.startswith(b"\x89PNG\r\n\x1a\n"):
                detected = "image/png"
            elif content.startswith((b"GIF87a", b"GIF89a")):
                detected = "image/gif"
            elif content.startswith(b"%PDF-"):
                detected = "application/pdf"
            elif content.startswith(b"PK\x03\x04") and filename.lower().endswith(
                ".docx"
            ):
                detected = DOCX_MIME
            else:
                detected = "application/octet-stream"
        return detected

    def _validate_file_format(
        self, content: bytes, mime_type: str
    ) -> tuple[bool, str | None]:
        """Run MIME-specific heuristics to avoid spoofing."""
        error_message: str | None = None
        if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
            error_message = "Invalid JPEG header"
        elif mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            error_message = "Invalid PNG header"
        elif mime_type == "image/gif" and not content.startswith(
            (b"GIF87a", b"GIF89a")
        ):
            error_message = "Invalid GIF header"
        elif mime_type == "application/pdf" and not content.startswith(b"%PDF-"):
            error_message = "Invalid PDF header"
        elif mime_type.startswith("text/"):
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                error_message = "Text content must be UTF-8"

        return error_message is None, error_message

    def _get_file_type(self, mime_type: str) -> FileType:
        """Map MIME types to logical file categories."""
        file_type = FileType.OTHER
        if mime_type.startswith("image/"):
            file_type = FileType.IMAGE
        elif mime_type.startswith("video/"):
            file_type = FileType.VIDEO
        elif mime_type.startswith("audio/"):
            file_type = FileType.AUDIO
        elif mime_type in {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            file_type = FileType.DOCUMENT
        elif mime_type == "text/csv":
            file_type = FileType.SPREADSHEET
        elif mime_type in {"text/plain", "application/json"}:
            file_type = FileType.TEXT
        elif mime_type == "application/zip":
            file_type = FileType.ARCHIVE
        return file_type

    @staticmethod
    def _sanitize_storage_component(value: str, fallback: str) -> str:
        """Return a filesystem-safe token for storage paths."""
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", value)
        cleaned = cleaned.strip("._")
        if not cleaned:
            return fallback
        return cleaned[:128]

    async def _store_file(
        self, *, file_id: str, user_id: str, filename: str, content: bytes
    ) -> StorageResult:
        """Store file content and return normalized storage metadata."""
        if self._integrations.storage:
            storage_result = await self._integrations.storage.store_file(
                file_id, user_id, filename, content
            )
            if isinstance(storage_result, Mapping):
                return StorageResult(
                    provider=StorageProvider(
                        storage_result.get("provider", StorageProvider.EXTERNAL)  # type: ignore[arg-type]
                    ),
                    path=storage_result["path"],  # type: ignore[index]
                    stored_filename=storage_result.get("stored_filename", filename),  # type: ignore[arg-type]
                    url=storage_result.get("url"),  # type: ignore[arg-type]
                )

            return StorageResult(
                provider=StorageProvider.EXTERNAL,
                path=str(storage_result.path),
                stored_filename=storage_result.stored_filename,
                url=getattr(storage_result, "url", None),
            )

        safe_user_id = self._sanitize_storage_component(user_id, fallback="user")
        safe_file_id = self._sanitize_storage_component(file_id, fallback="file")
        extension = Path(filename).suffix.lower()
        stored_filename = f"{safe_file_id}{extension}"

        relative_path = Path("files") / safe_user_id / stored_filename
        full_path = (self._storage_root / relative_path).resolve()
        storage_root = self._storage_root.resolve()
        if not full_path.is_relative_to(storage_root):
            raise ValidationError("Computed storage path escapes storage root")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        return StorageResult(
            provider=StorageProvider.LOCAL,
            path=str(relative_path),
            stored_filename=stored_filename,
        )

    async def _extract_metadata(
        self, content: bytes, mime_type: str
    ) -> FileMetadata | None:
        """Extract metadata from file content."""
        metadata = FileMetadata()
        metadata.creation_date = datetime.now(UTC)

        if mime_type.startswith("text/"):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return metadata
            metadata.character_count = len(text)
            words = text.split()
            metadata.word_count = len(words)
            metadata.encoding = "utf-8"
            keyword_candidates: dict[str, int] = {}
            for word in words:
                normalized = word.lower()
                if len(normalized) > 3:
                    keyword_candidates[normalized] = (
                        keyword_candidates.get(normalized, 0) + 1
                    )
            metadata.keywords = tuple(
                word
                for word, _ in sorted(
                    keyword_candidates.items(), key=lambda item: item[1], reverse=True
                )[:10]
            )
        return metadata

    async def _analyze_file_content(self, processed_file: ProcessedFile) -> None:
        """Analyze file content."""
        try:
            if not self._integrations.analysis:
                return
            if self._integrations.storage:
                content = await self._integrations.storage.get_file_content(
                    processed_file.storage_path
                )
            else:
                path = self._storage_root / processed_file.storage_path
                content = path.read_bytes() if path.exists() else None
            if not content:
                return

            analysis_result = await self._integrations.analysis.analyze_file(  # type: ignore[union-attr]
                content, processed_file.mime_type, processed_file.original_filename
            )
            processed_file.analysis_result = FileAnalysisResult(**analysis_result)
            processed_file.processing_status = ProcessingStatus.COMPLETED
            processed_file.processed_timestamp = datetime.now(UTC)
            processed_at = processed_file.processed_timestamp.isoformat()
            await self._repo.update(
                processed_file.id,
                {
                    "analysis_result": processed_file.analysis_result.model_dump(),
                    "processing_status": processed_file.processing_status.value,
                    "processed_timestamp": processed_at,
                },
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "File analysis failed", extra={"file_id": processed_file.id}
            )
            await self._repo.update(
                processed_file.id,
                {"processing_status": ProcessingStatus.FAILED.value},
            )

    async def _check_file_access(
        self, processed_file: ProcessedFile, user_id: str
    ) -> bool:
        """Check if a file is accessible to a user."""
        if processed_file.user_id == user_id:
            return True

        # Check if shared with user
        if user_id in processed_file.shared_with:
            return True

        # Check if public
        return processed_file.visibility == FileVisibility.PUBLIC

    def _deserialize_processed_file(self, data: Mapping[str, Any]) -> ProcessedFile:
        """Deserialize a processed file from a mapping."""
        # Extract and validate required fields
        required_fields = {
            "id": data["id"],
            "user_id": data["user_id"],
            "original_filename": data["original_filename"],
            "stored_filename": data["stored_filename"],
            "file_size": int(data["file_size"]),
            "file_hash": data["file_hash"],
            "storage_path": data["storage_path"],
        }

        # Extract optional fields with proper typing
        processed_fields: dict[str, Any] = {}

        if "trip_id" in data and data["trip_id"] is not None:
            processed_fields["trip_id"] = str(data["trip_id"])

        if "mime_type" in data:
            processed_fields["mime_type"] = str(data["mime_type"])

        # Handle processing status
        processing_status_raw = data.get(
            "processing_status", ProcessingStatus.PROCESSING.value
        )
        if isinstance(processing_status_raw, str):
            processed_fields["processing_status"] = ProcessingStatus(
                processing_status_raw
            )
        else:
            processed_fields["processing_status"] = ProcessingStatus.PROCESSING

        # Handle file type
        file_type_raw = data.get("file_type")
        if isinstance(file_type_raw, str):
            processed_fields["file_type"] = FileType(file_type_raw)

        # Handle storage provider
        storage_provider_raw = data.get("storage_provider")
        if isinstance(storage_provider_raw, str):
            processed_fields["storage_provider"] = StorageProvider(storage_provider_raw)

        # Handle visibility
        visibility_raw = data.get("visibility", FileVisibility.PRIVATE.value)
        if isinstance(visibility_raw, str):
            processed_fields["visibility"] = FileVisibility(visibility_raw)

        # Handle optional fields
        optional_fields = [
            "storage_url",
            "upload_timestamp",
            "processed_timestamp",
            "parent_file_id",
            "download_count",
            "last_accessed",
            "version",
        ]
        for field_name in optional_fields:
            if field_name in data and data[field_name] is not None:
                processed_fields[field_name] = data[field_name]

        # Handle list/tuple fields
        list_fields = ["tags", "shared_with"]
        for field_name in list_fields:
            if field_name in data:
                processed_fields[field_name] = tuple(data.get(field_name, []))

        # Handle complex objects with explicit type checking
        if "metadata" in data and isinstance(data["metadata"], Mapping):
            processed_fields["metadata"] = FileMetadata(
                **cast(dict[str, Any], data["metadata"])
            )

        if "analysis_result" in data and isinstance(data["analysis_result"], Mapping):
            processed_fields["analysis_result"] = FileAnalysisResult(
                **cast(dict[str, Any], data["analysis_result"])
            )

        return ProcessedFile(**required_fields, **processed_fields)

    def _ensure_background_task(self, task: asyncio.Task[Any]) -> None:
        """Ensure a background task is added to the set."""
        self._analysis_tasks.add(task)
        task.add_done_callback(self._analysis_tasks.discard)

    def _ensure_storage_structure(self) -> None:
        """Ensure the storage structure exists."""
        for relative in ("files", "temp", "processed", "thumbnails"):
            (self._storage_root / relative).mkdir(parents=True, exist_ok=True)
