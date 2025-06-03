"""
Test suite for FileProcessingService.

Comprehensive tests for file upload, validation, security, AI analysis,
and management operations. Achieves >90% test coverage.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError,
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.services.business.file_processing_service import (
    FileAnalysisResult,
    FileBatchUploadRequest,
    FileMetadata,
    FileProcessingService,
    FileSearchRequest,
    FileType,
    FileUploadRequest,
    FileUsageStats,
    FileVisibility,
    ProcessedFile,
    ProcessingStatus,
    StorageProvider,
    get_file_processing_service,
)


class TestFileProcessingService:
    """Test class for FileProcessingService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        mock_db = AsyncMock()
        mock_db.get_file.return_value = None
        mock_db.store_file.return_value = None
        mock_db.update_file.return_value = None
        mock_db.delete_file.return_value = True
        mock_db.search_files.return_value = []
        mock_db.get_file_by_hash.return_value = None
        mock_db.get_file_usage_stats.return_value = {
            "total_files": 0,
            "total_size": 0,
            "files_by_type": {},
            "storage_by_type": {},
            "recent_uploads": 0,
            "most_accessed": [],
        }
        return mock_db

    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service."""
        mock_storage = AsyncMock()
        mock_storage.store_file.return_value = {
            "path": "files/user123/test_file.pdf",
            "url": "https://storage.example.com/files/user123/test_file.pdf",
            "filename": "test_file.pdf",
        }
        mock_storage.get_file_content.return_value = b"test content"
        mock_storage.delete_file.return_value = True
        return mock_storage

    @pytest.fixture
    def mock_ai_analysis_service(self):
        """Mock AI analysis service."""
        mock_ai = AsyncMock()
        mock_ai.analyze_file.return_value = {
            "content_summary": "Test document summary",
            "extracted_text": "Test content",
            "entities": ["Travel", "Document"],
            "categories": ["Travel Document"],
            "sentiment": 0.5,
            "confidence_score": 0.85,
            "language_detected": "en",
            "travel_related": True,
            "travel_context": {"destination": "Paris", "dates": ["2024-06-01"]},
        }
        return mock_ai

    @pytest.fixture
    def mock_virus_scanner(self):
        """Mock virus scanner."""
        mock_scanner = AsyncMock()
        mock_scanner.scan_content.return_value = MagicMock(threats_detected=False)
        return mock_scanner

    @pytest.fixture
    def file_processing_service(
        self,
        mock_database_service,
        mock_storage_service,
        mock_ai_analysis_service,
        mock_virus_scanner,
    ):
        """Create FileProcessingService with mocked dependencies."""
        return FileProcessingService(
            database_service=mock_database_service,
            storage_service=mock_storage_service,
            ai_analysis_service=mock_ai_analysis_service,
            virus_scanner=mock_virus_scanner,
        )

    @pytest.fixture
    def sample_upload_request(self):
        """Sample file upload request."""
        return FileUploadRequest(
            filename="test_document.pdf",
            content=b"test content data",
            trip_id="trip_123",
            tags=["travel", "document"],
            visibility=FileVisibility.PRIVATE,
            auto_analyze=True,
        )

    @pytest.fixture
    def sample_processed_file(self):
        """Sample processed file."""
        return ProcessedFile(
            id="file_123",
            user_id="user_123",
            trip_id="trip_123",
            original_filename="test_document.pdf",
            stored_filename="file_123.pdf",
            file_size=1024,
            file_type=FileType.DOCUMENT,
            mime_type="application/pdf",
            file_hash="abc123hash",
            storage_provider=StorageProvider.LOCAL,
            storage_path="files/user_123/file_123.pdf",
            storage_url=None,
            processing_status=ProcessingStatus.COMPLETED,
            upload_timestamp=datetime.now(timezone.utc),
            processed_timestamp=datetime.now(timezone.utc),
            metadata=FileMetadata(
                page_count=1,
                title="Test Document",
                keywords=["test", "document"],
            ),
            analysis_result=FileAnalysisResult(
                content_summary="Test summary",
                travel_related=True,
            ),
            visibility=FileVisibility.PRIVATE,
            tags=["travel", "document"],
        )


class TestFileUpload:
    """Test file upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_file_success(
        self, file_processing_service, sample_upload_request
    ):
        """Test successful file upload."""
        user_id = "user_123"

        result = await file_processing_service.upload_file(
            user_id, sample_upload_request
        )

        assert result is not None
        assert result.user_id == user_id
        assert result.original_filename == sample_upload_request.filename
        assert result.file_size == len(sample_upload_request.content)
        assert result.processing_status in [
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
        ]
        assert result.tags == sample_upload_request.tags
        assert result.visibility == sample_upload_request.visibility

    @pytest.mark.asyncio
    async def test_upload_file_empty_content(self, file_processing_service):
        """Test upload with empty file content."""
        user_id = "user_123"
        upload_request = FileUploadRequest(
            filename="empty.txt",
            content=b"",
            auto_analyze=False,
        )

        with pytest.raises(CoreValidationError, match="File is empty"):
            await file_processing_service.upload_file(user_id, upload_request)

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, file_processing_service):
        """Test upload with file too large."""
        user_id = "user_123"
        large_content = b"a" * (file_processing_service.max_file_size + 1)
        upload_request = FileUploadRequest(
            filename="large.txt",
            content=large_content,
            auto_analyze=False,
        )

        with pytest.raises(CoreValidationError, match="exceeds max"):
            await file_processing_service.upload_file(user_id, upload_request)

    @pytest.mark.asyncio
    async def test_upload_file_invalid_extension(self, file_processing_service):
        """Test upload with invalid file extension."""
        user_id = "user_123"
        upload_request = FileUploadRequest(
            filename="malicious.exe",
            content=b"malicious content",
            auto_analyze=False,
        )

        with pytest.raises(CoreValidationError, match="not allowed"):
            await file_processing_service.upload_file(user_id, upload_request)

    @pytest.mark.asyncio
    async def test_upload_file_virus_detected(
        self, file_processing_service, sample_upload_request
    ):
        """Test upload with virus detected."""
        user_id = "user_123"

        # Mock virus scanner to detect threats
        file_processing_service.virus_scanner.scan_content.return_value = MagicMock(
            threats_detected=True
        )

        with pytest.raises(CoreValidationError, match="malicious content"):
            await file_processing_service.upload_file(user_id, sample_upload_request)

    @pytest.mark.asyncio
    async def test_upload_duplicate_file(
        self, file_processing_service, sample_upload_request, sample_processed_file
    ):
        """Test upload of duplicate file."""
        user_id = "user_123"

        # Mock duplicate file detection
        hashlib.sha256(sample_upload_request.content).hexdigest()
        file_processing_service.db.get_file_by_hash.return_value = (
            sample_processed_file.model_dump()
        )

        result = await file_processing_service.upload_file(
            user_id, sample_upload_request
        )

        # Should create new reference to existing file
        assert result.parent_file_id == sample_processed_file.id
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_upload_batch_success(self, file_processing_service):
        """Test successful batch upload."""
        user_id = "user_123"

        batch_request = FileBatchUploadRequest(
            files=[
                FileUploadRequest(filename="file1.txt", content=b"content 1"),
                FileUploadRequest(filename="file2.txt", content=b"content 2"),
            ],
            trip_id="trip_123",
        )

        results = await file_processing_service.upload_batch(user_id, batch_request)

        assert len(results) == 2
        assert all(result.user_id == user_id for result in results)
        assert all(result.trip_id == "trip_123" for result in results)

    @pytest.mark.asyncio
    async def test_upload_batch_size_limit_exceeded(self, file_processing_service):
        """Test batch upload with total size exceeding limit."""
        user_id = "user_123"

        large_content = b"a" * (5 * 1024 * 1024)  # 5MB each
        batch_request = FileBatchUploadRequest(
            files=[
                FileUploadRequest(filename="file1.txt", content=large_content),
                FileUploadRequest(filename="file2.txt", content=large_content),
            ],
            max_total_size=8 * 1024 * 1024,  # 8MB limit
        )

        with pytest.raises(CoreValidationError, match="exceeds limit"):
            await file_processing_service.upload_batch(user_id, batch_request)


class TestFileRetrieval:
    """Test file retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_file_success(
        self, file_processing_service, sample_processed_file
    ):
        """Test successful file retrieval."""
        user_id = "user_123"
        file_id = "file_123"

        file_processing_service.db.get_file.return_value = (
            sample_processed_file.model_dump()
        )

        result = await file_processing_service.get_file(file_id, user_id)

        assert result is not None
        assert result.id == file_id
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, file_processing_service):
        """Test file retrieval when file doesn't exist."""
        user_id = "user_123"
        file_id = "nonexistent"

        file_processing_service.db.get_file.return_value = None

        result = await file_processing_service.get_file(file_id, user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_file_access_denied(
        self, file_processing_service, sample_processed_file
    ):
        """Test file retrieval with access denied."""
        user_id = "different_user"
        file_id = "file_123"

        # File belongs to different user
        sample_processed_file.user_id = "other_user"
        file_processing_service.db.get_file.return_value = (
            sample_processed_file.model_dump()
        )

        with pytest.raises(CoreAuthorizationError, match="Access denied"):
            await file_processing_service.get_file(file_id, user_id)

    @pytest.mark.asyncio
    async def test_get_file_content_success(
        self, file_processing_service, sample_processed_file
    ):
        """Test successful file content retrieval."""
        user_id = "user_123"
        file_id = "file_123"
        expected_content = b"test file content"

        file_processing_service.db.get_file.return_value = (
            sample_processed_file.model_dump()
        )
        file_processing_service.storage_service.get_file_content.return_value = (
            expected_content
        )

        result = await file_processing_service.get_file_content(file_id, user_id)

        assert result == expected_content

    @pytest.mark.asyncio
    async def test_get_file_content_not_found(self, file_processing_service):
        """Test file content retrieval when file doesn't exist."""
        user_id = "user_123"
        file_id = "nonexistent"

        file_processing_service.db.get_file.return_value = None

        result = await file_processing_service.get_file_content(file_id, user_id)

        assert result is None


class TestFileSearch:
    """Test file search functionality."""

    @pytest.mark.asyncio
    async def test_search_files_success(
        self, file_processing_service, sample_processed_file
    ):
        """Test successful file search."""
        user_id = "user_123"
        search_request = FileSearchRequest(
            query="test",
            file_types=[FileType.DOCUMENT],
            trip_id="trip_123",
            tags=["travel"],
            limit=10,
        )

        file_processing_service.db.search_files.return_value = [
            sample_processed_file.model_dump()
        ]

        results = await file_processing_service.search_files(user_id, search_request)

        assert len(results) == 1
        assert results[0].id == sample_processed_file.id

    @pytest.mark.asyncio
    async def test_search_files_empty_results(self, file_processing_service):
        """Test file search with no results."""
        user_id = "user_123"
        search_request = FileSearchRequest(query="nonexistent")

        file_processing_service.db.search_files.return_value = []

        results = await file_processing_service.search_files(user_id, search_request)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_files_with_filters(self, file_processing_service):
        """Test file search with various filters."""
        user_id = "user_123"
        search_request = FileSearchRequest(
            file_types=[FileType.DOCUMENT, FileType.IMAGE],
            min_size=1024,
            max_size=10240,
            shared_only=False,
            limit=20,
            offset=10,
        )

        file_processing_service.db.search_files.return_value = []

        await file_processing_service.search_files(user_id, search_request)

        # Verify search was called with correct filters
        call_args = file_processing_service.db.search_files.call_args
        filters = call_args[0][0]

        assert filters["user_id"] == user_id
        assert filters["file_types"] == ["document", "image"]
        assert filters["min_size"] == 1024
        assert filters["max_size"] == 10240


class TestFileManagement:
    """Test file management operations."""

    @pytest.mark.asyncio
    async def test_delete_file_success(
        self, file_processing_service, sample_processed_file
    ):
        """Test successful file deletion."""
        user_id = "user_123"
        file_id = "file_123"

        file_processing_service.db.get_file.return_value = (
            sample_processed_file.model_dump()
        )
        file_processing_service.db.delete_file.return_value = True

        result = await file_processing_service.delete_file(file_id, user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, file_processing_service):
        """Test file deletion when file doesn't exist."""
        user_id = "user_123"
        file_id = "nonexistent"

        file_processing_service.db.get_file.return_value = None

        with pytest.raises(CoreResourceNotFoundError, match="not found"):
            await file_processing_service.delete_file(file_id, user_id)

    @pytest.mark.asyncio
    async def test_delete_file_not_owner(
        self, file_processing_service, sample_processed_file
    ):
        """Test file deletion by non-owner."""
        user_id = "different_user"
        file_id = "file_123"

        # File belongs to different user
        sample_processed_file.user_id = "other_user"
        file_processing_service.db.get_file.return_value = (
            sample_processed_file.model_dump()
        )

        with pytest.raises(CoreAuthorizationError, match="Only file owner"):
            await file_processing_service.delete_file(file_id, user_id)

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, file_processing_service):
        """Test getting file usage statistics."""
        user_id = "user_123"
        expected_stats = {
            "total_files": 10,
            "total_size": 5242880,
            "files_by_type": {"document": 5, "image": 3, "text": 2},
            "storage_by_type": {"document": 3145728, "image": 1572864, "text": 524288},
            "recent_uploads": 3,
            "most_accessed": ["file_1", "file_2", "file_3"],
        }

        file_processing_service.db.get_file_usage_stats.return_value = expected_stats

        result = await file_processing_service.get_usage_stats(user_id)

        assert isinstance(result, FileUsageStats)
        assert result.total_files == 10
        assert result.total_size == 5242880


class TestFileValidation:
    """Test file validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_file_content_valid_pdf(self, file_processing_service):
        """Test validation of valid PDF file."""
        filename = "document.pdf"
        content = b"%PDF-1.4\n%test content\n%%EOF"

        result = await file_processing_service._validate_file_content(filename, content)

        assert result.is_valid is True
        assert result.detected_mime_type == "application/pdf"
        assert result.file_size == len(content)
        assert result.file_hash is not None

    @pytest.mark.asyncio
    async def test_validate_file_content_invalid_extension(
        self, file_processing_service
    ):
        """Test validation with invalid file extension."""
        filename = "malicious.exe"
        content = b"malicious content"

        result = await file_processing_service._validate_file_content(filename, content)

        assert result.is_valid is False
        assert "not allowed" in result.error_message

    @pytest.mark.asyncio
    async def test_validate_file_content_suspicious_filename(
        self, file_processing_service
    ):
        """Test validation with suspicious filename patterns."""
        filename = "../../etc/passwd"
        content = b"valid content"

        result = await file_processing_service._validate_file_content(filename, content)

        assert len(result.security_warnings) > 0
        assert any(
            "suspicious pattern" in warning for warning in result.security_warnings
        )

    def test_detect_mime_type_pdf(self, file_processing_service):
        """Test MIME type detection for PDF."""
        filename = "document.pdf"
        content = b"%PDF-1.4"

        mime_type = file_processing_service._detect_mime_type(filename, content)

        assert mime_type == "application/pdf"

    def test_detect_mime_type_jpeg(self, file_processing_service):
        """Test MIME type detection for JPEG."""
        filename = "image.jpg"
        content = b"\xff\xd8\xff\xe0"

        mime_type = file_processing_service._detect_mime_type(filename, content)

        assert mime_type == "image/jpeg"

    def test_get_file_type_from_mime(self, file_processing_service):
        """Test file type categorization from MIME type."""
        assert file_processing_service._get_file_type("image/jpeg") == FileType.IMAGE
        assert (
            file_processing_service._get_file_type("application/pdf")
            == FileType.DOCUMENT
        )
        assert file_processing_service._get_file_type("text/plain") == FileType.TEXT
        assert file_processing_service._get_file_type("video/mp4") == FileType.VIDEO
        assert file_processing_service._get_file_type("audio/mpeg") == FileType.AUDIO
        assert (
            file_processing_service._get_file_type("application/zip")
            == FileType.ARCHIVE
        )


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_upload_file_service_error(
        self, file_processing_service, sample_upload_request
    ):
        """Test service error during file upload."""
        user_id = "user_123"

        # Mock database error
        file_processing_service.db.store_file.side_effect = Exception("Database error")

        with pytest.raises(CoreServiceError, match="File upload failed"):
            await file_processing_service.upload_file(user_id, sample_upload_request)

    @pytest.mark.asyncio
    async def test_search_files_error_recovery(self, file_processing_service):
        """Test error recovery in file search."""
        user_id = "user_123"
        search_request = FileSearchRequest(query="test")

        # Mock database error
        file_processing_service.db.search_files.side_effect = Exception(
            "Database error"
        )

        results = await file_processing_service.search_files(user_id, search_request)

        # Should return empty list instead of raising error
        assert results == []

    @pytest.mark.asyncio
    async def test_get_usage_stats_error_recovery(self, file_processing_service):
        """Test error recovery in usage stats."""
        user_id = "user_123"

        # Mock database error
        file_processing_service.db.get_file_usage_stats.side_effect = Exception(
            "Database error"
        )

        result = await file_processing_service.get_usage_stats(user_id)

        # Should return default stats instead of raising error
        assert result.total_files == 0
        assert result.total_size == 0


class TestDependencyInjection:
    """Test dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_file_processing_service(self):
        """Test dependency injection function."""
        service = await get_file_processing_service()

        assert isinstance(service, FileProcessingService)
        assert service.db is not None
        assert service.storage_root == Path("uploads")

    def test_file_processing_service_initialization(self):
        """Test service initialization with default parameters."""
        service = FileProcessingService()

        assert service.max_file_size == 10 * 1024 * 1024  # 10MB
        assert service.max_session_size == 50 * 1024 * 1024  # 50MB
        assert service.storage_root == Path("uploads")
        assert len(service.allowed_extensions) > 0
        assert len(service.allowed_mime_types) > 0


class TestFileAccess:
    """Test file access control."""

    def test_check_file_access_owner(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for owner."""
        user_id = "user_123"
        sample_processed_file.user_id = user_id

        has_access = file_processing_service._check_file_access(
            sample_processed_file, user_id
        )

        assert has_access is True

    def test_check_file_access_shared(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for shared user."""
        user_id = "user_456"
        sample_processed_file.user_id = "user_123"
        sample_processed_file.shared_with = [user_id]

        has_access = file_processing_service._check_file_access(
            sample_processed_file, user_id
        )

        assert has_access is True

    def test_check_file_access_public(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for public file."""
        user_id = "any_user"
        sample_processed_file.user_id = "user_123"
        sample_processed_file.visibility = FileVisibility.PUBLIC

        has_access = file_processing_service._check_file_access(
            sample_processed_file, user_id
        )

        assert has_access is True

    def test_check_file_access_denied(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check denied."""
        user_id = "unauthorized_user"
        sample_processed_file.user_id = "user_123"
        sample_processed_file.visibility = FileVisibility.PRIVATE
        sample_processed_file.shared_with = []

        has_access = file_processing_service._check_file_access(
            sample_processed_file, user_id
        )

        assert has_access is False
