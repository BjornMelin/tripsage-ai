"""
Example of how to write clean, robust tests using the new test configuration approach.

This demonstrates the proper patterns for testing TripSage components without
Pydantic validation errors or complex mocking setups.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import our clean test utilities
from tests.test_config import create_test_settings, MockCacheService, MockDatabaseService


class TestExampleService:
    """Example test class showing clean testing patterns."""

    def test_service_with_clean_settings(self):
        """Test a service using clean settings configuration."""
        # Create test settings - no validation errors
        settings = create_test_settings(
            environment="testing",
            debug=True,
        )
        
        # Verify settings are properly configured
        assert settings.environment == "testing"
        assert settings.debug is True
        assert settings.database.supabase_url == "https://test-project.supabase.co"
        assert settings.openai_api_key.get_secret_value() == "sk-test-openai-key-1234567890abcdef"

    @pytest.mark.asyncio
    async def test_service_with_mocked_dependencies(self):
        """Test a service with properly mocked dependencies."""
        # Use our reliable mock services
        mock_cache = MockCacheService()
        mock_db = MockDatabaseService()
        
        # Set up test data
        await mock_cache.set_json("test_key", {"data": "test_value"})
        
        # Test cache functionality
        result = await mock_cache.get_json("test_key")
        assert result == {"data": "test_value"}
        
        # Test database functionality
        assert await mock_db.health_check() is True

    def test_service_with_environment_override(self):
        """Test service behavior with specific environment settings."""
        # Create settings with specific overrides
        settings = create_test_settings(
            environment="production",
            debug=False,
        )
        
        # Verify the overrides work
        assert settings.environment == "production"
        assert settings.debug is False
        
        # Test production validation
        errors = settings.validate_critical_settings()
        # Should have errors since we're using test API keys in production
        assert len(errors) > 0


class TestExampleBusinessLogic:
    """Example of testing business logic without complex setup."""

    def test_simple_validation_logic(self):
        """Test simple validation without external dependencies."""
        # This kind of test doesn't need any special setup
        from tripsage_core.models.schemas_common.enums import TripStatus
        
        # Test enum values
        assert TripStatus.PLANNING == "planning"
        assert TripStatus.IN_PROGRESS == "in_progress"
        assert TripStatus.COMPLETED == "completed"

    def test_with_factory_data(self, sample_trip, sample_user):
        """Test using factory-generated test data."""
        # sample_trip and sample_user come from our conftest fixtures
        assert sample_trip["name"] == "Tokyo Adventure"
        assert sample_user["email"] == "test@example.com"
        
        # Test business logic with the factory data
        assert sample_trip["user_id"] == sample_user["id"]

    @pytest.mark.asyncio
    async def test_async_service_call(self, mock_chat_service):
        """Test async service calls with clean mocking."""
        # Mock service is already configured in conftest
        result = await mock_chat_service.process_message("Hello")
        
        assert result["response"] == "Test response"
        assert result["status"] == "completed"
        mock_chat_service.process_message.assert_called_once_with("Hello")


class TestExampleIntegration:
    """Example of integration testing with minimal setup."""

    @pytest.mark.asyncio
    async def test_service_integration(self):
        """Test service integration without full app startup."""
        # Use clean mocking to avoid dependency issues
        with (
            patch("tripsage_core.config.base_app_settings.get_settings", 
                  side_effect=lambda: create_test_settings()),
            patch("tripsage_core.services.infrastructure.cache_service.get_cache_service",
                  return_value=MockCacheService()),
        ):
            # Import and test the service
            from tripsage_core.services.business.chat_service import ChatService
            
            # The service can now be instantiated without validation errors
            # Note: This is just an example - the actual service may have different initialization
            service = ChatService()
            assert service is not None

    def test_settings_validation_patterns(self):
        """Test different settings validation patterns."""
        # Test valid configuration
        settings = create_test_settings(environment="testing")
        errors = settings.validate_critical_settings()
        # Should be empty since we use valid test values
        assert len(errors) == 0
        
        # Test with missing required settings 
        # Note: We can't easily test this with None since it would fail Pydantic validation
        # This is just to show the testing pattern
        settings_invalid = create_test_settings(environment="production")
        errors = settings_invalid.validate_critical_settings()
        # Should have errors since we're using test API keys in production
        assert len(errors) > 0


class TestExampleErrorHandling:
    """Example of testing error conditions cleanly."""

    def test_validation_error_handling(self):
        """Test how validation errors are handled."""
        from pydantic import ValidationError
        from tripsage_core.config.base_app_settings import DatabaseConfig
        
        # Test invalid configuration
        with pytest.raises(ValidationError):
            DatabaseConfig(supabase_timeout="not-a-number")

    @pytest.mark.asyncio  
    async def test_async_error_handling(self):
        """Test async error handling patterns."""
        # Use our mock service directly 
        mock_cache = MockCacheService()
        mock_cache.get_json = AsyncMock(side_effect=Exception("Cache error"))
        
        # Test that errors are handled appropriately
        with pytest.raises(Exception, match="Cache error"):
            await mock_cache.get_json("test_key")


class TestExamplePerformance:
    """Example of performance testing patterns."""

    def test_settings_instantiation_performance(self, performance_timer):
        """Test that settings instantiation is fast."""
        performance_timer.start()
        
        # Create multiple settings instances
        for _ in range(100):
            create_test_settings()
        
        performance_timer.stop()
        
        # Should complete quickly
        assert performance_timer.elapsed < 1.0

    def test_cache_operation_performance(self, performance_timer):
        """Test cache operation performance."""
        cache = MockCacheService()
        
        performance_timer.start()
        
        # Perform many cache operations
        for i in range(1000):
            cache._storage[f"key_{i}"] = f"value_{i}"
        
        performance_timer.stop()
        
        # Should complete very quickly
        assert performance_timer.elapsed < 0.1


# Additional examples of testing patterns

@pytest.mark.asyncio
async def test_standalone_async_function():
    """Example of standalone async test function."""
    # Simple async test without class
    result = await AsyncMock(return_value="test_result")()
    assert result == "test_result"


def test_with_multiple_fixtures(sample_user, sample_trip, mock_settings):
    """Example using multiple fixtures together."""
    # All fixtures are available and properly configured
    assert sample_user["id"] == sample_trip["user_id"]
    assert mock_settings.environment == "testing"


@pytest.mark.parametrize("environment,debug", [
    ("development", True),
    ("testing", True), 
    ("staging", False),
    ("production", False),
])
def test_environment_configurations(environment, debug):
    """Example of parametrized testing with settings."""
    settings = create_test_settings(environment=environment, debug=debug)
    assert settings.environment == environment
    assert settings.debug == debug