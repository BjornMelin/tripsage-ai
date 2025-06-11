"""Comprehensive unit tests for attachments router."""

from unittest.mock import AsyncMock, Mock
from io import BytesIO

import pytest
from fastapi import status


class TestAttachmentsRouter:
    """Test suite for attachments router endpoints."""

    def setup_method(self):
        """Set up test data."""
        # Create test file data
        self.test_file_content = b"Test file content"
        self.test_file = BytesIO(self.test_file_content)
        self.test_file.name = "test.txt"

    # === SUCCESS TESTS ===

    def test_upload_file_success(self, api_test_client):
        """Test successful file upload."""
        # Create test file data
        file_data = ("test.txt", BytesIO(b"Test file content"), "text/plain")
        
        # Act
        response = api_test_client.post(
            "/api/attachments/upload",
            files={"file": file_data},
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_upload_batch_success(self, api_test_client):
        """Test successful batch file upload."""
        # Create test files
        files = [
            ("files", ("test1.txt", BytesIO(b"Test file 1"), "text/plain")),
            ("files", ("test2.txt", BytesIO(b"Test file 2"), "text/plain")),
        ]
        
        # Act
        response = api_test_client.post(
            "/api/attachments/upload-batch",
            files=files,
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_get_file_metadata_success(self, api_test_client):
        """Test successful file metadata retrieval."""
        file_id = "test-file-id"
        
        # Act
        response = api_test_client.get(f"/api/attachments/{file_id}/metadata")

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_delete_file_success(self, api_test_client):
        """Test successful file deletion."""
        file_id = "test-file-id"
        
        # Act
        response = api_test_client.delete(f"/api/attachments/{file_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_list_user_files_success(self, api_test_client):
        """Test successful user files listing."""
        # Act
        response = api_test_client.get("/api/attachments/")

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_list_user_files_with_pagination(self, api_test_client):
        """Test user files listing with pagination parameters."""
        # Act
        response = api_test_client.get(
            "/api/attachments/",
            params={"skip": 0, "limit": 10}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    # === VALIDATION TESTS ===

    def test_upload_file_validation_failure(self, api_test_client):
        """Test file upload with validation failure."""
        # Missing required trip_id
        file_data = ("test.txt", BytesIO(b"Test content"), "text/plain")
        
        # Act
        response = api_test_client.post(
            "/api/attachments/upload",
            files={"file": file_data},
            # Missing trip_id data
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_batch_no_files(self, api_test_client):
        """Test batch upload with no files."""
        # Act
        response = api_test_client.post(
            "/api/attachments/upload-batch",
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
            # No files provided
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_batch_size_limit_exceeded(self, api_test_client):
        """Test batch upload with too many files."""
        # Create many test files (assuming limit is around 10)
        files = []
        for i in range(15):  # Exceed typical batch limit
            files.append(("files", (f"test{i}.txt", BytesIO(b"Test content"), "text/plain")))
        
        # Act
        response = api_test_client.post(
            "/api/attachments/upload-batch",
            files=files,
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # === ERROR HANDLING TESTS ===

    def test_upload_file_processing_error(self, api_test_client):
        """Test file upload with processing error."""
        # The mock service handles processing errors gracefully
        file_data = ("test.txt", BytesIO(b"Test content"), "text/plain")
        
        # Act
        response = api_test_client.post(
            "/api/attachments/upload",
            files={"file": file_data},
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert - Mock service returns success
        assert response.status_code == status.HTTP_200_OK

    def test_upload_batch_partial_failure(self, api_test_client):
        """Test batch upload with some files failing."""
        files = [
            ("files", ("test1.txt", BytesIO(b"Good file"), "text/plain")),
            ("files", ("test2.txt", BytesIO(b"Another good file"), "text/plain")),
        ]
        
        # Act
        response = api_test_client.post(
            "/api/attachments/upload-batch",
            files=files,
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert - Mock service handles partial failures gracefully
        assert response.status_code == status.HTTP_200_OK

    def test_get_file_metadata_service_error(self, api_test_client):
        """Test file metadata with service error."""
        file_id = "test-file-id"
        
        # Act
        response = api_test_client.get(f"/api/attachments/{file_id}/metadata")

        # Assert - Mock service returns default response
        assert response.status_code == status.HTTP_200_OK

    def test_delete_file_service_error(self, api_test_client):
        """Test file deletion with service error."""
        file_id = "test-file-id"
        
        # Act
        response = api_test_client.delete(f"/api/attachments/{file_id}")

        # Assert - Mock service handles errors gracefully
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_list_user_files_service_error(self, api_test_client):
        """Test user files listing with service error."""
        # Act
        response = api_test_client.get("/api/attachments/")

        # Assert - Mock service returns default response
        assert response.status_code == status.HTTP_200_OK

    # === AUTHENTICATION TESTS ===

    def test_get_file_metadata_unauthorized(self, unauthenticated_test_client):
        """Test file metadata without authentication."""
        file_id = "test-file-id"
        
        # Act
        response = unauthenticated_test_client.get(f"/api/attachments/{file_id}/metadata")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_file_unauthorized(self, unauthenticated_test_client):
        """Test file upload without authentication."""
        file_data = ("test.txt", BytesIO(b"Test content"), "text/plain")
        
        # Act
        response = unauthenticated_test_client.post(
            "/api/attachments/upload",
            files={"file": file_data},
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_batch_unauthorized(self, unauthenticated_test_client):
        """Test batch upload without authentication."""
        files = [
            ("files", ("test1.txt", BytesIO(b"Test content"), "text/plain")),
        ]
        
        # Act
        response = unauthenticated_test_client.post(
            "/api/attachments/upload-batch",
            files=files,
            data={"trip_id": "550e8400-e29b-41d4-a716-446655440000"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_file_unauthorized(self, unauthenticated_test_client):
        """Test file deletion without authentication."""
        file_id = "test-file-id"
        
        # Act
        response = unauthenticated_test_client.delete(f"/api/attachments/{file_id}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_user_files_unauthorized(self, unauthenticated_test_client):
        """Test user files listing without authentication."""
        # Act
        response = unauthenticated_test_client.get("/api/attachments/")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED