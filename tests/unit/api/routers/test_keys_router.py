"""Comprehensive unit tests for keys router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import APIKeyFactory
from tripsage.api.main import app


class TestKeysRouter:
    """Test suite for API keys router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_service = Mock()
        self.mock_monitoring_service = Mock()
        self.sample_api_key = APIKeyFactory.create()
        self.sample_api_keys = APIKeyFactory.create_service_keys()
        self.sample_validation_response = {
            "is_valid": True,
            "message": "Key is valid",
            "service": "openai",
            "key_hash": "hash123",
        }

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_list_keys_success(self, mock_auth, mock_service_dep):
        """Test successful API keys listing."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.list_keys = AsyncMock(return_value=self.sample_api_keys)

        # Act
        response = self.client.get(
            "/api/keys", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(self.sample_api_keys)
        self.mock_service.list_keys.assert_called_once_with("test-user-id")

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_list_keys_empty(self, mock_auth, mock_service_dep):
        """Test listing keys when user has no keys."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.list_keys = AsyncMock(return_value=[])

        # Act
        response = self.client.get(
            "/api/keys", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_create_key_success(self, mock_auth, mock_service_dep):
        """Test successful API key creation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.validate_key = AsyncMock(
            return_value=self.sample_validation_response
        )
        self.mock_service.create_key = AsyncMock(return_value=self.sample_api_key)

        create_request = {
            "service": "openai",
            "key": "sk-test123456789",
            "name": "My OpenAI Key",
        }

        # Act
        response = self.client.post(
            "/api/keys",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["service_name"] == "openai"
        self.mock_service.validate_key.assert_called_once()
        self.mock_service.create_key.assert_called_once()

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_create_key_invalid_key(self, mock_auth, mock_service_dep):
        """Test API key creation with invalid key."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        invalid_validation = {
            "is_valid": False,
            "message": "Invalid API key format",
            "service": "openai",
        }
        self.mock_service.validate_key = AsyncMock(return_value=invalid_validation)

        create_request = {
            "service": "openai",
            "key": "invalid-key",
            "name": "Invalid Key",
        }

        # Act
        response = self.client.post(
            "/api/keys",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid API key" in response.json()["detail"]

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_delete_key_success(self, mock_auth, mock_service_dep):
        """Test successful API key deletion."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        key_id = "test-key-id"
        existing_key = {**self.sample_api_key, "user_id": "test-user-id"}
        self.mock_service.get_key = AsyncMock(return_value=existing_key)
        self.mock_service.delete_key = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            f"/api/keys/{key_id}", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.mock_service.get_key.assert_called_once_with(key_id)
        self.mock_service.delete_key.assert_called_once_with(key_id)

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_delete_key_not_found(self, mock_auth, mock_service_dep):
        """Test deletion of non-existent API key."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        key_id = "non-existent-key"
        self.mock_service.get_key = AsyncMock(return_value=None)

        # Act
        response = self.client.delete(
            f"/api/keys/{key_id}", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "API key not found" in response.json()["detail"]

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_delete_key_forbidden(self, mock_auth, mock_service_dep):
        """Test deletion of key owned by another user."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        key_id = "other-user-key"
        other_user_key = {**self.sample_api_key, "user_id": "other-user-id"}
        self.mock_service.get_key = AsyncMock(return_value=other_user_key)

        # Act
        response = self.client.delete(
            f"/api/keys/{key_id}", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.json()["detail"]

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_validate_key_success(self, mock_auth, mock_service_dep):
        """Test successful API key validation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.validate_key = AsyncMock(
            return_value=self.sample_validation_response
        )

        validate_request = {"service": "openai", "key": "sk-test123456789"}

        # Act
        response = self.client.post(
            "/api/keys/validate",
            json=validate_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert data["service"] == "openai"
        self.mock_service.validate_key.assert_called_once()

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_validate_key_invalid(self, mock_auth, mock_service_dep):
        """Test validation of invalid API key."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        invalid_validation = {
            "is_valid": False,
            "message": "Key does not have required permissions",
            "service": "openai",
        }
        self.mock_service.validate_key = AsyncMock(return_value=invalid_validation)

        validate_request = {"service": "openai", "key": "sk-invalid123"}

        # Act
        response = self.client.post(
            "/api/keys/validate",
            json=validate_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is False
        assert "permissions" in data["message"]

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_rotate_key_success(self, mock_auth, mock_service_dep):
        """Test successful API key rotation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        key_id = "test-key-id"
        existing_key = {
            **self.sample_api_key,
            "user_id": "test-user-id",
            "service": "openai",
        }
        rotated_key = {**existing_key, "key_hash": "new_hash"}

        self.mock_service.get_key = AsyncMock(return_value=existing_key)
        self.mock_service.validate_key = AsyncMock(
            return_value=self.sample_validation_response
        )
        self.mock_service.rotate_key = AsyncMock(return_value=rotated_key)

        rotate_request = {"new_key": "sk-new123456789"}

        # Act
        response = self.client.post(
            f"/api/keys/{key_id}/rotate",
            json=rotate_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key_hash"] == "new_hash"
        self.mock_service.get_key.assert_called_once_with(key_id)
        self.mock_service.validate_key.assert_called_once()
        self.mock_service.rotate_key.assert_called_once()

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_rotate_key_not_found(self, mock_auth, mock_service_dep):
        """Test rotation of non-existent API key."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        key_id = "non-existent-key"
        self.mock_service.get_key = AsyncMock(return_value=None)

        rotate_request = {"new_key": "sk-new123456789"}

        # Act
        response = self.client.post(
            f"/api/keys/{key_id}/rotate",
            json=rotate_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "API key not found" in response.json()["detail"]

    @patch("tripsage.api.routers.keys.get_key_health_metrics")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_get_metrics_success(self, mock_auth, mock_health_metrics):
        """Test successful metrics retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        sample_metrics = {
            "total_keys": 10,
            "active_keys": 8,
            "failed_validations": 2,
            "last_updated": "2024-01-01T00:00:00Z",
        }
        mock_health_metrics.return_value = sample_metrics

        # Act
        response = self.client.get(
            "/api/keys/metrics", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_keys"] == 10
        assert data["active_keys"] == 8
        mock_health_metrics.assert_called_once()

    @patch("tripsage.api.routers.keys.get_monitoring_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_get_audit_log_success(self, mock_auth, mock_monitoring_dep):
        """Test successful audit log retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_monitoring_dep.return_value = self.mock_monitoring_service
        sample_audit_log = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "action": "key_created",
                "key_id": "key123",
                "user_id": "test-user-id",
            }
        ]
        self.mock_monitoring_service.get_audit_log = AsyncMock(
            return_value=sample_audit_log
        )

        # Act
        response = self.client.get(
            "/api/keys/audit?limit=50", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["action"] == "key_created"

    def test_list_keys_unauthorized(self):
        """Test keys listing without authentication."""
        response = self.client.get("/api/keys")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_key_unauthorized(self):
        """Test key creation without authentication."""
        create_request = {"service": "openai", "key": "sk-test123", "name": "Test Key"}
        response = self.client.post("/api/keys", json=create_request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.keys.get_key_service")
    @patch("tripsage.api.routers.keys.require_principal_dep")
    def test_create_key_service_error(self, mock_auth, mock_service_dep):
        """Test key creation with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.validate_key = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        create_request = {"service": "openai", "key": "sk-test123", "name": "Test Key"}

        # Act
        response = self.client.post(
            "/api/keys",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create API key" in response.json()["detail"]

    @pytest.mark.parametrize("service", ["", None, "invalid_service", "a" * 100])
    def test_create_key_invalid_service(self, service):
        """Test key creation with invalid service values."""
        create_request = {"service": service, "key": "sk-test123", "name": "Test Key"}

        response = self.client.post(
            "/api/keys",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("key", ["", None, "short", "a" * 1000])
    def test_create_key_invalid_key_format(self, key):
        """Test key creation with invalid key values."""
        create_request = {"service": "openai", "key": key, "name": "Test Key"}

        response = self.client.post(
            "/api/keys",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("limit", [0, -1, 1001])
    def test_get_audit_log_invalid_limit(self, limit):
        """Test audit log with invalid limit values."""
        response = self.client.get(
            f"/api/keys/audit?limit={limit}",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_key_missing_required_fields(self):
        """Test key creation with missing required fields."""
        create_request = {
            "name": "Test Key"
            # Missing service and key
        }

        response = self.client.post(
            "/api/keys",
            json=create_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
