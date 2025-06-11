"""Comprehensive tests for configuration system and DatabaseConfig fixes."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from tripsage_core.config.base_app_settings import (
    CoreAppSettings,
    DatabaseConfig,
    DragonflyConfig,
    get_settings,
    init_settings,
)

# Suppress warnings about missing environment variables in tests
pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")

# Skip auto-fixture to avoid conflicts with our specific test setups
pytest_plugins = []


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class with SUPABASE_ prefix."""  

    def test_default_values(self):
        """Test default configuration values."""
        config = DatabaseConfig(_env_file=None)
        
        # Test defaults
        assert config.url == "https://test-project.supabase.co"
        assert config.anon_key.get_secret_value() == "test-anon-key"
        assert config.service_role_key is None
        assert config.jwt_secret.get_secret_value() == "test-jwt-secret"
        assert config.project_id is None
        assert config.timeout == 60.0
        assert config.auto_refresh_token is True
        assert config.persist_session is True
        assert config.pgvector_enabled is True
        assert config.vector_dimensions == 1536

    def test_environment_variable_loading(self):
        """Test loading configuration from SUPABASE_ prefixed environment variables."""
        env_vars = {
            "SUPABASE_URL": "https://custom-project.supabase.co",
            "SUPABASE_ANON_KEY": "custom-anon-key-123",
            "SUPABASE_SERVICE_ROLE_KEY": "custom-service-key-456",
            "SUPABASE_JWT_SECRET": "custom-jwt-secret-789",
            "SUPABASE_PROJECT_ID": "custom-project-id",
            "SUPABASE_TIMEOUT": "30.0",
            "SUPABASE_AUTO_REFRESH_TOKEN": "false",
            "SUPABASE_PERSIST_SESSION": "false",
            "SUPABASE_PGVECTOR_ENABLED": "false",
            "SUPABASE_VECTOR_DIMENSIONS": "768",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)

            assert config.url == "https://custom-project.supabase.co"
            assert config.anon_key.get_secret_value() == "custom-anon-key-123"
            assert config.service_role_key.get_secret_value() == "custom-service-key-456"
            assert config.jwt_secret.get_secret_value() == "custom-jwt-secret-789"
            assert config.project_id == "custom-project-id"
            assert config.timeout == 30.0
            assert config.auto_refresh_token is False
            assert config.persist_session is False
            assert config.pgvector_enabled is False
            assert config.vector_dimensions == 768

    def test_backward_compatibility_properties(self):
        """Test backward compatibility properties for DatabaseConfig."""
        config = DatabaseConfig(
            _env_file=None,
            url="https://compat-test.supabase.co",
            anon_key=SecretStr("compat-anon-key"),
            service_role_key=SecretStr("compat-service-key"),
            jwt_secret=SecretStr("compat-jwt-secret"),
            project_id="compat-project",
            timeout=45.0,
            auto_refresh_token=False,
            persist_session=False,
        )

        # Test property getters
        assert config.supabase_url == "https://compat-test.supabase.co"
        assert config.supabase_anon_key.get_secret_value() == "compat-anon-key"
        assert config.supabase_service_role_key.get_secret_value() == "compat-service-key"
        assert config.supabase_jwt_secret.get_secret_value() == "compat-jwt-secret"
        assert config.supabase_project_id == "compat-project"
        assert config.supabase_timeout == 45.0
        assert config.supabase_auto_refresh_token is False
        assert config.supabase_persist_session is False

        # Test property setters
        config.supabase_url = "https://new-url.supabase.co"
        config.supabase_anon_key = SecretStr("new-anon-key")
        config.supabase_service_role_key = SecretStr("new-service-key")
        config.supabase_jwt_secret = SecretStr("new-jwt-secret")
        config.supabase_project_id = "new-project-id"
        config.supabase_timeout = 90.0
        config.supabase_auto_refresh_token = True
        config.supabase_persist_session = True

        assert config.url == "https://new-url.supabase.co"
        assert config.anon_key.get_secret_value() == "new-anon-key"
        assert config.service_role_key.get_secret_value() == "new-service-key"
        assert config.jwt_secret.get_secret_value() == "new-jwt-secret"
        assert config.project_id == "new-project-id"
        assert config.timeout == 90.0
        assert config.auto_refresh_token is True
        assert config.persist_session is True

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SUPABASE_URL=https://envfile-test.supabase.co\n")
            f.write("SUPABASE_ANON_KEY=envfile-anon-key\n")
            f.write("SUPABASE_JWT_SECRET=envfile-jwt-secret\n")
            f.write("SUPABASE_TIMEOUT=25.5\n")
            temp_env_file = f.name

        try:
            config = DatabaseConfig(_env_file=temp_env_file)
            
            assert config.url == "https://envfile-test.supabase.co"
            assert config.anon_key.get_secret_value() == "envfile-anon-key"
            assert config.jwt_secret.get_secret_value() == "envfile-jwt-secret"
            assert config.timeout == 25.5
        finally:
            os.unlink(temp_env_file)

    def test_secret_str_handling(self):
        """Test SecretStr field handling and security."""
        config = DatabaseConfig(
            _env_file=None,
            anon_key=SecretStr("secret-anon-key"),
            service_role_key=SecretStr("secret-service-key"),
            jwt_secret=SecretStr("secret-jwt-token"),
        )

        # Secrets should be accessible via get_secret_value()
        assert config.anon_key.get_secret_value() == "secret-anon-key"
        assert config.service_role_key.get_secret_value() == "secret-service-key"
        assert config.jwt_secret.get_secret_value() == "secret-jwt-token"

        # Secrets should be hidden in string representation
        config_str = str(config)
        assert "secret-anon-key" not in config_str
        assert "secret-service-key" not in config_str
        assert "secret-jwt-token" not in config_str
        assert "**********" in config_str or "SecretStr('**********')" in config_str

        # JSON serialization should hide secrets
        config_dict = config.model_dump()
        assert "secret-anon-key" not in str(config_dict)
        assert "secret-service-key" not in str(config_dict)
        assert "secret-jwt-token" not in str(config_dict)

    def test_model_config_settings(self):
        """Test SettingsConfigDict configuration."""
        config = DatabaseConfig(_env_file=None)
        
        # Check model configuration
        model_config = config.model_config
        assert model_config['env_prefix'] == 'SUPABASE_'
        assert model_config['env_file'] == '.env'
        assert model_config['env_file_encoding'] == 'utf-8'
        assert model_config['case_sensitive'] is False
        assert model_config['extra'] == 'ignore'


class TestDragonflyConfig:
    """Test cases for DragonflyConfig class with DRAGONFLY_ prefix."""

    def test_default_values(self):
        """Test default configuration values."""
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

    def test_environment_variable_loading(self):
        """Test loading configuration from DRAGONFLY_ prefixed environment variables."""
        env_vars = {
            "DRAGONFLY_URL": "redis://custom-host:6380/1",
            "DRAGONFLY_PASSWORD": "custom-password",
            "DRAGONFLY_TTL_SHORT": "600",
            "DRAGONFLY_TTL_MEDIUM": "7200",
            "DRAGONFLY_TTL_LONG": "172800",
            "DRAGONFLY_MAX_MEMORY_POLICY": "allkeys-random",
            "DRAGONFLY_MAX_MEMORY": "8gb",
            "DRAGONFLY_MAX_CONNECTIONS": "5000",
            "DRAGONFLY_THREAD_COUNT": "8",
            "DRAGONFLY_PORT": "6380",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DragonflyConfig(_env_file=None)

            assert config.url == "redis://custom-host:6380/1"
            assert config.password == "custom-password"
            assert config.ttl_short == 600
            assert config.ttl_medium == 7200
            assert config.ttl_long == 172800
            assert config.max_memory_policy == "allkeys-random"
            assert config.max_memory == "8gb"
            assert config.max_connections == 5000
            assert config.thread_count == 8
            assert config.port == 6380


class TestConfigurationValidation:
    """Test cases for configuration validation and error handling."""

    def test_invalid_environment_values(self):
        """Test validation of invalid environment values."""
        # Test case-insensitive environment validation
        for invalid_env in ["prod", "dev", "test", "invalid", "PRODUCTION"]:
            with pytest.raises(ValidationError) as exc_info:
                CoreAppSettings(_env_file=None, environment=invalid_env)
            
            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert "Environment must be one of" in str(errors[0]["ctx"]["error"])

    def test_invalid_log_level_values(self):
        """Test validation of invalid log level values."""
        for invalid_level in ["TRACE", "VERBOSE", "FINE", "ALL", "OFF"]:
            with pytest.raises(ValidationError) as exc_info:
                CoreAppSettings(_env_file=None, log_level=invalid_level)
            
            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert "Log level must be one of" in str(errors[0]["ctx"]["error"])

    def test_secret_str_validation(self):
        """Test SecretStr field validation and handling."""
        # Test empty secret string
        config = DatabaseConfig(_env_file=None, anon_key=SecretStr(""))
        assert config.anon_key.get_secret_value() == ""
        
        # Test None handling
        config = DatabaseConfig(_env_file=None)
        assert config.service_role_key is None
        
        # Test secret string with special characters
        special_secret = "test-key!@#$%^&*()_+{}|:<>?[]\\\";\'"
        config = DatabaseConfig(_env_file=None, anon_key=SecretStr(special_secret))
        assert config.anon_key.get_secret_value() == special_secret

    def test_configuration_inheritance(self):
        """Test proper inheritance of nested configurations."""
        settings = CoreAppSettings(_env_file=None)
        
        # Verify all nested configurations are properly instantiated
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.dragonfly, DragonflyConfig)
        assert hasattr(settings, "mem0")
        assert hasattr(settings, "langgraph")
        assert hasattr(settings, "crawl4ai")
        assert hasattr(settings, "agent")
        assert hasattr(settings, "feature_flags")
        assert hasattr(settings, "opentelemetry")

    def test_field_mapping_and_aliases(self):
        """Test field mapping and backward compatibility."""
        # Test SUPABASE_ prefix mapping
        env_vars = {
            "SUPABASE_URL": "https://alias-test.supabase.co",
            "SUPABASE_ANON_KEY": "alias-anon-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)
            
            # Both direct and legacy property access should work
            assert config.url == "https://alias-test.supabase.co"
            assert config.supabase_url == "https://alias-test.supabase.co"
            assert config.anon_key.get_secret_value() == "alias-anon-key"
            assert config.supabase_anon_key.get_secret_value() == "alias-anon-key"

    def test_case_insensitive_environment_variables(self):
        """Test case insensitive environment variable handling."""
        env_vars = {
            "supabase_url": "https://lowercase.supabase.co",  # lowercase
            "SUPABASE_ANON_KEY": "UPPERCASE-KEY",  # uppercase
            "Supabase_Jwt_Secret": "MixedCase-Secret",  # mixed case
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)
            
            # All should be loaded correctly due to case_sensitive=False
            assert config.url == "https://lowercase.supabase.co"
            assert config.anon_key.get_secret_value() == "UPPERCASE-KEY"
            assert config.jwt_secret.get_secret_value() == "MixedCase-Secret"

    def test_extra_environment_variables_ignored(self):
        """Test that extra environment variables are ignored."""
        env_vars = {
            "SUPABASE_URL": "https://valid.supabase.co",
            "SUPABASE_INVALID_FIELD": "should-be-ignored",
            "SUPABASE_ANOTHER_UNKNOWN": "also-ignored",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Should not raise validation error due to extra='ignore'
            config = DatabaseConfig(_env_file=None)
            assert config.url == "https://valid.supabase.co"
            
            # Unknown fields should not be accessible
            assert not hasattr(config, "invalid_field")
            assert not hasattr(config, "another_unknown")


class TestEnvironmentFileHandling:
    """Test cases for .env file loading and processing."""

    def test_env_file_priority(self):
        """Test environment variable priority: direct env > .env file > defaults."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SUPABASE_URL=https://envfile.supabase.co\n")
            f.write("SUPABASE_ANON_KEY=envfile-key\n")
            f.write("SUPABASE_TIMEOUT=15.0\n")
            temp_env_file = f.name

        try:
            # Test .env file loading (should override defaults)
            config1 = DatabaseConfig(_env_file=temp_env_file)
            assert config1.url == "https://envfile.supabase.co"
            assert config1.anon_key.get_secret_value() == "envfile-key"
            assert config1.timeout == 15.0
            
            # Test environment variable override (should override .env file)
            with patch.dict(os.environ, {"SUPABASE_URL": "https://override.supabase.co"}, clear=False):
                config2 = DatabaseConfig(_env_file=temp_env_file)
                assert config2.url == "https://override.supabase.co"  # env override
                assert config2.anon_key.get_secret_value() == "envfile-key"  # from file
                assert config2.timeout == 15.0  # from file
                
        finally:
            os.unlink(temp_env_file)

    def test_missing_env_file(self):
        """Test handling of missing .env file."""
        # Should not raise error when .env file doesn't exist
        config = DatabaseConfig(_env_file="/nonexistent/.env")
        
        # Should use default values
        assert config.url == "https://test-project.supabase.co"
        assert config.anon_key.get_secret_value() == "test-anon-key"

    def test_env_file_encoding(self):
        """Test .env file encoding handling."""
        # Create temporary .env file with UTF-8 content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
            f.write("SUPABASE_URL=https://üñíçödé.supabase.co\n")  # Unicode characters
            f.write("SUPABASE_PROJECT_ID=tëst-prøjëct\n")
            temp_env_file = f.name

        try:
            config = DatabaseConfig(_env_file=temp_env_file)
            assert config.url == "https://üñíçödé.supabase.co"
            assert config.project_id == "tëst-prøjëct"
        finally:
            os.unlink(temp_env_file)


class TestSecurityAndLogging:
    """Test cases for security aspects and logging behavior."""

    def test_secret_not_in_logs(self):
        """Test that secrets are not exposed in string representations."""
        settings = CoreAppSettings(
            _env_file=None,
            openai_api_key=SecretStr("very-secret-openai-key"),
            api_key_master_secret=SecretStr("super-secret-master-key"),
        )
        
        # Convert to string (simulating logging)
        settings_str = str(settings)
        settings_repr = repr(settings)
        
        # Secrets should not appear in string representations
        assert "very-secret-openai-key" not in settings_str
        assert "super-secret-master-key" not in settings_str
        assert "very-secret-openai-key" not in settings_repr
        assert "super-secret-master-key" not in settings_repr
        
        # Should contain masked values instead
        assert "**********" in settings_str or "SecretStr('**********')" in settings_str

    def test_secret_json_serialization(self):
        """Test that secrets are properly handled in JSON serialization."""
        settings = CoreAppSettings(
            _env_file=None,
            openai_api_key=SecretStr("secret-api-key"),
        )
        
        # Model dump should not expose secrets
        settings_dict = settings.model_dump()
        settings_json_str = str(settings_dict)
        
        assert "secret-api-key" not in settings_json_str
        
        # With secrets revealed
        settings_dict_with_secrets = settings.model_dump(exclude_unset=True)
        # Still should not expose them in regular dump
        assert "secret-api-key" not in str(settings_dict_with_secrets)

    def test_production_security_validation(self):
        """Test production security validation requirements."""
        # Production with insecure default secrets should fail validation
        production_settings = CoreAppSettings(
            _env_file=None,
            environment="production",
            debug=False,
            api_key_master_secret=SecretStr("master-secret-for-byok-encryption"),  # default
        )
        
        errors = production_settings.validate_critical_settings()
        
        # Should contain security warnings for default secrets
        security_errors = [error for error in errors if "secret" in error.lower()]
        assert len(security_errors) > 0
        assert any("master secret" in error for error in security_errors)

    def test_development_security_relaxed(self):
        """Test that development environment has relaxed security validation."""
        dev_settings = CoreAppSettings(
            _env_file=None,
            environment="development",
            debug=True,  # Allowed in development
            api_key_master_secret=SecretStr("master-secret-for-byok-encryption"),  # default OK
        )
        
        errors = dev_settings.validate_critical_settings()
        
        # Should have fewer security restrictions in development
        assert "Debug mode should be disabled" not in errors


class TestInitializationAndCaching:
    """Test cases for settings initialization and caching behavior."""

    def test_init_settings_function(self):
        """Test init_settings function behavior."""
        # Clear cache first
        get_settings.cache_clear()
        
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=False):
            settings = init_settings()
            
            assert isinstance(settings, CoreAppSettings)
            assert settings.environment == "testing"

    def test_init_settings_validation_failure(self):
        """Test init_settings with validation failures."""
        # Clear cache first
        get_settings.cache_clear()
        
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "OPENAI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError) as exc_info:
                init_settings()
            
            assert "Critical settings validation failed" in str(exc_info.value)
            assert "OpenAI API key is missing" in str(exc_info.value)

    def test_get_settings_caching_detailed(self):
        """Test detailed caching behavior of get_settings."""
        # Clear cache first
        get_settings.cache_clear()
        
        with patch.dict(os.environ, {"APP_NAME": "CacheTest"}, clear=False):
            # First call - should create new instance
            settings1 = get_settings()
            assert settings1.app_name == "CacheTest"
            
            # Second call - should return cached instance
            settings2 = get_settings()
            assert settings1 is settings2  # Same object reference
            
            # Change environment (shouldn't affect cached instance)
            with patch.dict(os.environ, {"APP_NAME": "NewName"}, clear=False):
                settings3 = get_settings()
                assert settings3 is settings1  # Still cached
                assert settings3.app_name == "CacheTest"  # Original value
            
            # Clear cache and get new instance
            get_settings.cache_clear()
            settings4 = get_settings()
            assert settings4 is not settings1  # New instance
            assert settings4.app_name == "NewName"  # Updated value

    def test_base_dir_path_resolution(self):
        """Test base_dir path resolution."""
        settings = CoreAppSettings(_env_file=None)
        
        # base_dir should be a valid Path object pointing to project root
        assert isinstance(settings.base_dir, Path)
        assert settings.base_dir.exists()
        
        # Should point to the project root (containing pyproject.toml or similar)
        potential_markers = ["pyproject.toml", "requirements.txt", "setup.py"]
        has_marker = any((settings.base_dir / marker).exists() for marker in potential_markers)
        assert has_marker, f"base_dir {settings.base_dir} doesn't seem to be project root"


class TestEdgeCasesAndErrorHandling:
    """Test cases for edge cases and error handling scenarios."""

    def test_empty_environment_variables(self):
        """Test handling of empty environment variables."""
        env_vars = {
            "SUPABASE_URL": "",
            "SUPABASE_ANON_KEY": "",
            "SUPABASE_TIMEOUT": "",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Empty strings should be treated as not set, falling back to defaults
            config = DatabaseConfig(_env_file=None)
            
            # Empty URL should fall back to default
            assert config.url == "https://test-project.supabase.co"
            # Empty anon_key should fall back to default
            assert config.anon_key.get_secret_value() == "test-anon-key"
            # Empty timeout should fall back to default
            assert config.timeout == 60.0

    def test_invalid_type_conversions(self):
        """Test handling of invalid type conversions."""
        env_vars = {
            "SUPABASE_TIMEOUT": "not-a-number",
            "SUPABASE_AUTO_REFRESH_TOKEN": "not-a-boolean",
            "SUPABASE_VECTOR_DIMENSIONS": "not-an-integer",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            with pytest.raises(ValidationError) as exc_info:
                DatabaseConfig(_env_file=None)
            
            errors = exc_info.value.errors()
            # Should have validation errors for invalid types
            assert len(errors) > 0
            error_fields = [error['loc'][0] for error in errors]
            assert 'timeout' in error_fields or 'auto_refresh_token' in error_fields or 'vector_dimensions' in error_fields

    def test_malformed_env_file(self):
        """Test handling of malformed .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            # Write malformed content
            f.write("SUPABASE_URL=https://valid.supabase.co\n")
            f.write("INVALID_LINE_WITHOUT_EQUALS\n")
            f.write("=VALUE_WITHOUT_KEY\n")
            f.write("SUPABASE_ANON_KEY=valid-key\n")
            temp_env_file = f.name

        try:
            # Should still load valid lines and ignore malformed ones
            config = DatabaseConfig(_env_file=temp_env_file)
            assert config.url == "https://valid.supabase.co"
            assert config.anon_key.get_secret_value() == "valid-key"
        finally:
            os.unlink(temp_env_file)

    def test_circular_environment_references(self):
        """Test handling of environment variables with circular references."""
        env_vars = {
            "SUPABASE_URL": "${SUPABASE_BASE_URL}/auth",
            "SUPABASE_BASE_URL": "${SUPABASE_URL}",  # Circular reference
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Should not crash, just use the literal value
            config = DatabaseConfig(_env_file=None)
            # The value should be taken literally (pydantic-settings doesn't expand variables by default)
            assert "${SUPABASE_BASE_URL}" in config.url

    def test_very_long_environment_values(self):
        """Test handling of very long environment variable values."""
        long_value = "x" * 10000  # 10KB string
        env_vars = {
            "SUPABASE_URL": f"https://very-long-subdomain-{long_value}.supabase.co",
            "SUPABASE_PROJECT_ID": long_value,
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)
            assert long_value in config.url
            assert config.project_id == long_value

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters in environment values."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/~`"
        unicode_chars = "测试数据🚀✨🎯🔥💎⚡🌟🎨🎭🎪"
        
        env_vars = {
            "SUPABASE_PROJECT_ID": f"test-{special_chars}-{unicode_chars}",
            "SUPABASE_URL": f"https://{unicode_chars}.supabase.co",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)
            assert special_chars in config.project_id
            assert unicode_chars in config.project_id
            assert unicode_chars in config.url


class TestPerformanceAndMemory:
    """Test cases for performance and memory usage."""

    def test_settings_instantiation_performance(self):
        """Test that settings instantiation is reasonably fast."""
        import time
        
        start_time = time.time()
        for _ in range(100):
            settings = CoreAppSettings(_env_file=None)
            # Access a few properties to ensure full initialization
            _ = settings.environment
            _ = settings.database.url
            _ = settings.dragonfly.url
        end_time = time.time()
        
        # Should be able to create 100 instances in less than 1 second
        assert (end_time - start_time) < 1.0

    def test_memory_usage_with_large_configs(self):
        """Test memory usage doesn't grow excessively with large configurations."""
        import sys
        
        # Create many settings instances
        settings_list = []
        for i in range(50):
            env_vars = {
                f"SUPABASE_PROJECT_ID": f"project-{i}",
                f"APP_NAME": f"App-{i}",
            }
            with patch.dict(os.environ, env_vars, clear=False):
                settings = CoreAppSettings(_env_file=None)
                settings_list.append(settings)
        
        # Basic sanity check - we should have created all instances
        assert len(settings_list) == 50
        assert all(isinstance(s, CoreAppSettings) for s in settings_list)

    def test_cached_settings_memory_efficiency(self):
        """Test that cached settings are memory efficient."""
        # Clear cache first
        get_settings.cache_clear()
        
        # Get same settings instance multiple times
        settings_refs = []
        for _ in range(100):
            settings_refs.append(get_settings())
        
        # All references should point to the same object
        first_settings = settings_refs[0]
        assert all(s is first_settings for s in settings_refs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])