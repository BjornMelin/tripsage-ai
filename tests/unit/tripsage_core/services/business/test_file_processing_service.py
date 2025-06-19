"""Comprehensive test suite for FileProcessingService.

This module tests the FileProcessingService with realistic test data
that aligns with the actual service implementation and validation logic.
Uses modern pytest patterns and proper mocking.
"""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tripsage_core.exceptions import (
    CoreResourceNotFoundError,
    CoreValidationError,
)
from tripsage_core.services.business.file_processing_service import (
    FileProcessingService,
    FileUploadRequest,
    FileValidationResult,
    FileVisibility,
)


class TestFileProcessingService:
    """Test suite for FileProcessingService functionality."""

    @pytest.fixture
    def mock_database_service(self):
        """Create mock database service."""
        return AsyncMock()

    @pytest.fixture
    def mock_storage_service(self):
        """Create mock storage service."""
        return AsyncMock()

    @pytest.fixture
    def file_processing_service(self, mock_database_service, mock_storage_service):
        """Create FileProcessingService instance with mocked dependencies."""
        service = FileProcessingService(
            database_service=mock_database_service,
            storage_service=mock_storage_service,
            max_file_size=10 * 1024 * 1024,
            max_session_size=50 * 1024 * 1024,
        )
        # Mock the allowed extensions and MIME types to be more permissive for testing
        service.allowed_extensions = {".txt", ".pdf", ".jpg", ".png", ".doc", ".docx"}
        service.allowed_mime_types = {
            "text/plain",
            "application/pdf",
            "image/jpeg",
            "image/png",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        # Disable suspicious pattern checking for tests
        service.suspicious_patterns = []
        return service

    @pytest.fixture
    def sample_user_id(self) -> str:
        """Create sample user ID."""
        return str(uuid4())

    @pytest.fixture
    def valid_text_content(self) -> bytes:
        """Create valid text file content."""
        return b"This is a valid text file content for testing purposes."

    @pytest.fixture
    def sample_upload_request(self, valid_text_content) -> FileUploadRequest:
        """Create sample file upload request with valid content."""
        return FileUploadRequest(
            filename="test_document.txt",
            content=valid_text_content,
            trip_id=str(uuid4()),
            tags=["documents", "travel"],
            visibility=FileVisibility.PRIVATE,
            auto_analyze=True,
        )

    # Test File Validation

    @pytest.mark.asyncio
    async def test_validate_file_content_accepts_valid_text_file(
        self,
        file_processing_service: FileProcessingService,
        valid_text_content: bytes,
    ):
        """Test file validation accepts valid text content."""
        # Act
        result = await file_processing_service._validate_file_content(
            "test.txt", valid_text_content
        )

        # Assert
        assert isinstance(result, FileValidationResult)
        assert result.is_valid is True
        assert result.file_size == len(valid_text_content)
        assert result.file_hash is not None

    @pytest.mark.asyncio
    async def test_validate_file_content_rejects_oversized_file(
        self,
        file_processing_service: FileProcessingService,
    ):
        """Test file validation rejects files exceeding size limit."""
        # Arrange - Create oversized content
        oversized_content = b"x" * (15 * 1024 * 1024)  # 15MB > 10MB limit

        # Act
        result = await file_processing_service._validate_file_content(
            "large.txt", oversized_content
        )

        # Assert
        assert result.is_valid is False
        assert "exceeds max" in result.error_message

    @pytest.mark.asyncio
    async def test_validate_file_content_rejects_empty_file(
        self,
        file_processing_service: FileProcessingService,
    ):
        """Test file validation rejects empty files."""
        # Act
        result = await file_processing_service._validate_file_content("empty.txt", b"")

        # Assert
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_validate_file_content_rejects_invalid_extension(
        self,
        file_processing_service: FileProcessingService,
        valid_text_content: bytes,
    ):
        """Test file validation rejects disallowed file extensions."""
        # Act
        result = await file_processing_service._validate_file_content(
            "script.exe", valid_text_content
        )

        # Assert
        assert result.is_valid is False
        assert "not allowed" in result.error_message

    # Test File Upload Operations

    @pytest.mark.asyncio
    async def test_upload_file_fails_with_invalid_content(
        self,
        file_processing_service: FileProcessingService,
        sample_user_id: str,
    ):
        """Test file upload fails with validation errors."""
        # Arrange
        invalid_request = FileUploadRequest(
            filename="test.exe",  # Invalid extension
            content=b"malicious content",
        )

        # Act & Assert
        with pytest.raises(CoreValidationError):
            await file_processing_service.upload_file(sample_user_id, invalid_request)

    @pytest.mark.asyncio
    async def test_upload_file_validates_size_limit(
        self,
        file_processing_service: FileProcessingService,
        sample_user_id: str,
    ):
        """Test file upload enforces size limits."""
        # Arrange - Create oversized file
        oversized_content = b"x" * (15 * 1024 * 1024)  # 15MB > 10MB limit
        upload_request = FileUploadRequest(
            filename="large_file.txt",
            content=oversized_content,
        )

        # Act & Assert
        with pytest.raises(CoreValidationError) as exc_info:
            await file_processing_service.upload_file(sample_user_id, upload_request)

        assert "exceeds max" in str(exc_info.value)

    # Test File Retrieval Operations

    @pytest.mark.asyncio
    async def test_get_file_returns_none_when_not_found(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
    ):
        """Test file retrieval returns None for missing files."""
        # Arrange
        file_id = str(uuid4())
        mock_database_service.fetch_one.return_value = None

        # Act
        result = await file_processing_service.get_file(file_id, sample_user_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_file_content_returns_none_for_missing_file(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
    ):
        """Test file content retrieval returns None for missing files."""
        # Arrange
        file_id = str(uuid4())
        mock_database_service.fetch_one.return_value = None

        # Act
        result = await file_processing_service.get_file_content(file_id, sample_user_id)

        # Assert
        assert result is None

    # Test File Search Operations

    @pytest.mark.asyncio
    async def test_search_files_returns_empty_list_when_no_results(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
    ):
        """Test file search returns empty list when no matches found."""
        # Arrange
        from tripsage_core.services.business.file_processing_service import (
            FileSearchRequest,
        )

        search_request = FileSearchRequest(
            query="nonexistent file",
            limit=10,
        )
        mock_database_service.fetch_all.return_value = []

        # Act
        results = await file_processing_service.search_files(
            sample_user_id, search_request
        )

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0

    # Test File Deletion Operations

    @pytest.mark.asyncio
    async def test_delete_file_returns_false_when_file_not_found(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
    ):
        """Test file deletion returns False for missing files."""
        # Arrange
        file_id = str(uuid4())
        mock_database_service.fetch_one.return_value = None

        # Act & Assert
        with pytest.raises(CoreResourceNotFoundError):
            await file_processing_service.delete_file(file_id, sample_user_id)

    # Test Usage Statistics

    @pytest.mark.asyncio
    async def test_get_usage_stats_handles_database_errors_gracefully(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
    ):
        """Test usage statistics handles database errors gracefully."""
        # Arrange
        mock_database_service.fetch_one.side_effect = Exception("Database error")

        # Act
        result = await file_processing_service.get_usage_stats(sample_user_id)

        # Assert
        from tripsage_core.services.business.file_processing_service import (
            FileUsageStats,
        )

        assert isinstance(result, FileUsageStats)
        assert result.total_files == 0
        assert result.total_size == 0

    # Test Error Handling

    @pytest.mark.asyncio
    async def test_service_handles_empty_filename_validation(
        self,
        file_processing_service: FileProcessingService,
        valid_text_content: bytes,
    ):
        """Test service handles empty filename validation."""
        # Act
        result = await file_processing_service._validate_file_content(
            "", valid_text_content
        )

        # Assert
        assert result.is_valid is False
        assert "Filename is required" in result.error_message

    @pytest.mark.asyncio
    async def test_concurrent_file_operations_handling(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
    ):
        """Test service handles concurrent file operations correctly."""
        # Arrange
        file_ids = [str(uuid4()) for _ in range(3)]

        # Mock database to return None for all files (not found)
        mock_database_service.fetch_one.return_value = None

        # Act - Attempt to get multiple files concurrently
        tasks = [
            file_processing_service.get_file(file_id, sample_user_id)
            for file_id in file_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - All should return None (not found)
        assert all(result is None for result in results)
        assert len(results) == 3

    # Test MIME Type Detection

    def test_detect_mime_type_for_common_files(
        self,
        file_processing_service: FileProcessingService,
    ):
        """Test MIME type detection for common file types."""
        # Test cases
        test_cases = [
            ("document.txt", b"text content", "text/plain"),
            ("image.jpg", b"fake jpeg content", "image/jpeg"),
            ("document.pdf", b"fake pdf content", "application/pdf"),
        ]

        for filename, content, expected_mime in test_cases:
            # Act
            detected_mime = file_processing_service._detect_mime_type(filename, content)

            # Assert
            assert detected_mime == expected_mime

    # Test File Format Validation

    def test_validate_file_format_with_various_types(
        self,
        file_processing_service: FileProcessingService,
    ):
        """Test file format validation for different file types."""
        # Test valid text file
        is_valid, error = file_processing_service._validate_file_format(
            b"Simple text content", "text/plain"
        )
        assert is_valid is True
        assert error is None

        # Test invalid format (empty content for PDF)
        is_valid, error = file_processing_service._validate_file_format(
            b"not a pdf", "application/pdf"
        )
        assert is_valid is False
        assert "Invalid PDF header" in error

    # Integration Test

    @pytest.mark.asyncio
    async def test_file_processing_service_initialization(self):
        """Test FileProcessingService initializes correctly with defaults."""
        # Act
        service = FileProcessingService()

        # Assert
        assert service.max_file_size == 10 * 1024 * 1024  # 10MB default
        assert service.max_session_size == 50 * 1024 * 1024  # 50MB default
        assert len(service.allowed_extensions) > 0
        assert len(service.allowed_mime_types) > 0

    @pytest.mark.asyncio
    async def test_file_service_with_realistic_workflow(
        self,
        file_processing_service: FileProcessingService,
        mock_database_service: AsyncMock,
        sample_user_id: str,
        valid_text_content: bytes,
    ):
        """Test realistic file service workflow without upload."""
        # Test file validation (the core functionality we can test)
        validation_result = await file_processing_service._validate_file_content(
            "test.txt", valid_text_content
        )
        assert validation_result.is_valid is True

        # Test file retrieval (not found)
        file_id = str(uuid4())
        mock_database_service.fetch_one.return_value = None
        result = await file_processing_service.get_file(file_id, sample_user_id)
        assert result is None

        # Test usage stats with error handling
        mock_database_service.fetch_one.side_effect = Exception("DB error")
        stats = await file_processing_service.get_usage_stats(sample_user_id)
        assert stats.total_files == 0
