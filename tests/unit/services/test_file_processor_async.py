"""
Tests for async file processor service.

This module tests the refactored file processor that now uses aiofiles
for proper async file operations.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from tripsage.services.external.file_processor import (
    FileProcessingError,
    FileProcessor,
    ProcessedFile,
    UploadResult,
)


class TestFileProcessorAsync:
    """Test async implementation of file processor."""

    @pytest.fixture
    def file_processor(self):
        """Create file processor for testing."""
        return FileProcessor()

    @pytest.fixture
    def mock_upload_file(self):
        """Create mock upload file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test_document.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"Mock PDF content")
        mock_file.seek = AsyncMock()
        return mock_file

    @pytest.fixture
    def mock_text_file(self):
        """Create mock text file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test_document.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = 256
        mock_file.read = AsyncMock(return_value=b"This is test content\nLine 2\nLine 3")
        mock_file.seek = AsyncMock()
        return mock_file

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    async def test_async_file_upload_success(self, file_processor, mock_upload_file, temp_storage_dir):
        """Test successful async file upload."""
        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            # Setup async file mock
            mock_file_handle = AsyncMock()
            mock_file_handle.write = AsyncMock()
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_file_handle

            # Execute
            result = await file_processor.upload_file(
                file=mock_upload_file,
                user_id="test_user_123",
                storage_path=temp_storage_dir
            )

            # Verify
            assert isinstance(result, UploadResult)
            assert result.success is True
            assert result.file_id is not None
            assert result.original_filename == "test_document.pdf"
            assert result.content_type == "application/pdf"
            assert result.file_size == 1024

            # Verify async file operations
            mock_upload_file.read.assert_called_once()
            mock_aiofiles_open.assert_called_once()
            mock_file_handle.write.assert_called_once_with(b"Mock PDF content")

    @pytest.mark.asyncio
    async def test_async_text_file_metadata_extraction(self, file_processor, mock_text_file, temp_storage_dir):
        """Test async metadata extraction for text files."""
        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            # Setup write operation mock
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            
            # Setup read operation mock for metadata extraction
            mock_read_handle = AsyncMock()
            mock_read_handle.read = AsyncMock(return_value="This is test content\nLine 2\nLine 3")
            
            # Mock aiofiles.open to return different handles for write and read
            mock_aiofiles_open.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # For write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_read_handle))     # For read
            ]

            # Execute
            result = await file_processor.upload_file(
                file=mock_text_file,
                user_id="test_user_123",
                storage_path=temp_storage_dir
            )

            # Verify
            assert result.success is True
            assert result.processed_file.metadata["line_count"] == 3
            assert result.processed_file.metadata["character_count"] == 35

            # Verify both write and read operations
            assert mock_aiofiles_open.call_count == 2
            mock_write_handle.write.assert_called_once()
            mock_read_handle.read.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(self, file_processor, temp_storage_dir):
        """Test concurrent file upload operations."""
        # Create multiple mock files
        mock_files = []
        for i in range(3):
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = f"test_file_{i}.txt"
            mock_file.content_type = "text/plain"
            mock_file.size = 100 + i * 50
            mock_file.read = AsyncMock(return_value=f"Content of file {i}".encode())
            mock_file.seek = AsyncMock()
            mock_files.append(mock_file)

        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            # Setup async file handle
            mock_file_handle = AsyncMock()
            mock_file_handle.write = AsyncMock()
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_file_handle

            # Execute concurrent uploads
            upload_tasks = [
                file_processor.upload_file(
                    file=mock_file,
                    user_id=f"user_{i}",
                    storage_path=temp_storage_dir
                )
                for i, mock_file in enumerate(mock_files)
            ]

            results = await asyncio.gather(*upload_tasks)

            # Verify all uploads succeeded
            assert len(results) == 3
            assert all(result.success for result in results)
            assert all(result.file_id is not None for result in results)

            # Verify unique file IDs
            file_ids = [result.file_id for result in results]
            assert len(set(file_ids)) == 3

    @pytest.mark.asyncio
    async def test_async_file_processing_error_handling(self, file_processor, mock_upload_file, temp_storage_dir):
        """Test error handling in async file processing."""
        # Simulate file write error
        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            mock_aiofiles_open.side_effect = IOError("Disk full")

            # Execute and verify error handling
            result = await file_processor.upload_file(
                file=mock_upload_file,
                user_id="test_user_123",
                storage_path=temp_storage_dir
            )

            assert result.success is False
            assert "Disk full" in result.error_message

    @pytest.mark.asyncio
    async def test_async_file_validation_error(self, file_processor, temp_storage_dir):
        """Test file validation error handling."""
        # Create invalid file (too large)
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "huge_file.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 100 * 1024 * 1024  # 100MB - exceeds typical limits
        mock_file.read = AsyncMock(return_value=b"Mock content")
        mock_file.seek = AsyncMock()

        with patch('tripsage.services.external.file_processor.validate_file') as mock_validate:
            mock_validate.side_effect = ValueError("File too large")

            # Execute
            result = await file_processor.upload_file(
                file=mock_file,
                user_id="test_user_123",
                storage_path=temp_storage_dir
            )

            # Verify
            assert result.success is False
            assert "File too large" in result.error_message

    @pytest.mark.asyncio
    async def test_async_file_cleanup_on_error(self, file_processor, mock_upload_file, temp_storage_dir):
        """Test file cleanup when processing fails."""
        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            # Setup to succeed on write but fail on metadata extraction
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_write_handle

            # Simulate metadata extraction failure
            with patch.object(file_processor, '_extract_file_metadata', side_effect=Exception("Metadata error")):
                # Execute
                result = await file_processor.upload_file(
                    file=mock_upload_file,
                    user_id="test_user_123",
                    storage_path=temp_storage_dir
                )

                # Verify error handling
                assert result.success is False
                assert "Metadata error" in result.error_message

    @pytest.mark.asyncio
    async def test_process_multiple_file_types_concurrently(self, file_processor, temp_storage_dir):
        """Test processing different file types concurrently."""
        # Create files of different types
        pdf_file = MagicMock(spec=UploadFile)
        pdf_file.filename = "document.pdf"
        pdf_file.content_type = "application/pdf"
        pdf_file.size = 1024
        pdf_file.read = AsyncMock(return_value=b"PDF content")
        pdf_file.seek = AsyncMock()

        image_file = MagicMock(spec=UploadFile)
        image_file.filename = "image.jpg"
        image_file.content_type = "image/jpeg"
        image_file.size = 2048
        image_file.read = AsyncMock(return_value=b"JPEG content")
        image_file.seek = AsyncMock()

        text_file = MagicMock(spec=UploadFile)
        text_file.filename = "notes.txt"
        text_file.content_type = "text/plain"
        text_file.size = 512
        text_file.read = AsyncMock(return_value=b"Text content\nSecond line")
        text_file.seek = AsyncMock()

        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            # Setup file handles for different operations
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            
            mock_read_handle = AsyncMock()
            mock_read_handle.read = AsyncMock(return_value="Text content\nSecond line")
            
            # Mock aiofiles.open for write operations (all files) and read operations (text files)
            mock_aiofiles_open.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # PDF write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # Image write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # Text write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_read_handle))    # Text read for metadata
            ]

            # Execute concurrent processing
            tasks = [
                file_processor.upload_file(pdf_file, "user1", temp_storage_dir),
                file_processor.upload_file(image_file, "user2", temp_storage_dir),
                file_processor.upload_file(text_file, "user3", temp_storage_dir)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert len(results) == 3
            assert all(result.success for result in results)

            # Verify file types are correctly identified
            assert results[0].content_type == "application/pdf"
            assert results[1].content_type == "image/jpeg"
            assert results[2].content_type == "text/plain"

            # Verify text file has metadata
            assert results[2].processed_file.metadata["line_count"] == 2


class TestFileProcessorValidation:
    """Test file processor validation with async operations."""

    @pytest.fixture
    def file_processor(self):
        """Create file processor for testing."""
        return FileProcessor()

    @pytest.mark.asyncio
    async def test_file_size_validation(self, file_processor):
        """Test file size validation."""
        # Create oversized file
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "huge_file.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 50 * 1024 * 1024  # 50MB
        mock_file.read = AsyncMock(return_value=b"Mock content")
        mock_file.seek = AsyncMock()

        with patch('tripsage.services.external.file_processor.validate_file') as mock_validate:
            mock_validate.side_effect = ValueError("File size exceeds limit")

            with tempfile.TemporaryDirectory() as temp_dir:
                result = await file_processor.upload_file(
                    file=mock_file,
                    user_id="test_user",
                    storage_path=Path(temp_dir)
                )

            assert result.success is False
            assert "File size exceeds limit" in result.error_message

    @pytest.mark.asyncio
    async def test_file_type_validation(self, file_processor):
        """Test file type validation."""
        # Create file with suspicious extension
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "malicious.exe"
        mock_file.content_type = "application/octet-stream"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"Mock content")
        mock_file.seek = AsyncMock()

        with patch('tripsage.services.external.file_processor.validate_file') as mock_validate:
            mock_validate.side_effect = ValueError("File type not allowed")

            with tempfile.TemporaryDirectory() as temp_dir:
                result = await file_processor.upload_file(
                    file=mock_file,
                    user_id="test_user",
                    storage_path=Path(temp_dir)
                )

            assert result.success is False
            assert "File type not allowed" in result.error_message


class TestFileProcessorPerformance:
    """Test performance aspects of async file processor."""

    @pytest.fixture
    def file_processor(self):
        """Create file processor for testing."""
        return FileProcessor()

    @pytest.mark.asyncio
    async def test_large_file_streaming(self, file_processor):
        """Test handling of large files with streaming."""
        # Create mock large file
        large_content = b"Large file content " * 1000  # ~19KB
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "large_file.txt"
        mock_file.content_type = "text/plain"
        mock_file.size = len(large_content)
        mock_file.read = AsyncMock(return_value=large_content)
        mock_file.seek = AsyncMock()

        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_write_handle

            with tempfile.TemporaryDirectory() as temp_dir:
                start_time = asyncio.get_event_loop().time()
                result = await file_processor.upload_file(
                    file=mock_file,
                    user_id="test_user",
                    storage_path=Path(temp_dir)
                )
                end_time = asyncio.get_event_loop().time()

            # Verify success and reasonable performance
            assert result.success is True
            assert (end_time - start_time) < 1.0  # Should complete quickly with mocks

    @pytest.mark.asyncio
    async def test_concurrent_large_file_processing(self, file_processor):
        """Test concurrent processing of multiple large files."""
        # Create multiple large mock files
        large_files = []
        for i in range(5):
            content = f"Large file {i} content ".encode() * 500  # ~10KB each
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = f"large_file_{i}.txt"
            mock_file.content_type = "text/plain"
            mock_file.size = len(content)
            mock_file.read = AsyncMock(return_value=content)
            mock_file.seek = AsyncMock()
            large_files.append(mock_file)

        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_write_handle

            with tempfile.TemporaryDirectory() as temp_dir:
                # Process all files concurrently
                start_time = asyncio.get_event_loop().time()
                tasks = [
                    file_processor.upload_file(
                        file=mock_file,
                        user_id=f"user_{i}",
                        storage_path=Path(temp_dir)
                    )
                    for i, mock_file in enumerate(large_files)
                ]
                results = await asyncio.gather(*tasks)
                end_time = asyncio.get_event_loop().time()

            # Verify all succeeded
            assert len(results) == 5
            assert all(result.success for result in results)
            
            # Verify concurrent processing was efficient
            total_time = end_time - start_time
            assert total_time < 2.0  # Should be much faster than sequential processing


@pytest.mark.integration
class TestFileProcessorIntegration:
    """Integration tests for file processor with real-like scenarios."""

    @pytest.fixture
    def file_processor(self):
        """Create file processor for testing."""
        return FileProcessor()

    @pytest.mark.asyncio
    async def test_complete_file_processing_workflow(self, file_processor):
        """Test complete file processing workflow."""
        # Create realistic file
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "travel_itinerary.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 2048
        mock_file.read = AsyncMock(return_value=b"PDF travel itinerary content")
        mock_file.seek = AsyncMock()

        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_write_handle

            with tempfile.TemporaryDirectory() as temp_dir:
                # Execute complete workflow
                result = await file_processor.upload_file(
                    file=mock_file,
                    user_id="traveler_123",
                    storage_path=Path(temp_dir)
                )

                # Verify complete result
                assert result.success is True
                assert result.file_id is not None
                assert result.original_filename == "travel_itinerary.pdf"
                assert result.content_type == "application/pdf"
                assert result.file_size == 2048
                assert result.storage_path is not None
                
                # Verify processed file
                assert isinstance(result.processed_file, ProcessedFile)
                assert result.processed_file.file_id == result.file_id
                assert result.processed_file.user_id == "traveler_123"
                assert result.processed_file.original_filename == "travel_itinerary.pdf"
                assert "storage_timestamp" in result.processed_file.metadata

    @pytest.mark.asyncio
    async def test_travel_document_processing_scenario(self, file_processor):
        """Test processing travel-related documents."""
        # Create different travel documents
        documents = [
            {
                "filename": "passport.jpg",
                "content_type": "image/jpeg",
                "content": b"Mock passport image content"
            },
            {
                "filename": "hotel_booking.pdf", 
                "content_type": "application/pdf",
                "content": b"Hotel booking confirmation PDF"
            },
            {
                "filename": "flight_tickets.txt",
                "content_type": "text/plain", 
                "content": b"Flight ticket details\nDeparture: NYC\nDestination: Paris"
            }
        ]

        mock_files = []
        for doc in documents:
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = doc["filename"]
            mock_file.content_type = doc["content_type"]
            mock_file.size = len(doc["content"])
            mock_file.read = AsyncMock(return_value=doc["content"])
            mock_file.seek = AsyncMock()
            mock_files.append(mock_file)

        with patch('aiofiles.open', create=True) as mock_aiofiles_open:
            # Setup for write operations and text file read
            mock_write_handle = AsyncMock()
            mock_write_handle.write = AsyncMock()
            
            mock_read_handle = AsyncMock()
            mock_read_handle.read = AsyncMock(return_value="Flight ticket details\nDeparture: NYC\nDestination: Paris")
            
            # Mock multiple aiofiles.open calls
            mock_aiofiles_open.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # passport write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # hotel write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_write_handle)),  # flight write
                AsyncMock(__aenter__=AsyncMock(return_value=mock_read_handle))    # flight read for metadata
            ]

            with tempfile.TemporaryDirectory() as temp_dir:
                # Process all documents concurrently
                tasks = [
                    file_processor.upload_file(
                        file=mock_file,
                        user_id="traveler_456",
                        storage_path=Path(temp_dir)
                    )
                    for mock_file in mock_files
                ]
                
                results = await asyncio.gather(*tasks)

                # Verify all documents processed successfully
                assert len(results) == 3
                assert all(result.success for result in results)
                
                # Verify document types
                assert results[0].content_type == "image/jpeg"
                assert results[1].content_type == "application/pdf"
                assert results[2].content_type == "text/plain"
                
                # Verify text file metadata
                assert results[2].processed_file.metadata["line_count"] == 3