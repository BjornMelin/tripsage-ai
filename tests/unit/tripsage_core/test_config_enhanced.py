"""
Enhanced configuration testing for TripSage Core.

This module provides comprehensive testing for the CoreAppSettings and all
configuration classes with focus on:
- Environment variable validation and loading
- Supabase integration configuration
- Security validation for production environments
- Configuration class relationships and dependencies
- Error handling and validation edge cases
- Production readiness validation
- Backward compatibility properties
- Feature flag validation
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from tripsage_core.config.base_app_settings import (
    AgentConfig,
    CoreAppSettings,
    Crawl4AIConfig,
    DatabaseConfig,
    DragonflyConfig,
    FeatureFlags,
    LangGraphConfig,
    Mem0Config,
    OpenTelemetryConfig,
    get_settings,
    init_settings,
)


class TestDatabaseConfig:
    """Test DatabaseConfig class validation and properties."""

    def test_database_config_defaults(self):
        """Test default configuration values."""
        # Clear environment to test true defaults
        env_vars_to_clear = [
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "SUPABASE_JWT_SECRET",
            "SUPABASE_TIMEOUT",
            "SUPABASE_AUTO_REFRESH_TOKEN",
            "SUPABASE_PERSIST_SESSION",
            "SUPABASE_PGVECTOR_ENABLED",
            "SUPABASE_VECTOR_DIMENSIONS",
        ]

        with patch.dict(os.environ, {}, clear=False):
            for var in env_vars_to_clear:
                os.environ.pop(var, None)

            config = DatabaseConfig(_env_file=None)  # Don't load from .env file

            assert config.url == "https://test-project.supabase.co"
            assert config.anon_key.get_secret_value() == "test-anon-key"
            assert config.jwt_secret.get_secret_value() == "test-jwt-secret"
            assert config.timeout == 60.0
            assert config.auto_refresh_token is True
            assert config.persist_session is True
            assert config.pgvector_enabled is True
            assert config.vector_dimensions == 1536

    def test_database_config_environment_variables(self):
        """Test loading from environment variables."""
        env_vars = {
            "SUPABASE_URL": "https://custom-project.supabase.co",
            "SUPABASE_ANON_KEY": "custom-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "custom-service-role-key",
            "SUPABASE_JWT_SECRET": "custom-jwt-secret",
            "SUPABASE_PROJECT_ID": "custom-project-id",
            "SUPABASE_TIMEOUT": "90.0",
            "SUPABASE_AUTO_REFRESH_TOKEN": "false",
            "SUPABASE_PERSIST_SESSION": "false",
            "SUPABASE_PGVECTOR_ENABLED": "false",
            "SUPABASE_VECTOR_DIMENSIONS": "512",
        }

        with patch.dict(os.environ, env_vars):
            config = DatabaseConfig()

            assert config.url == "https://custom-project.supabase.co"
            assert config.anon_key.get_secret_value() == "custom-anon-key"
            assert (
                config.service_role_key.get_secret_value() == "custom-service-role-key"
            )
            assert config.jwt_secret.get_secret_value() == "custom-jwt-secret"
            assert config.project_id == "custom-project-id"
            assert config.timeout == 90.0
            assert config.auto_refresh_token is False
            assert config.persist_session is False
            assert config.pgvector_enabled is False
            assert config.vector_dimensions == 512

    def test_database_config_backward_compatibility_properties(self):
        """Test backward compatibility properties."""
        config = DatabaseConfig()

        # Test getters
        assert config.supabase_url == config.url
        assert config.supabase_anon_key == config.anon_key
        assert config.supabase_service_role_key == config.service_role_key
        assert config.supabase_jwt_secret == config.jwt_secret
        assert config.supabase_project_id == config.project_id
        assert config.supabase_timeout == config.timeout
        assert config.supabase_auto_refresh_token == config.auto_refresh_token
        assert config.supabase_persist_session == config.persist_session

    def test_database_config_backward_compatibility_setters(self):
        """Test backward compatibility setters."""
        from pydantic import SecretStr

        config = DatabaseConfig()

        # Test setters
        config.supabase_url = "https://new-url.supabase.co"
        assert config.url == "https://new-url.supabase.co"

        config.supabase_anon_key = SecretStr("new-anon-key")
        assert config.anon_key.get_secret_value() == "new-anon-key"

        config.supabase_service_role_key = SecretStr("new-service-key")
        assert config.service_role_key.get_secret_value() == "new-service-key"

        config.supabase_jwt_secret = SecretStr("new-jwt-secret")
        assert config.jwt_secret.get_secret_value() == "new-jwt-secret"

        config.supabase_project_id = "new-project-id"
        assert config.project_id == "new-project-id"

        config.supabase_timeout = 120.0
        assert config.timeout == 120.0

        config.supabase_auto_refresh_token = False
        assert config.auto_refresh_token is False

        config.supabase_persist_session = False
        assert config.persist_session is False

    def test_database_config_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SUPABASE_URL=https://env-file.supabase.co\n")
            f.write("SUPABASE_ANON_KEY=env-file-anon-key\n")
            f.write("SUPABASE_TIMEOUT=45.0\n")
            f.flush()

            # Clear environment first to avoid conflicts
            with patch.dict(os.environ, {}, clear=False):
                for key in list(os.environ.keys()):
                    if key.startswith("SUPABASE_"):
                        os.environ.pop(key, None)

                # Create config with custom env file
                config = DatabaseConfig(_env_file=f.name)

                assert config.url == "https://env-file.supabase.co"
                assert config.anon_key.get_secret_value() == "env-file-anon-key"
                assert config.timeout == 45.0

        # Clean up
        os.unlink(f.name)


class TestDragonflyConfig:
    """Test DragonflyConfig class validation and properties."""

    def test_dragonfly_config_defaults(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=False):
            # Clear any DRAGONFLY_ environment variables
            for key in list(os.environ.keys()):
                if key.startswith("DRAGONFLY_"):
                    os.environ.pop(key, None)

            config = DragonflyConfig(_env_file=None)

            assert config.url == "redis://localhost:6379/0"
            assert config.password is None
            assert config.ttl_short == 300
            assert config.ttl_medium == 3600
            assert config.ttl_long == 86400
            assert config.max_memory_policy == "allkeys-lru"
            assert config.max_memory == "4gb"
            assert config.max_connections == 10000
            assert config.thread_count == 4
            assert config.port == 6379

    def test_dragonfly_config_environment_variables(self):
        """Test loading from environment variables with DRAGONFLY_ prefix."""
        env_vars = {
            "DRAGONFLY_URL": "redis://production-dragonfly:6380/1",
            "DRAGONFLY_PASSWORD": "secure-password",
            "DRAGONFLY_TTL_SHORT": "600",
            "DRAGONFLY_TTL_MEDIUM": "7200",
            "DRAGONFLY_TTL_LONG": "172800",
            "DRAGONFLY_MAX_MEMORY_POLICY": "allkeys-random",
            "DRAGONFLY_MAX_MEMORY": "8gb",
            "DRAGONFLY_MAX_CONNECTIONS": "20000",
            "DRAGONFLY_THREAD_COUNT": "8",
            "DRAGONFLY_PORT": "6380",
        }

        with patch.dict(os.environ, env_vars):
            config = DragonflyConfig()

            assert config.url == "redis://production-dragonfly:6380/1"
            assert config.password == "secure-password"
            assert config.ttl_short == 600
            assert config.ttl_medium == 7200
            assert config.ttl_long == 172800
            assert config.max_memory_policy == "allkeys-random"
            assert config.max_memory == "8gb"
            assert config.max_connections == 20000
            assert config.thread_count == 8
            assert config.port == 6380

    def test_dragonfly_config_case_insensitive(self):
        """Test case insensitive environment variable loading."""
        env_vars = {
            "dragonfly_url": "redis://lowercase-test:6379/0",
            "DRAGONFLY_PASSWORD": "mixed-case-test",
        }

        with patch.dict(os.environ, env_vars):
            config = DragonflyConfig()

            assert config.url == "redis://lowercase-test:6379/0"
            assert config.password == "mixed-case-test"


class TestMem0Config:
    """Test Mem0Config class validation and properties."""

    def test_mem0_config_defaults(self):
        """Test default configuration values."""
        config = Mem0Config()

        assert config.vector_store_type == "pgvector"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimensions == 1536
        assert config.memory_types == [
            "user_preferences",
            "trip_history",
            "search_patterns",
            "conversation_context",
        ]
        assert config.max_memories_per_user == 1000
        assert config.memory_ttl_days == 365
        assert config.similarity_threshold == 0.7
        assert config.max_search_results == 10
        assert config.batch_size == 100
        assert config.async_processing is True

    def test_mem0_config_custom_memory_types(self):
        """Test custom memory types configuration."""
        custom_types = ["custom_preferences", "special_history"]

        config = Mem0Config(memory_types=custom_types)

        assert config.memory_types == custom_types

    def test_mem0_config_validation_ranges(self):
        """Test validation of numeric ranges."""
        # Test valid ranges
        config = Mem0Config(
            similarity_threshold=0.8, max_search_results=5, batch_size=50
        )

        assert config.similarity_threshold == 0.8
        assert config.max_search_results == 5
        assert config.batch_size == 50


class TestLangGraphConfig:
    """Test LangGraphConfig class validation and properties."""

    def test_langgraph_config_defaults(self):
        """Test default configuration values."""
        config = LangGraphConfig(_env_file=None)

        assert config.checkpoint_storage == "postgresql"
        assert config.enable_streaming is True
        assert config.max_graph_depth == 20
        assert config.default_agent_timeout == 300
        assert config.enable_parallel_execution is True
        assert config.max_parallel_agents == 5
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.enable_error_recovery is True
        assert config.enable_tracing is True
        assert config.trace_storage_days == 7

    def test_langgraph_config_performance_settings(self):
        """Test performance-related settings."""
        config = LangGraphConfig(
            max_graph_depth=50, max_parallel_agents=10, default_agent_timeout=600
        )

        assert config.max_graph_depth == 50
        assert config.max_parallel_agents == 10
        assert config.default_agent_timeout == 600


class TestCrawl4AIConfig:
    """Test Crawl4AIConfig class validation and properties."""

    def test_crawl4ai_config_defaults(self):
        """Test default configuration values."""
        config = Crawl4AIConfig()

        assert config.api_url == "http://localhost:8000/api"
        assert config.api_key is None
        assert config.timeout == 30000
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.default_format == "markdown"
        assert config.extract_metadata is True
        assert config.preserve_links is True
        assert config.concurrent_requests == 5
        assert config.rate_limit_delay == 0.5
        assert config.cache_enabled is True
        assert config.cache_ttl == 3600

    def test_crawl4ai_config_with_api_key(self):
        """Test configuration with API key."""
        from pydantic import SecretStr

        config = Crawl4AIConfig(api_key=SecretStr("test-api-key"))

        assert config.api_key.get_secret_value() == "test-api-key"


class TestAgentConfig:
    """Test AgentConfig class validation and properties."""

    def test_agent_config_defaults(self):
        """Test default configuration values."""
        config = AgentConfig()

        assert config.model_name == "gpt-4o"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.agent_timeout == 120
        assert config.max_retries == 3
        assert config.agent_memory_size == 10

        # Test default preferences
        assert config.default_flight_preferences["seat_class"] == "economy"
        assert config.default_flight_preferences["max_stops"] == 1
        assert config.default_accommodation_preferences["property_type"] == "hotel"
        assert config.default_accommodation_preferences["min_rating"] == 3.5

    def test_agent_config_custom_preferences(self):
        """Test custom preference configuration."""
        custom_flight_prefs = {
            "seat_class": "business",
            "max_stops": 0,
            "preferred_airlines": ["AA", "DL"],
            "time_window": "morning",
        }

        custom_accommodation_prefs = {
            "property_type": "apartment",
            "min_rating": 4.5,
            "amenities": ["wifi", "kitchen", "parking"],
            "location_preference": "downtown",
        }

        config = AgentConfig(
            default_flight_preferences=custom_flight_prefs,
            default_accommodation_preferences=custom_accommodation_prefs,
        )

        assert config.default_flight_preferences == custom_flight_prefs
        assert config.default_accommodation_preferences == custom_accommodation_prefs


class TestFeatureFlags:
    """Test FeatureFlags class validation and properties."""

    def test_feature_flags_defaults(self):
        """Test default feature flag values."""
        flags = FeatureFlags()

        # Agent features
        assert flags.enable_agent_memory is True
        assert flags.enable_parallel_agents is True
        assert flags.enable_streaming_responses is True

        # API features
        assert flags.enable_rate_limiting is True
        assert flags.enable_caching is True
        assert flags.enable_debug_mode is False

        # External integrations
        assert flags.enable_crawl4ai is True
        assert flags.enable_mem0 is True
        assert flags.enable_langgraph is True

    def test_feature_flags_custom_values(self):
        """Test custom feature flag values."""
        flags = FeatureFlags(
            enable_agent_memory=False, enable_debug_mode=True, enable_crawl4ai=False
        )

        assert flags.enable_agent_memory is False
        assert flags.enable_debug_mode is True
        assert flags.enable_crawl4ai is False


class TestOpenTelemetryConfig:
    """Test OpenTelemetryConfig class validation and properties."""

    def test_opentelemetry_config_defaults(self):
        """Test default configuration values."""
        config = OpenTelemetryConfig()

        assert config.enabled is True
        assert config.service_name == "tripsage"
        assert config.service_version == "1.0.0"
        assert config.otlp_endpoint is None
        assert config.use_console_exporter is True
        assert config.export_timeout_millis == 30000
        assert config.max_queue_size == 2048
        assert config.headers is None

    def test_opentelemetry_config_with_endpoint(self):
        """Test configuration with OTLP endpoint."""
        config = OpenTelemetryConfig(
            otlp_endpoint="http://localhost:4318/v1/traces",
            headers={"Authorization": "Bearer token"},
        )

        assert config.otlp_endpoint == "http://localhost:4318/v1/traces"
        assert config.headers == {"Authorization": "Bearer token"}


class TestCoreAppSettings:
    """Test CoreAppSettings main configuration class."""

    def test_core_app_settings_defaults(self):
        """Test default configuration values."""
        settings = CoreAppSettings()

        assert settings.app_name == "TripSage"
        assert settings.debug is False
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert isinstance(settings.base_dir, Path)

        # Check nested configurations
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.dragonfly, DragonflyConfig)
        assert isinstance(settings.mem0, Mem0Config)
        assert isinstance(settings.langgraph, LangGraphConfig)
        assert isinstance(settings.crawl4ai, Crawl4AIConfig)
        assert isinstance(settings.agent, AgentConfig)
        assert isinstance(settings.feature_flags, FeatureFlags)
        assert isinstance(settings.opentelemetry, OpenTelemetryConfig)

    def test_core_app_settings_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "testing", "staging", "production"]:
            settings = CoreAppSettings(environment=env)
            assert settings.environment == env

        # Invalid environment
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(environment="invalid")

        error = exc_info.value.errors()[0]
        assert "Environment must be one of" in error["msg"]

    def test_core_app_settings_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels (case insensitive)
        for level in ["DEBUG", "info", "Warning", "ERROR", "critical"]:
            settings = CoreAppSettings(log_level=level)
            assert settings.log_level == level.upper()

        # Invalid log level
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(log_level="invalid")

        error = exc_info.value.errors()[0]
        assert "Log level must be one of" in error["msg"]

    def test_core_app_settings_environment_methods(self):
        """Test environment checking methods."""
        # Development
        dev_settings = CoreAppSettings(environment="development")
        assert dev_settings.is_development() is True
        assert dev_settings.is_testing() is False
        assert dev_settings.is_production() is False

        # Testing
        test_settings = CoreAppSettings(environment="testing")
        assert test_settings.is_development() is False
        assert test_settings.is_testing() is True
        assert test_settings.is_production() is False

        # Production
        prod_settings = CoreAppSettings(environment="production")
        assert prod_settings.is_development() is False
        assert prod_settings.is_testing() is False
        assert prod_settings.is_production() is True

    def test_core_app_settings_get_secret_value(self):
        """Test get_secret_value method."""
        from pydantic import SecretStr

        settings = CoreAppSettings(openai_api_key=SecretStr("test-openai-key"))

        # Valid secret
        assert settings.get_secret_value("openai_api_key") == "test-openai-key"

        # Non-existent key
        assert settings.get_secret_value("nonexistent_key") is None

        # Non-secret attribute
        assert settings.get_secret_value("app_name") is None

    def test_core_app_settings_validate_critical_settings_development(self):
        """Test critical settings validation in development."""
        settings = CoreAppSettings(environment="development")

        # Should pass with default test values
        errors = settings.validate_critical_settings()
        assert len(errors) == 0

    def test_core_app_settings_validate_critical_settings_production_missing_keys(self):
        """Test critical settings validation in production with missing keys."""
        from pydantic import SecretStr

        settings = CoreAppSettings(
            environment="production",
            openai_api_key=SecretStr(""),  # Empty OpenAI key
        )
        settings.database.supabase_url = ""  # Empty Supabase URL

        errors = settings.validate_critical_settings()

        # Should have multiple errors for missing keys
        assert len(errors) > 0
        assert any("OpenAI API key is missing" in error for error in errors)
        assert any("Supabase URL is missing" in error for error in errors)

    def test_core_app_settings_validate_critical_settings_production_debug_mode(self):
        """Test production validation with debug mode enabled."""
        settings = CoreAppSettings(environment="production", debug=True)

        errors = settings.validate_critical_settings()

        assert any(
            "Debug mode should be disabled in production" in error for error in errors
        )

    def test_core_app_settings_validate_critical_settings_production_localhost_services(
        self,
    ):
        """Test production validation with localhost services."""
        settings = CoreAppSettings(environment="production")

        # Set localhost URLs
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.crawl4ai.api_url = "http://localhost:8000/api"

        errors = settings.validate_critical_settings()

        assert any(
            "DragonflyDB is using localhost in production" in error for error in errors
        )
        assert any(
            "Crawl4AI is using localhost in production" in error for error in errors
        )

    def test_core_app_settings_validate_critical_settings_production_default_secrets(
        self,
    ):
        """Test production validation with default secrets."""
        from pydantic import SecretStr

        settings = CoreAppSettings(
            environment="production",
            api_key_master_secret=SecretStr("master-secret-for-byok-encryption"),
        )
        settings.database.jwt_secret = SecretStr("test-jwt-secret")

        errors = settings.validate_critical_settings()

        assert any(
            "API key master secret must be changed in production" in error
            for error in errors
        )
        assert any(
            "Supabase JWT secret must be changed in production" in error
            for error in errors
        )

    def test_core_app_settings_validate_critical_settings_production_fallback_secret(
        self,
    ):
        """Test production validation with fallback JWT secret."""
        from pydantic import SecretStr

        settings = CoreAppSettings(environment="production")
        settings.database.jwt_secret = SecretStr("fallback-secret-for-development-only")

        errors = settings.validate_critical_settings()

        assert any(
            "Supabase JWT secret must be changed in production" in error
            for error in errors
        )

    def test_core_app_settings_nested_config_integration(self):
        """Test that nested configurations are properly integrated."""
        settings = CoreAppSettings()

        # Test that changes to nested configs are reflected
        settings.database.timeout = 120.0
        assert settings.database.timeout == 120.0

        settings.dragonfly.ttl_short = 600
        assert settings.dragonfly.ttl_short == 600

        settings.feature_flags.enable_debug_mode = True
        assert settings.feature_flags.enable_debug_mode is True


class TestConfigurationLoading:
    """Test configuration loading patterns and environment handling."""

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to @lru_cache
        assert settings1 is settings2

    def test_init_settings_success(self):
        """Test successful settings initialization."""
        # Mock logging to avoid log output during tests
        with patch("logging.info"), patch("logging.debug"):
            settings = init_settings()

            assert isinstance(settings, CoreAppSettings)
            assert settings.environment in [
                "development",
                "testing",
                "staging",
                "production",
            ]

    def test_init_settings_validation_failure(self):
        """Test settings initialization with validation failures."""
        # Create settings that will fail production validation
        with patch(
            "tripsage_core.config.base_app_settings.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.environment = "production"
            mock_settings.validate_critical_settings.return_value = [
                "OpenAI API key is missing",
                "Supabase URL is missing",
            ]
            mock_get_settings.return_value = mock_settings

            with patch("logging.info"), patch("logging.error"):
                with pytest.raises(ValueError) as exc_info:
                    init_settings()

                assert "Critical settings validation failed" in str(exc_info.value)

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over defaults."""
        env_vars = {
            "APP_NAME": "CustomTripSage",
            "DEBUG": "true",
            "ENVIRONMENT": "staging",
            "LOG_LEVEL": "DEBUG",
            "SUPABASE_URL": "https://custom.supabase.co",
            "DRAGONFLY_TTL_SHORT": "900",
        }

        with patch.dict(os.environ, env_vars):
            settings = CoreAppSettings()

            assert settings.app_name == "CustomTripSage"
            assert settings.debug is True
            assert settings.environment == "staging"
            assert settings.log_level == "DEBUG"
            assert settings.database.url == "https://custom.supabase.co"
            assert settings.dragonfly.ttl_short == 900

    def test_configuration_inheritance_and_overrides(self):
        """Test configuration inheritance and override patterns."""
        # Test that nested configurations can be overridden
        custom_database = DatabaseConfig(
            url="https://override.supabase.co", timeout=90.0
        )

        custom_dragonfly = DragonflyConfig(url="redis://override:6379/1", ttl_short=600)

        settings = CoreAppSettings(database=custom_database, dragonfly=custom_dragonfly)

        assert settings.database.url == "https://override.supabase.co"
        assert settings.database.timeout == 90.0
        assert settings.dragonfly.url == "redis://override:6379/1"
        assert settings.dragonfly.ttl_short == 600

    def test_model_config_validation(self):
        """Test model configuration settings."""
        settings = CoreAppSettings()

        # Check model config is properly set
        assert settings.model_config["case_sensitive"] is False
        assert settings.model_config["extra"] == "ignore"
        assert settings.model_config["validate_default"] is True

    def test_secret_handling(self):
        """Test proper secret handling across configurations."""
        from pydantic import SecretStr

        settings = CoreAppSettings(
            openai_api_key=SecretStr("secret-openai-key"),
            google_maps_api_key=SecretStr("secret-maps-key"),
        )

        # Secrets should be properly wrapped
        assert isinstance(settings.openai_api_key, SecretStr)
        assert isinstance(settings.google_maps_api_key, SecretStr)

        # Should be able to get secret values
        assert settings.openai_api_key.get_secret_value() == "secret-openai-key"
        assert settings.google_maps_api_key.get_secret_value() == "secret-maps-key"

        # Repr should not expose secrets
        settings_repr = repr(settings)
        assert "secret-openai-key" not in settings_repr
        assert "secret-maps-key" not in settings_repr


class TestConfigurationErrorHandling:
    """Test error handling and edge cases in configuration."""

    def test_invalid_environment_value(self):
        """Test handling of invalid environment values."""
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(environment="invalid_env")

        error = exc_info.value.errors()[0]
        assert error["type"] == "value_error"
        assert "Environment must be one of" in error["msg"]

    def test_invalid_log_level_value(self):
        """Test handling of invalid log level values."""
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(log_level="INVALID_LEVEL")

        error = exc_info.value.errors()[0]
        assert error["type"] == "value_error"
        assert "Log level must be one of" in error["msg"]

    def test_configuration_with_none_values(self):
        """Test configuration with None values for optional fields."""
        settings = CoreAppSettings(
            google_maps_api_key=None,
            google_client_id=None,
            openweathermap_api_key=None,
            duffel_api_key=None,
        )

        assert settings.google_maps_api_key is None
        assert settings.google_client_id is None
        assert settings.openweathermap_api_key is None
        assert settings.duffel_api_key is None

    def test_validate_critical_settings_empty_list(self):
        """Test validate_critical_settings returns empty list for valid config."""
        # Use development environment which is less strict
        settings = CoreAppSettings(environment="development")

        errors = settings.validate_critical_settings()
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_nested_config_validation_errors(self):
        """Test that validation errors in nested configs are handled properly."""
        # This would test if validation errors in nested configs bubble up properly
        # Since our current nested configs don't have strict validation,
        # we test that they at least initialize properly
        settings = CoreAppSettings()

        # All nested configs should be valid
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.dragonfly, DragonflyConfig)
        assert isinstance(settings.mem0, Mem0Config)
        assert isinstance(settings.langgraph, LangGraphConfig)
        assert isinstance(settings.crawl4ai, Crawl4AIConfig)
        assert isinstance(settings.agent, AgentConfig)
        assert isinstance(settings.feature_flags, FeatureFlags)
        assert isinstance(settings.opentelemetry, OpenTelemetryConfig)


class TestProductionReadinessValidation:
    """Test production readiness validation comprehensively."""

    def test_production_readiness_all_requirements_met(self):
        """Test production readiness when all requirements are met."""
        from pydantic import SecretStr

        settings = CoreAppSettings(
            environment="production",
            debug=False,
            openai_api_key=SecretStr("prod-openai-key"),
            google_maps_api_key=SecretStr("prod-maps-key"),
            openweathermap_api_key=SecretStr("prod-weather-key"),
            duffel_api_key=SecretStr("prod-duffel-key"),
            api_key_master_secret=SecretStr("production-master-secret"),
        )

        # Set production URLs
        settings.database.url = "https://production.supabase.co"
        settings.database.anon_key = SecretStr("production-anon-key")
        settings.database.jwt_secret = SecretStr("production-jwt-secret")
        settings.dragonfly.url = "redis://production-dragonfly:6379/0"
        settings.crawl4ai.api_url = "https://production-crawl4ai.com/api"

        errors = settings.validate_critical_settings()
        assert len(errors) == 0

    def test_production_readiness_missing_external_api_keys(self):
        """Test production readiness with missing external API keys."""
        settings = CoreAppSettings(environment="production")

        errors = settings.validate_critical_settings()

        # Should have errors for missing production API keys
        expected_missing = [
            "Duffel API key is missing for production",
            "Google Maps API key is missing for production",
            "OpenWeatherMap API key is missing for production",
        ]

        for expected_error in expected_missing:
            assert any(expected_error in error for error in errors)

    def test_production_readiness_localhost_detection(self):
        """Test production readiness localhost detection."""
        settings = CoreAppSettings(environment="production")

        # Set localhost URLs (should be detected)
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.crawl4ai.api_url = "http://localhost:8000/api"

        errors = settings.validate_critical_settings()

        assert any(
            "DragonflyDB is using localhost in production" in error for error in errors
        )
        assert any(
            "Crawl4AI is using localhost in production" in error for error in errors
        )

    def test_production_readiness_insecure_secrets_detection(self):
        """Test production readiness insecure secrets detection."""
        from pydantic import SecretStr

        settings = CoreAppSettings(
            environment="production",
            api_key_master_secret=SecretStr("master-secret-for-byok-encryption"),
        )
        settings.database.jwt_secret = SecretStr("test-jwt-secret")

        errors = settings.validate_critical_settings()

        assert any(
            "API key master secret must be changed in production" in error
            for error in errors
        )
        assert any(
            "Supabase JWT secret must be changed in production" in error
            for error in errors
        )

    def test_staging_environment_validation(self):
        """Test validation in staging environment (less strict than production)."""
        settings = CoreAppSettings(environment="staging")

        # Staging should be less strict than production
        errors = settings.validate_critical_settings()

        # Should only check core requirements, not production-specific ones
        # (our current implementation treats staging same as development)
        assert len(errors) == 0 or all(
            "production" not in error.lower() for error in errors
        )

    def test_testing_environment_validation(self):
        """Test validation in testing environment."""
        settings = CoreAppSettings(environment="testing")

        errors = settings.validate_critical_settings()

        # Testing environment should allow test/mock values
        assert len(errors) == 0 or all(
            "production" not in error.lower() for error in errors
        )
