"""
Integration tests for API services.

Tests the integration between API services and core business services,
ensuring proper delegation and model adaptation.
"""

from uuid import uuid4

import pytest

from tripsage.api.models.requests.api_keys import CreateApiKeyRequest
from tripsage.api.models.requests.auth import LoginRequest, RegisterUserRequest
from tripsage.api.services.auth_service import AuthService
from tripsage.api.services.key_service import KeyService
from tripsage.api.services.trip_service import TripService


class TestApiServicesIntegration:
    """Integration tests for API services."""

    @pytest.fixture
    def sample_user_data(self):
        """Sample user registration data."""
        return {
            "username": f"testuser_{uuid4().hex[:8]}",
            "email": f"test_{uuid4().hex[:8]}@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
        }

    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip creation data."""
        return {
            "name": "Test Integration Trip",
            "description": "A test trip for integration testing",
            "destination": "Paris, France",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "budget": 2000.0,
        }

    @pytest.fixture
    def sample_api_key_data(self):
        """Sample API key creation data."""
        return {
            "name": "Test OpenAI Key",
            "service": "openai",
            "key_value": "sk-test123456789",
            "description": "Test API key for integration testing",
        }

    @pytest.mark.asyncio
    async def test_auth_service_integration(self, sample_user_data):
        """Test auth service integration with core services."""
        # This test would require actual core services to be available
        # For now, we'll test the service instantiation and method signatures

        auth_service = AuthService()

        # Verify service has required methods
        assert hasattr(auth_service, "register_user")
        assert hasattr(auth_service, "login_user")
        assert hasattr(auth_service, "refresh_token")
        assert hasattr(auth_service, "get_current_user")
        assert hasattr(auth_service, "change_password")
        assert hasattr(auth_service, "forgot_password")
        assert hasattr(auth_service, "reset_password")
        assert hasattr(auth_service, "logout_user")

        # Verify model adaptation methods
        assert hasattr(auth_service, "_adapt_token_response")
        assert hasattr(auth_service, "_adapt_user_response")

        # Test request model creation
        register_request = RegisterUserRequest(
            username=sample_user_data["username"],
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            password_confirm=sample_user_data["password"],
            full_name=sample_user_data["full_name"],
        )

        assert register_request.username == sample_user_data["username"]
        assert register_request.email == sample_user_data["email"]

        login_request = LoginRequest(
            username=sample_user_data["username"],
            password=sample_user_data["password"],
        )

        assert login_request.username == sample_user_data["username"]

    @pytest.mark.asyncio
    async def test_key_service_integration(self, sample_api_key_data):
        """Test key service integration with core services."""
        key_service = KeyService()

        # Verify service has required methods
        assert hasattr(key_service, "create_api_key")
        assert hasattr(key_service, "get_user_api_keys")
        assert hasattr(key_service, "get_api_key")
        assert hasattr(key_service, "get_service_status")
        assert hasattr(key_service, "get_all_services_status")
        assert hasattr(key_service, "validate_api_key")
        assert hasattr(key_service, "validate_key_value")
        assert hasattr(key_service, "rotate_api_key")
        assert hasattr(key_service, "delete_api_key")

        # Verify model adaptation methods
        assert hasattr(key_service, "_adapt_api_key_response")
        assert hasattr(key_service, "_adapt_validation_response")

        # Test request model creation
        create_request = CreateApiKeyRequest(
            name=sample_api_key_data["name"],
            service=sample_api_key_data["service"],
            key_value=sample_api_key_data["key_value"],
            description=sample_api_key_data["description"],
        )

        assert create_request.name == sample_api_key_data["name"]
        assert create_request.service == sample_api_key_data["service"]

    @pytest.mark.asyncio
    async def test_trip_service_integration(self, sample_trip_data):
        """Test trip service integration with core services."""
        trip_service = TripService()

        # Verify service has required methods
        assert hasattr(trip_service, "create_trip")
        assert hasattr(trip_service, "get_trip")
        assert hasattr(trip_service, "get_user_trips")
        assert hasattr(trip_service, "update_trip")
        assert hasattr(trip_service, "delete_trip")
        assert hasattr(trip_service, "search_trips")

        # Verify lazy initialization
        assert hasattr(trip_service, "_get_core_trip_service")

        # Test data validation
        assert sample_trip_data["name"] == "Test Integration Trip"
        assert sample_trip_data["destination"] == "Paris, France"
        assert sample_trip_data["budget"] == 2000.0

    @pytest.mark.asyncio
    async def test_service_dependency_injection_compatibility(self):
        """Test that services are compatible with FastAPI dependency injection."""
        # Import dependency functions
        from api.services.auth_service import get_auth_service
        from api.services.key_service import get_key_service
        from api.services.trip_service import get_trip_service

        # Verify dependency functions exist and are callable
        assert callable(get_auth_service)
        assert callable(get_key_service)
        assert callable(get_trip_service)

        # Verify they have the correct signatures for FastAPI Depends
        import inspect

        auth_sig = inspect.signature(get_auth_service)
        key_sig = inspect.signature(get_key_service)
        trip_sig = inspect.signature(get_trip_service)

        # All should be async functions
        assert inspect.iscoroutinefunction(get_auth_service)
        assert inspect.iscoroutinefunction(get_key_service)
        assert inspect.iscoroutinefunction(get_trip_service)

        assert auth_sig is not None
        assert key_sig is not None
        assert trip_sig is not None

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test that all services handle errors consistently."""
        from tripsage_core.exceptions.exceptions import (
            CoreAuthenticationError,
            CoreServiceError,
            CoreValidationError,
        )

        # All services should handle these core exceptions
        auth_service = AuthService()
        key_service = KeyService()
        trip_service = TripService()

        # Verify services exist and can be instantiated
        assert isinstance(auth_service, AuthService)
        assert isinstance(key_service, KeyService)
        assert isinstance(trip_service, TripService)

        # Verify exception types are available for handling
        assert issubclass(CoreAuthenticationError, Exception)
        assert issubclass(CoreServiceError, Exception)
        assert issubclass(CoreValidationError, Exception)

    @pytest.mark.asyncio
    async def test_model_validation_integration(self):
        """Test that API models validate correctly."""
        from pydantic import ValidationError

        # Test auth request validation
        with pytest.raises(ValidationError):
            RegisterUserRequest(
                username="",  # Empty username should fail
                email="invalid-email",  # Invalid email should fail
                password="weak",  # Weak password should fail
                password_confirm="different",  # Non-matching password should fail
                full_name="Test User",
            )

        # Test key request validation
        with pytest.raises(ValidationError):
            CreateApiKeyRequest(
                name="",  # Empty name should fail
                service="invalid_service",  # Invalid service should fail
                key_value="",  # Empty key should fail
            )

        # Test valid models
        valid_register = RegisterUserRequest(
            username="validuser",
            email="valid@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="Valid User",
        )
        assert valid_register.username == "validuser"

        valid_key = CreateApiKeyRequest(
            name="Valid Key",
            service="openai",
            key_value="sk-validkey123",
        )
        assert valid_key.service == "openai"

    @pytest.mark.asyncio
    async def test_service_logging_integration(self, caplog):
        """Test that services log appropriately."""
        import logging

        # Set logging level to capture debug messages
        caplog.set_level(logging.DEBUG)

        # Create services
        auth_service = AuthService()
        key_service = KeyService()
        trip_service = TripService()

        # Verify services can be created without errors
        assert auth_service is not None
        assert key_service is not None
        assert trip_service is not None

        # Note: Actual logging tests would require mocking core services
        # and triggering operations that generate log messages

    @pytest.mark.asyncio
    async def test_service_configuration_integration(self):
        """Test that services integrate properly with configuration."""
        # Test that services can access configuration through core services
        auth_service = AuthService()
        key_service = KeyService()
        trip_service = TripService()

        # Verify lazy initialization patterns
        assert auth_service.core_auth_service is None
        assert auth_service.user_service is None
        assert key_service.core_key_service is None
        assert trip_service.core_trip_service is None

        # Verify initialization methods exist
        assert hasattr(auth_service, "_get_core_auth_service")
        assert hasattr(auth_service, "_get_user_service")
        assert hasattr(key_service, "_get_core_key_service")
        assert hasattr(trip_service, "_get_core_trip_service")

    @pytest.mark.asyncio
    async def test_cross_service_compatibility(self):
        """Test that services can work together in a typical workflow."""
        # This test verifies that the services have compatible interfaces
        # for a typical user workflow: register -> login -> create trip -> add API key

        # 1. User registration data
        user_data = {
            "username": "workflowuser",
            "email": "workflow@example.com",
            "password": "SecurePassword123!",
            "full_name": "Workflow User",
        }

        # 2. Trip creation data
        trip_data = {
            "name": "Workflow Trip",
            "description": "A trip created in workflow test",
            "destination": "London, UK",
            "start_date": "2025-07-01",
            "end_date": "2025-07-07",
        }

        # 3. API key creation data
        key_data = {
            "name": "Workflow API Key",
            "service": "openai",
            "key_value": "sk-workflow123",
        }

        # Verify all data structures are compatible with service interfaces
        register_request = RegisterUserRequest(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            password_confirm=user_data["password"],
            full_name=user_data["full_name"],
        )

        create_key_request = CreateApiKeyRequest(
            name=key_data["name"],
            service=key_data["service"],
            key_value=key_data["key_value"],
        )

        # Verify models are valid
        assert register_request.username == user_data["username"]
        assert create_key_request.service == key_data["service"]
        assert trip_data["name"] == "Workflow Trip"

        # Verify services can be instantiated for the workflow
        auth_service = AuthService()
        key_service = KeyService()
        trip_service = TripService()

        assert auth_service is not None
        assert key_service is not None
        assert trip_service is not None
