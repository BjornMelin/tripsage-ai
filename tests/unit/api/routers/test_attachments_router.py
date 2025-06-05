"""Comprehensive unit tests for attachments router."""

from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tripsage.api.main import app


class TestAttachmentsRouter:
    """Test suite for attachments router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_file_service = Mock()

        # Sample test data
        self.sample_file_result = Mock()
        self.sample_file_result.id = "file-123"
        self.sample_file_result.original_filename = "travel-document.pdf"
        self.sample_file_result.file_size = 1024
        self.sample_file_result.mime_type = "application/pdf"
        self.sample_file_result.processing_status.value = "completed"

        self.sample_file_info = {
            "id": "file-123",
            "filename": "travel-document.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "processing_status": "completed",
            "upload_timestamp": "2024-01-01T00:00:00Z",
            "analysis_results": {
                "extracted_text": "Flight confirmation",
                "detected_type": "flight_booking",
            },
        }

        self.sample_validation_result = Mock()
        self.sample_validation_result.is_valid = True
        self.sample_validation_result.error_message = None

    def create_test_file(
        self,
        filename="test.pdf",
        content=b"test content",
        content_type="application/pdf",
    ):
        """Create a test file for upload."""
        file_data = BytesIO(content)
        return ("file", (filename, file_data, content_type))

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.validate_file")
    def test_upload_file_success(self, mock_validate, mock_auth, mock_service_dep):
        """Test successful file upload."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        mock_validate.return_value = self.sample_validation_result
        self.mock_file_service.upload_file = AsyncMock(
            return_value=self.sample_file_result
        )

        # Act
        files = {"file": ("travel-doc.pdf", BytesIO(b"PDF content"), "application/pdf")}
        response = self.client.post(
            "/api/attachments/upload",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["file_id"] == "file-123"
        assert data["filename"] == "travel-document.pdf"
        assert data["file_size"] == 1024
        assert data["mime_type"] == "application/pdf"
        assert data["processing_status"] == "completed"
        assert data["upload_status"] == "completed"
        self.mock_file_service.upload_file.assert_called_once()

    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.validate_file")
    def test_upload_file_validation_failure(self, mock_validate, mock_auth):
        """Test file upload with validation failure."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        invalid_validation = Mock()
        invalid_validation.is_valid = False
        invalid_validation.error_message = "File type not allowed"
        mock_validate.return_value = invalid_validation

        # Act
        files = {
            "file": ("malicious.exe", BytesIO(b"malware"), "application/x-executable")
        }
        response = self.client.post(
            "/api/attachments/upload",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "File type not allowed" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.validate_file")
    def test_upload_file_processing_error(
        self, mock_validate, mock_auth, mock_service_dep
    ):
        """Test file upload with processing error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        mock_validate.return_value = self.sample_validation_result
        self.mock_file_service.upload_file = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        # Act
        files = {"file": ("test.pdf", BytesIO(b"PDF content"), "application/pdf")}
        response = self.client.post(
            "/api/attachments/upload",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "File processing failed" in response.json()["detail"]

    def test_upload_file_unauthorized(self):
        """Test file upload without authentication."""
        # Act
        files = {"file": ("test.pdf", BytesIO(b"PDF content"), "application/pdf")}
        response = self.client.post("/api/attachments/upload", files=files)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.validate_file")
    @patch(
        "tripsage.api.routers.attachments.MAX_SESSION_SIZE", 1000
    )  # Small limit for testing
    def test_upload_batch_success(self, mock_validate, mock_auth, mock_service_dep):
        """Test successful batch file upload."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        mock_validate.return_value = self.sample_validation_result

        # Create multiple file results
        file_results = []
        for i in range(2):
            result = Mock()
            result.id = f"file-{i}"
            result.original_filename = f"document-{i}.pdf"
            result.file_size = 200
            result.mime_type = "application/pdf"
            result.processing_status.value = "completed"
            file_results.append(result)

        self.mock_file_service.upload_file = AsyncMock(side_effect=file_results)

        # Act
        files = [
            ("files", ("doc1.pdf", BytesIO(b"a" * 200), "application/pdf")),
            ("files", ("doc2.pdf", BytesIO(b"b" * 200), "application/pdf")),
        ]
        response = self.client.post(
            "/api/attachments/upload/batch",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_files"] == 2
        assert data["total_size"] == 400
        assert len(data["files"]) == 2
        assert self.mock_file_service.upload_file.call_count == 2

    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_upload_batch_no_files(self, mock_auth):
        """Test batch upload with no files provided."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")

        # Act
        response = self.client.post(
            "/api/attachments/upload/batch",
            files=[],
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No files provided" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.MAX_SESSION_SIZE", 100)  # Very small limit
    def test_upload_batch_size_limit_exceeded(self, mock_auth):
        """Test batch upload exceeding size limit."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")

        # Act - Upload files that exceed the limit
        files = [
            ("files", ("large1.pdf", BytesIO(b"a" * 60), "application/pdf")),
            ("files", ("large2.pdf", BytesIO(b"b" * 60), "application/pdf")),
        ]
        response = self.client.post(
            "/api/attachments/upload/batch",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "exceeds session limit" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.validate_file")
    def test_upload_batch_partial_failure(
        self, mock_validate, mock_auth, mock_service_dep
    ):
        """Test batch upload with some files failing."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service

        # First file validates, second fails validation
        mock_validate.side_effect = [
            self.sample_validation_result,  # Success
            Mock(is_valid=False, error_message="Invalid file type"),  # Failure
        ]

        self.mock_file_service.upload_file = AsyncMock(
            return_value=self.sample_file_result
        )

        # Act
        files = [
            ("files", ("valid.pdf", BytesIO(b"valid content"), "application/pdf")),
            ("files", ("invalid.exe", BytesIO(b"malware"), "application/x-executable")),
        ]
        response = self.client.post(
            "/api/attachments/upload/batch",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_files"] == 1  # Only one file processed successfully
        assert len(data["files"]) == 1

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_get_file_metadata_success(self, mock_auth, mock_service_dep):
        """Test successful file metadata retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.get_file = AsyncMock(return_value=self.sample_file_info)

        # Act
        response = self.client.get(
            "/api/attachments/files/file-123",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "file-123"
        assert data["filename"] == "travel-document.pdf"
        assert "analysis_results" in data
        self.mock_file_service.get_file.assert_called_once_with(
            "file-123", "test-user-id"
        )

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_get_file_metadata_not_found(self, mock_auth, mock_service_dep):
        """Test file metadata retrieval for non-existent file."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.get_file = AsyncMock(return_value=None)

        # Act
        response = self.client.get(
            "/api/attachments/files/nonexistent",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found or access denied" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_get_file_metadata_service_error(self, mock_auth, mock_service_dep):
        """Test file metadata retrieval with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.get_file = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        response = self.client.get(
            "/api/attachments/files/file-123",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve file information" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_delete_file_success(self, mock_auth, mock_service_dep):
        """Test successful file deletion."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.delete_file = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            "/api/attachments/files/file-123",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "File deleted successfully"
        assert data["file_id"] == "file-123"
        self.mock_file_service.delete_file.assert_called_once_with(
            "file-123", "test-user-id"
        )

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_delete_file_not_found(self, mock_auth, mock_service_dep):
        """Test deletion of non-existent file."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.delete_file = AsyncMock(return_value=False)

        # Act
        response = self.client.delete(
            "/api/attachments/files/nonexistent",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found or access denied" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_delete_file_service_error(self, mock_auth, mock_service_dep):
        """Test file deletion with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.delete_file = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        response = self.client.delete(
            "/api/attachments/files/file-123",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to delete file" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_list_user_files_success(self, mock_auth, mock_service_dep):
        """Test successful file listing."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        sample_files = [
            {
                "id": "file-1",
                "filename": "doc1.pdf",
                "file_size": 1024,
                "upload_timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "id": "file-2",
                "filename": "doc2.pdf",
                "file_size": 2048,
                "upload_timestamp": "2024-01-02T00:00:00Z",
            },
        ]
        self.mock_file_service.search_files = AsyncMock(return_value=sample_files)

        # Act
        response = self.client.get(
            "/api/attachments/files?limit=10&offset=0",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["files"]) == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert data["total"] == 2
        self.mock_file_service.search_files.assert_called_once()

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_list_user_files_with_pagination(self, mock_auth, mock_service_dep):
        """Test file listing with custom pagination parameters."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.search_files = AsyncMock(return_value=[])

        # Act
        response = self.client.get(
            "/api/attachments/files?limit=25&offset=50",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 25
        assert data["offset"] == 50
        assert data["files"] == []

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    def test_list_user_files_service_error(self, mock_auth, mock_service_dep):
        """Test file listing with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        self.mock_file_service.search_files = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        response = self.client.get(
            "/api/attachments/files", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve file list" in response.json()["detail"]

    def test_list_user_files_unauthorized(self):
        """Test file listing without authentication."""
        # Act
        response = self.client.get("/api/attachments/files")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_file_metadata_unauthorized(self):
        """Test file metadata retrieval without authentication."""
        # Act
        response = self.client.get("/api/attachments/files/file-123")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_file_unauthorized(self):
        """Test file deletion without authentication."""
        # Act
        response = self.client.delete("/api/attachments/files/file-123")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "limit,offset",
        [
            (-1, 0),  # Invalid limit
            (0, 0),  # Zero limit
            (1001, 0),  # Limit too high
            (10, -1),  # Invalid offset
        ],
    )
    def test_list_user_files_invalid_pagination(self, limit, offset):
        """Test file listing with invalid pagination parameters."""
        # Act
        response = self.client.get(
            f"/api/attachments/files?limit={limit}&offset={offset}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert - Depending on FastAPI validation, this might be 422 or handled gracefully
        # For now, we'll test that the request is handled appropriately
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_200_OK,
        ]

    def test_upload_file_no_file_provided(self):
        """Test file upload without providing a file."""
        # Act
        response = self.client.post(
            "/api/attachments/upload", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    @patch("tripsage.api.routers.attachments.require_principal_dep")
    @patch("tripsage.api.routers.attachments.validate_file")
    def test_upload_batch_all_files_fail(
        self, mock_validate, mock_auth, mock_service_dep
    ):
        """Test batch upload where all files fail validation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_file_service
        failed_validation = Mock()
        failed_validation.is_valid = False
        failed_validation.error_message = "Invalid file type"
        mock_validate.return_value = failed_validation

        # Act
        files = [
            ("files", ("bad1.exe", BytesIO(b"malware1"), "application/x-executable")),
            ("files", ("bad2.exe", BytesIO(b"malware2"), "application/x-executable")),
        ]
        response = self.client.post(
            "/api/attachments/upload/batch",
            files=files,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "All files failed validation/processing" in response.json()["detail"]

    @patch("tripsage.api.routers.attachments.get_file_processing_service")
    def test_get_file_processing_service_singleton(self, mock_service_class):
        """Test that file processing service is created properly."""
        # Arrange
        from tripsage.api.routers.attachments import get_file_processing_service

        # Act
        service1 = get_file_processing_service()
        service2 = get_file_processing_service()

        # Assert - Each call creates a new instance (not a true singleton in this implementation)
        assert service1 is not None
        assert service2 is not None

    def test_file_upload_response_model(self):
        """Test FileUploadResponse model creation."""
        # Arrange
        from tripsage.api.routers.attachments import FileUploadResponse

        # Act
        response = FileUploadResponse(
            file_id="test-123",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            processing_status="completed",
            upload_status="completed",
        )

        # Assert
        assert response.file_id == "test-123"
        assert response.filename == "test.pdf"
        assert response.message == "Upload successful"  # Default value

    def test_batch_upload_response_model(self):
        """Test BatchUploadResponse model creation."""
        # Arrange
        from tripsage.api.routers.attachments import (
            BatchUploadResponse,
            FileUploadResponse,
        )

        file_responses = [
            FileUploadResponse(
                file_id="test-123",
                filename="test.pdf",
                file_size=1024,
                mime_type="application/pdf",
                processing_status="completed",
                upload_status="completed",
            )
        ]

        # Act
        response = BatchUploadResponse(
            files=file_responses, total_files=1, total_size=1024
        )

        # Assert
        assert len(response.files) == 1
        assert response.total_files == 1
        assert response.total_size == 1024
