"""
Comprehensive tests for FileProcessingService.

This module provides full test coverage for file processing operations
including upload, validation, storage, metadata extraction, and AI analysis.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError as PermissionError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.file_processing_service import (
    FileAnalysisResult,
    FileBatchUploadRequest,
    FileMetadata,
    FileProcessingService,
    FileSearchRequest,
    FileType,
    FileUploadRequest,
    FileVisibility,
    ProcessedFile,
    ProcessingStatus,
    StorageProvider,
    get_file_processing_service,
)


class TestFileProcessingService:
    """Test suite for FileProcessingService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service."""
        storage = AsyncMock()
        return storage

    @pytest.fixture
    def mock_ai_analysis_service(self):
        """Mock AI analysis service."""
        ai = AsyncMock()
        return ai

    @pytest.fixture
    def mock_virus_scanner(self):
        """Mock virus scanner."""
        scanner = AsyncMock()
        return scanner

    @pytest.fixture
    def file_processing_service(
        self,
        mock_database_service,
        mock_storage_service,
        mock_ai_analysis_service,
        mock_virus_scanner,
    ):
        """Create FileProcessingService instance with mocked dependencies."""
        with patch(
            "tripsage_core.services.business.file_processing_service.Path.mkdir"
        ):
            return FileProcessingService(
                database_service=mock_database_service,
                storage_service=mock_storage_service,
                ai_analysis_service=mock_ai_analysis_service,
                virus_scanner=mock_virus_scanner,
            )

    @pytest.fixture
    def sample_file_content(self):
        """Sample file content for testing."""
        return b"Sample file content for testing purposes"

    @pytest.fixture
    def sample_upload_request(self, sample_file_content):
        """Sample file upload request."""
        return FileUploadRequest(
            filename="test_document.pdf",
            content=sample_file_content,
            trip_id=str(uuid4()),
            tags=["document", "travel"],
            visibility=FileVisibility.PRIVATE,
            auto_analyze=True,
        )

    @pytest.fixture
    def sample_processed_file(self):
        """Sample processed file object."""
        file_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return ProcessedFile(
            id=file_id,
            user_id=user_id,
            trip_id=str(uuid4()),
            original_filename="test_document.pdf",
            stored_filename=f"{file_id}.pdf",
            file_size=1024,
            file_type=FileType.DOCUMENT,
            mime_type="application/pdf",
            file_hash="abc123",
            storage_provider=StorageProvider.LOCAL,
            storage_path=f"files/{user_id}/{file_id}.pdf",
            storage_url=None,
            processing_status=ProcessingStatus.COMPLETED,
            upload_timestamp=now,
            processed_timestamp=now,
            metadata=FileMetadata(page_count=5, title="Test Document"),
            analysis_result=FileAnalysisResult(
                content_summary="Test document summary", travel_related=True
            ),
            visibility=FileVisibility.PRIVATE,
            shared_with=[],
            tags=["document", "travel"],
            version=1,
            download_count=0,
            last_accessed=None,
        )

    async def test_upload_file_success(
        self,
        file_processing_service,
        mock_database_service,
        mock_storage_service,
        mock_virus_scanner,
        sample_upload_request,
    ):
        """Test successful file upload."""
        user_id = str(uuid4())

        # Mock virus scanner
        virus_result = MagicMock()
        virus_result.threats_detected = False
        mock_virus_scanner.scan_content.return_value = virus_result

        # Mock storage service
        mock_storage_service.store_file.return_value = {
            "path": f"files/{user_id}/test.pdf",
            "filename": "test.pdf",
            "url": "https://storage.example.com/test.pdf",
        }

        # Mock database
        mock_database_service.get_file_by_hash.return_value = None
        mock_database_service.store_file.return_value = None

        result = await file_processing_service.upload_file(
            user_id, sample_upload_request
        )

        # Assertions
        assert result.user_id == user_id
        assert result.original_filename == sample_upload_request.filename
        assert result.file_type == FileType.DOCUMENT
        assert result.processing_status == ProcessingStatus.PROCESSING
        assert result.tags == sample_upload_request.tags

        # Verify service calls
        mock_virus_scanner.scan_content.assert_called_once()
        mock_storage_service.store_file.assert_called_once()
        mock_database_service.store_file.assert_called_once()

    async def test_upload_file_malicious_content(
        self, file_processing_service, mock_virus_scanner, sample_upload_request
    ):
        """Test file upload with malicious content."""
        user_id = str(uuid4())

        # Mock virus scanner to detect threats
        virus_result = MagicMock()
        virus_result.threats_detected = True
        mock_virus_scanner.scan_content.return_value = virus_result

        with pytest.raises(ValidationError, match="File contains malicious content"):
            await file_processing_service.upload_file(user_id, sample_upload_request)

    async def test_upload_file_duplicate_detection(
        self,
        file_processing_service,
        mock_database_service,
        mock_virus_scanner,
        sample_upload_request,
        sample_processed_file,
    ):
        """Test duplicate file detection during upload."""
        user_id = str(uuid4())

        # Mock virus scanner
        virus_result = MagicMock()
        virus_result.threats_detected = False
        mock_virus_scanner.scan_content.return_value = virus_result

        # Mock existing file
        mock_database_service.get_file_by_hash.return_value = (
            sample_processed_file.model_dump()
        )
        mock_database_service.store_file.return_value = None

        result = await file_processing_service.upload_file(
            user_id, sample_upload_request
        )

        # Should create new reference to existing file
        assert result.parent_file_id == sample_processed_file.id
        assert result.user_id == user_id

    async def test_upload_file_invalid_extension(
        self, file_processing_service, sample_file_content
    ):
        """Test file upload with invalid extension."""
        user_id = str(uuid4())

        invalid_request = FileUploadRequest(
            filename="test.exe", content=sample_file_content
        )

        with pytest.raises(
            ValidationError, match="File extension '.exe' is not allowed"
        ):
            await file_processing_service.upload_file(user_id, invalid_request)

    async def test_upload_file_empty_content(self, file_processing_service):
        """Test file upload with empty content."""
        user_id = str(uuid4())

        empty_request = FileUploadRequest(filename="test.pdf", content=b"")

        with pytest.raises(ValidationError, match="File is empty"):
            await file_processing_service.upload_file(user_id, empty_request)

    async def test_upload_file_oversized(self, file_processing_service):
        """Test file upload exceeding size limit."""
        user_id = str(uuid4())

        # Create content larger than max size
        large_content = b"x" * (file_processing_service.max_file_size + 1)

        oversized_request = FileUploadRequest(
            filename="test.pdf", content=large_content
        )

        with pytest.raises(ValidationError, match="File size .* exceeds maximum"):
            await file_processing_service.upload_file(user_id, oversized_request)

    async def test_upload_batch_success(
        self,
        file_processing_service,
        mock_database_service,
        mock_storage_service,
        mock_virus_scanner,
        sample_file_content,
    ):
        """Test successful batch file upload."""
        user_id = str(uuid4())
        trip_id = str(uuid4())

        # Mock dependencies
        virus_result = MagicMock()
        virus_result.threats_detected = False
        mock_virus_scanner.scan_content.return_value = virus_result

        mock_storage_service.store_file.return_value = {
            "path": f"files/{user_id}/test.pdf",
            "filename": "test.pdf",
        }

        mock_database_service.get_file_by_hash.return_value = None
        mock_database_service.store_file.return_value = None

        # Create batch request
        files = [
            FileUploadRequest(filename="doc1.pdf", content=sample_file_content),
            FileUploadRequest(filename="doc2.pdf", content=sample_file_content),
        ]

        batch_request = FileBatchUploadRequest(files=files, trip_id=trip_id)

        results = await file_processing_service.upload_batch(user_id, batch_request)

        # Assertions
        assert len(results) == 2
        for result in results:
            assert result.user_id == user_id
            assert result.trip_id == trip_id

    async def test_upload_batch_oversized(self, file_processing_service):
        """Test batch upload exceeding total size limit."""
        user_id = str(uuid4())

        # Create files that exceed batch size limit
        large_content = b"x" * (25 * 1024 * 1024)  # 25MB each
        files = [
            FileUploadRequest(filename="doc1.pdf", content=large_content),
            FileUploadRequest(filename="doc2.pdf", content=large_content),
        ]

        batch_request = FileBatchUploadRequest(files=files)

        with pytest.raises(ValidationError, match="Batch size exceeds limit"):
            await file_processing_service.upload_batch(user_id, batch_request)

    async def test_get_file_success(
        self, file_processing_service, mock_database_service, sample_processed_file
    ):
        """Test successful file retrieval."""
        mock_database_service.get_file.return_value = sample_processed_file.model_dump()
        mock_database_service.update_file.return_value = None

        result = await file_processing_service.get_file(
            sample_processed_file.id, sample_processed_file.user_id
        )

        assert result is not None
        assert result.id == sample_processed_file.id
        assert result.last_accessed is not None
        mock_database_service.update_file.assert_called_once()

    async def test_get_file_not_found(
        self, file_processing_service, mock_database_service
    ):
        """Test file retrieval when file doesn't exist."""
        file_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_file.return_value = None

        result = await file_processing_service.get_file(file_id, user_id)

        assert result is None

    async def test_get_file_access_denied(
        self, file_processing_service, mock_database_service, sample_processed_file
    ):
        """Test file retrieval with access denied."""
        different_user_id = str(uuid4())

        mock_database_service.get_file.return_value = sample_processed_file.model_dump()

        with pytest.raises(PermissionError, match="Access denied to file"):
            await file_processing_service.get_file(
                sample_processed_file.id, different_user_id
            )

    async def test_get_file_content_success(
        self,
        file_processing_service,
        mock_database_service,
        mock_storage_service,
        sample_processed_file,
        sample_file_content,
    ):
        """Test successful file content retrieval."""
        mock_database_service.get_file.return_value = sample_processed_file.model_dump()
        mock_database_service.update_file.return_value = None
        mock_storage_service.get_file_content.return_value = sample_file_content

        result = await file_processing_service.get_file_content(
            sample_processed_file.id, sample_processed_file.user_id
        )

        assert result == sample_file_content
        mock_storage_service.get_file_content.assert_called_once()

    async def test_search_files_success(
        self, file_processing_service, mock_database_service, sample_processed_file
    ):
        """Test successful file search."""
        user_id = str(uuid4())

        search_request = FileSearchRequest(
            query="document", file_types=[FileType.DOCUMENT], tags=["travel"], limit=10
        )

        mock_database_service.search_files.return_value = [
            sample_processed_file.model_dump()
        ]

        results = await file_processing_service.search_files(user_id, search_request)

        assert len(results) == 1
        assert results[0].id == sample_processed_file.id
        mock_database_service.search_files.assert_called_once()

    async def test_delete_file_success(
        self,
        file_processing_service,
        mock_database_service,
        mock_storage_service,
        sample_processed_file,
    ):
        """Test successful file deletion."""
        mock_database_service.get_file.return_value = sample_processed_file.model_dump()
        mock_database_service.update_file.return_value = None
        mock_database_service.delete_file.return_value = True
        mock_storage_service.delete_file.return_value = None

        result = await file_processing_service.delete_file(
            sample_processed_file.id, sample_processed_file.user_id
        )

        assert result is True
        mock_storage_service.delete_file.assert_called_once()
        mock_database_service.delete_file.assert_called_once()

    async def test_delete_file_not_owner(
        self, file_processing_service, mock_database_service, sample_processed_file
    ):
        """Test file deletion by non-owner."""
        different_user_id = str(uuid4())

        mock_database_service.get_file.return_value = sample_processed_file.model_dump()
        mock_database_service.update_file.return_value = None

        with pytest.raises(PermissionError, match="Only file owner can delete"):
            await file_processing_service.delete_file(
                sample_processed_file.id, different_user_id
            )

    async def test_get_usage_stats_success(
        self, file_processing_service, mock_database_service
    ):
        """Test successful usage statistics retrieval."""
        user_id = str(uuid4())

        stats_data = {
            "total_files": 25,
            "total_size": 104857600,  # 100MB
            "files_by_type": {"document": 15, "image": 10},
            "storage_by_type": {"document": 83886080, "image": 20971520},
            "recent_uploads": 5,
            "most_accessed": [str(uuid4()), str(uuid4())],
        }

        mock_database_service.get_file_usage_stats.return_value = stats_data

        result = await file_processing_service.get_usage_stats(user_id)

        assert result.total_files == 25
        assert result.total_size == 104857600
        assert len(result.most_accessed) == 2
        mock_database_service.get_file_usage_stats.assert_called_once()

    def test_detect_mime_type_from_filename(self, file_processing_service):
        """Test MIME type detection from filename."""
        test_cases = [
            ("document.pdf", "application/pdf"),
            ("image.jpg", "image/jpeg"),
            ("text.txt", "text/plain"),
            ("data.csv", "text/csv"),
        ]

        for filename, expected_mime in test_cases:
            result = file_processing_service._detect_mime_type(filename, b"")
            assert result == expected_mime

    def test_detect_mime_type_from_content(self, file_processing_service):
        """Test MIME type detection from content headers."""
        test_cases = [
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"GIF87a", "image/gif"),
            (b"%PDF-1.4", "application/pdf"),
        ]

        for content, expected_mime in test_cases:
            result = file_processing_service._detect_mime_type("unknown", content)
            assert result == expected_mime

    def test_get_file_type_categorization(self, file_processing_service):
        """Test file type categorization."""
        test_cases = [
            ("image/jpeg", FileType.IMAGE),
            ("video/mp4", FileType.VIDEO),
            ("audio/mp3", FileType.AUDIO),
            ("application/pdf", FileType.DOCUMENT),
            ("text/csv", FileType.SPREADSHEET),
            ("text/plain", FileType.TEXT),
            ("application/zip", FileType.ARCHIVE),
            ("application/unknown", FileType.OTHER),
        ]

        for mime_type, expected_type in test_cases:
            result = file_processing_service._get_file_type(mime_type)
            assert result == expected_type

    def test_validate_image_format(self, file_processing_service):
        """Test image format validation."""
        # Valid JPEG
        valid, error = file_processing_service._validate_image_format(
            b"\xff\xd8\xff\xe0", "image/jpeg"
        )
        assert valid is True
        assert error is None

        # Invalid JPEG header
        valid, error = file_processing_service._validate_image_format(
            b"invalid", "image/jpeg"
        )
        assert valid is False
        assert "Invalid JPEG header" in error

    def test_validate_pdf_format(self, file_processing_service):
        """Test PDF format validation."""
        # Valid PDF
        valid, error = file_processing_service._validate_pdf_format(
            b"%PDF-1.4\nsome content\n%%EOF"
        )
        assert valid is True
        assert error is None

        # Invalid PDF header
        valid, error = file_processing_service._validate_pdf_format(b"invalid")
        assert valid is False
        assert "Invalid PDF header" in error

    def test_validate_text_format(self, file_processing_service):
        """Test text format validation."""
        # Valid UTF-8 text
        valid, error = file_processing_service._validate_text_format(
            "Hello, world! 🌍".encode("utf-8")
        )
        assert valid is True
        assert error is None

        # Invalid UTF-8
        valid, error = file_processing_service._validate_text_format(b"\xff\xfe")
        assert valid is False
        assert "not valid UTF-8" in error

    async def test_extract_metadata_text_file(self, file_processing_service):
        """Test metadata extraction for text files."""
        content = b"This is a sample text file with multiple words for testing."

        metadata = await file_processing_service._extract_metadata(
            content, "text/plain", "sample.txt"
        )

        assert metadata.character_count == len(content.decode("utf-8"))
        assert metadata.word_count == 11  # Number of words
        assert metadata.encoding == "utf-8"
        assert len(metadata.keywords) > 0

    async def test_check_file_access_owner(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for owner."""
        has_access = await file_processing_service._check_file_access(
            sample_processed_file, sample_processed_file.user_id
        )
        assert has_access is True

    async def test_check_file_access_shared(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for shared user."""
        shared_user_id = str(uuid4())
        sample_processed_file.shared_with = [shared_user_id]

        has_access = await file_processing_service._check_file_access(
            sample_processed_file, shared_user_id
        )
        assert has_access is True

    async def test_check_file_access_public(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for public file."""
        random_user_id = str(uuid4())
        sample_processed_file.visibility = FileVisibility.PUBLIC

        has_access = await file_processing_service._check_file_access(
            sample_processed_file, random_user_id
        )
        assert has_access is True

    async def test_check_file_access_denied(
        self, file_processing_service, sample_processed_file
    ):
        """Test file access check for denied access."""
        random_user_id = str(uuid4())
        sample_processed_file.visibility = FileVisibility.PRIVATE
        sample_processed_file.shared_with = []

        has_access = await file_processing_service._check_file_access(
            sample_processed_file, random_user_id
        )
        assert has_access is False

    async def test_analyze_file_content_success(
        self,
        file_processing_service,
        mock_storage_service,
        mock_ai_analysis_service,
        sample_processed_file,
        sample_file_content,
    ):
        """Test successful file content analysis."""
        # Mock storage and AI services
        mock_storage_service.get_file_content.return_value = sample_file_content
        mock_ai_analysis_service.analyze_file.return_value = {
            "content_summary": "Test document about travel",
            "travel_related": True,
            "confidence_score": 0.85,
        }

        # Mock database update
        file_processing_service.db.update_file = AsyncMock()

        await file_processing_service._analyze_file_content(sample_processed_file)

        # Verify analysis was performed
        mock_ai_analysis_service.analyze_file.assert_called_once()
        assert sample_processed_file.processing_status == ProcessingStatus.COMPLETED
        assert sample_processed_file.analysis_result is not None

    async def test_service_error_handling(
        self, file_processing_service, mock_database_service, sample_upload_request
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.get_file_by_hash.side_effect = Exception("Database error")

        with pytest.raises(ServiceError, match="File upload failed"):
            await file_processing_service.upload_file(user_id, sample_upload_request)

    def test_get_file_processing_service_dependency(self):
        """Test the dependency injection function."""
        with patch(
            "tripsage_core.services.business.file_processing_service.Path.mkdir"
        ):
            service = get_file_processing_service()
            assert isinstance(service, FileProcessingService)

    async def test_local_storage_fallback(self, tmp_path):
        """Test local storage fallback when external storage unavailable."""
        with patch(
            "tripsage_core.services.business.file_processing_service.Path.mkdir"
        ):
            service = FileProcessingService(
                database_service=AsyncMock(),
                storage_service=None,  # No external storage
                storage_root=str(tmp_path),
            )

        file_id = str(uuid4())
        user_id = str(uuid4())
        filename = "test.txt"
        content = b"test content"

        result = await service._store_file(file_id, user_id, filename, content)

        assert result["provider"] == StorageProvider.LOCAL
        assert "path" in result
        assert result["stored_filename"] == f"{file_id}.txt"
