"""
Standalone configuration testing for TripSage Core.

This module tests the configuration system without any pytest fixtures
or conftest.py interference. Run with: python test_config_standalone.py
"""

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from pydantic import SecretStr, ValidationError

# Import config components
from tripsage_core.config import Settings, get_settings


def test_settings_creation_success():
    """Test Settings can be created successfully."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None)
        assert isinstance(settings, Settings)
        assert settings.environment == "development"
    print("✓ Settings creation success")


def test_all_fields_accessible():
    """Test all configuration fields are accessible."""
    settings = Settings(_env_file=None)
    
    # Core fields
    assert hasattr(settings, 'environment')
    assert hasattr(settings, 'debug')
    assert hasattr(settings, 'log_level')
    
    # Database fields
    assert hasattr(settings, 'database_url')
    assert hasattr(settings, 'database_public_key')
    assert hasattr(settings, 'postgres_url')
    
    # AI fields
    assert hasattr(settings, 'openai_api_key')
    assert hasattr(settings, 'openai_model')
    
    # Rate limiting
    assert hasattr(settings, 'rate_limit_enabled')
    assert hasattr(settings, 'rate_limit_requests_per_minute')
    
    # WebSocket fields
    assert hasattr(settings, 'enable_websockets')
    assert hasattr(settings, 'websocket_timeout')
    print("✓ All fields accessible")


def test_environment_validation():
    """Test environment field validation."""
    # Valid environments
    for env in ["development", "production", "test", "testing"]:
        settings = Settings(environment=env, _env_file=None)
        assert settings.environment == env
    
    # Invalid environment
    try:
        Settings(environment="invalid", _env_file=None)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        error = e.errors()[0]
        # Pydantic 2.x uses literal_error instead of custom validator
        assert error["type"] == "literal_error" and "development" in str(e)
    print("✓ Environment validation")


def test_environment_variable_override():
    """Test environment variables override defaults."""
    env_vars = {
        "ENVIRONMENT": "production",
        "DEBUG": "true",
        "LOG_LEVEL": "ERROR",
        "API_TITLE": "Test API",
        "DATABASE_URL": "https://test.supabase.co",
        "OPENAI_MODEL": "gpt-3.5-turbo"
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings(_env_file=None)
        
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.log_level == "ERROR"
        assert settings.api_title == "Test API"
        assert settings.database_url == "https://test.supabase.co"
        assert settings.openai_model == "gpt-3.5-turbo"
    print("✓ Environment variable override")


def test_type_coercion():
    """Test automatic type conversion from environment variables."""
    env_vars = {
        "DEBUG": "true",
        "REDIS_MAX_CONNECTIONS": "75",
        "DB_HEALTH_CHECK_INTERVAL": "45.5",
        "RATE_LIMIT_ENABLED": "false",
        "ENABLE_WEBSOCKETS": "1"
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings(_env_file=None)
        
        assert settings.debug is True
        assert settings.redis_max_connections == 75
        assert settings.db_health_check_interval == 45.5
        assert settings.rate_limit_enabled is False
        assert settings.enable_websockets is True
    print("✓ Type coercion")


def test_secret_field_types():
    """Test SecretStr field types."""
    settings = Settings(
        openai_api_key=SecretStr("secret-key"),
        database_public_key=SecretStr("public-key"),
        database_service_key=SecretStr("service-key"),
        database_jwt_secret=SecretStr("jwt-secret"),
        secret_key=SecretStr("app-secret"),
        _env_file=None
    )
    
    assert isinstance(settings.openai_api_key, SecretStr)
    assert isinstance(settings.database_public_key, SecretStr)
    assert isinstance(settings.database_service_key, SecretStr)
    assert isinstance(settings.database_jwt_secret, SecretStr)
    assert isinstance(settings.secret_key, SecretStr)
    print("✓ Secret field types")


def test_secret_value_access():
    """Test accessing secret values."""
    settings = Settings(
        openai_api_key=SecretStr("test-openai-key"),
        _env_file=None
    )
    
    assert settings.openai_api_key.get_secret_value() == "test-openai-key"
    print("✓ Secret value access")


def test_secret_masking():
    """Test that secrets are masked in representations."""
    settings = Settings(
        openai_api_key=SecretStr("very-secret-key"),
        secret_key=SecretStr("app-secret"),
        _env_file=None
    )
    
    settings_repr = repr(settings)
    
    # Secrets should not appear in string representation
    assert "very-secret-key" not in settings_repr
    assert "app-secret" not in settings_repr
    print("✓ Secret masking")


def test_environment_properties():
    """Test environment checking properties."""
    # Development
    dev_settings = Settings(environment="development", _env_file=None)
    assert dev_settings.is_development is True
    assert dev_settings.is_production is False
    assert dev_settings.is_testing is False
    
    # Production
    prod_settings = Settings(environment="production", _env_file=None)
    assert prod_settings.is_development is False
    assert prod_settings.is_production is True
    assert prod_settings.is_testing is False
    
    # Testing
    test_settings = Settings(environment="test", _env_file=None)
    assert test_settings.is_development is False
    assert test_settings.is_production is False
    assert test_settings.is_testing is True
    print("✓ Environment properties")


def test_effective_postgres_url_explicit():
    """Test effective_postgres_url with explicit postgres_url."""
    settings = Settings(
        postgres_url="postgresql://user:pass@localhost:5432/db",
        _env_file=None
    )
    
    assert settings.effective_postgres_url == "postgresql://user:pass@localhost:5432/db"
    print("✓ Effective postgres URL explicit")


def test_effective_postgres_url_scheme_conversion():
    """Test postgres:// to postgresql:// conversion."""
    settings = Settings(
        postgres_url="postgres://user:pass@localhost:5432/db",
        _env_file=None
    )
    
    assert settings.effective_postgres_url == "postgresql://user:pass@localhost:5432/db"
    print("✓ Effective postgres URL scheme conversion")


def test_effective_postgres_url_test_supabase():
    """Test handling of test Supabase URL."""
    settings = Settings(
        database_url="https://test.supabase.com",
        _env_file=None
    )
    
    url = settings.effective_postgres_url
    assert url == "postgresql://postgres:password@127.0.0.1:5432/test_database"
    print("✓ Effective postgres URL test supabase")


def test_env_file_basic_loading():
    """Test basic .env file loading."""
    env_content = """
ENVIRONMENT=test
DEBUG=true
API_TITLE=EnvFile API
DATABASE_URL=https://envfile.supabase.co
OPENAI_MODEL=gpt-3.5-turbo
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        f.flush()
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                settings = Settings(_env_file=f.name)
                
                assert settings.environment == "test"
                assert settings.debug is True
                assert settings.api_title == "EnvFile API"
                assert settings.database_url == "https://envfile.supabase.co"
                assert settings.openai_model == "gpt-3.5-turbo"
        finally:
            os.unlink(f.name)
    print("✓ Env file basic loading")


def test_validation_error_messages():
    """Test validation error messages are clear."""
    try:
        Settings(environment="invalid", _env_file=None)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        error = e.errors()[0]
        assert error['loc'] == ('environment',)
        # Pydantic 2.x uses literal_error 
        assert error['type'] == 'literal_error'
    print("✓ Validation error messages")


def test_core_defaults():
    """Test core configuration defaults."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None)
        
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.api_title == "TripSage API"
        assert settings.api_version == "1.0.0"
    print("✓ Core defaults")


def test_database_defaults():
    """Test database configuration defaults."""
    settings = Settings(_env_file=None)
    
    assert settings.database_url == "https://test.supabase.com"
    assert settings.postgres_url is None
    print("✓ Database defaults")


def test_rate_limiting_defaults():
    """Test rate limiting defaults."""
    settings = Settings(_env_file=None)
    
    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_requests_per_minute == 60
    assert settings.rate_limit_requests_per_hour == 1000
    assert settings.rate_limit_requests_per_day == 10000
    assert settings.rate_limit_burst_size == 10
    print("✓ Rate limiting defaults")


def test_websocket_defaults():
    """Test WebSocket configuration defaults."""
    settings = Settings(_env_file=None)
    
    assert settings.enable_websockets is True
    assert settings.websocket_timeout == 300
    assert settings.max_websocket_connections == 1000
    print("✓ WebSocket defaults")


def test_get_settings_function():
    """Test get_settings function exists and works."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    print("✓ get_settings function")


def test_settings_creation_performance():
    """Test Settings creation performance."""
    start_time = time.time()
    
    for _ in range(50):
        Settings(_env_file=None)
    
    end_time = time.time()
    creation_time = end_time - start_time
    
    # Should create 50 instances quickly
    assert creation_time < 2.0
    print(f"✓ Settings creation performance ({creation_time:.3f}s for 50 instances)")


def test_concurrent_access():
    """Test concurrent Settings creation."""
    def create_settings():
        return Settings(_env_file=None)
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(create_settings) for _ in range(10)]
        settings_list = [future.result() for future in futures]
    
    assert len(settings_list) == 10
    for settings in settings_list:
        assert isinstance(settings, Settings)
    print("✓ Concurrent access")


def test_websocket_uppercase_setters():
    """Test WebSocket uppercase property setters and getters."""
    settings = Settings(
        enable_websockets=True,
        websocket_timeout=600,
        max_websocket_connections=2000,
        _env_file=None
    )
    
    # Test getters
    assert settings.ENABLE_WEBSOCKETS is True
    assert settings.WEBSOCKET_TIMEOUT == 600
    assert settings.MAX_WEBSOCKET_CONNECTIONS == 2000
    
    # Test setters
    settings.ENABLE_WEBSOCKETS = False
    settings.WEBSOCKET_TIMEOUT = 300
    settings.MAX_WEBSOCKET_CONNECTIONS = 1500
    
    assert settings.enable_websockets is False
    assert settings.websocket_timeout == 300
    assert settings.max_websocket_connections == 1500
    print("✓ WebSocket uppercase setters and getters")


def test_postgres_url_conversion_scenarios():
    """Test additional PostgreSQL URL conversion scenarios."""
    # Test postgresql:// URL passthrough
    settings1 = Settings(
        database_url="postgresql://user:pass@host:5432/db",
        _env_file=None
    )
    assert settings1.effective_postgres_url == "postgresql://user:pass@host:5432/db"
    
    # Test real Supabase URL conversion
    settings2 = Settings(
        database_url="https://myproject123.supabase.co",
        _env_file=None
    )
    url = settings2.effective_postgres_url
    assert "postgresql://postgres.myproject123" in url
    assert "pooler.supabase.com" in url
    assert "6543" in url
    
    # Test unknown URL format fallback
    settings3 = Settings(
        database_url="unknown://format/url",
        _env_file=None
    )
    url = settings3.effective_postgres_url
    assert url == "postgresql://postgres:password@127.0.0.1:5432/test_database"
    print("✓ PostgreSQL URL conversion scenarios")


def test_comprehensive_configuration_sections():
    """Test all configuration sections are accessible."""
    settings = Settings(_env_file=None)
    
    # Core configuration
    assert hasattr(settings, 'environment')
    assert hasattr(settings, 'debug')
    assert hasattr(settings, 'log_level')
    
    # API configuration
    assert hasattr(settings, 'api_title')
    assert hasattr(settings, 'api_version')
    assert hasattr(settings, 'cors_origins')
    assert hasattr(settings, 'cors_credentials')
    
    # Database configuration
    assert hasattr(settings, 'database_url')
    assert hasattr(settings, 'database_public_key')
    assert hasattr(settings, 'database_service_key')
    assert hasattr(settings, 'database_jwt_secret')
    assert hasattr(settings, 'postgres_url')
    
    # Security configuration
    assert hasattr(settings, 'secret_key')
    
    # Redis configuration
    assert hasattr(settings, 'redis_url')
    assert hasattr(settings, 'redis_password')
    assert hasattr(settings, 'redis_max_connections')
    
    # AI configuration
    assert hasattr(settings, 'openai_api_key')
    assert hasattr(settings, 'openai_model')
    
    # Rate limiting configuration
    assert hasattr(settings, 'rate_limit_enabled')
    assert hasattr(settings, 'rate_limit_use_dragonfly')
    assert hasattr(settings, 'rate_limit_requests_per_minute')
    assert hasattr(settings, 'rate_limit_requests_per_hour')
    assert hasattr(settings, 'rate_limit_requests_per_day')
    assert hasattr(settings, 'rate_limit_burst_size')
    assert hasattr(settings, 'rate_limit_enable_sliding_window')
    assert hasattr(settings, 'rate_limit_enable_token_bucket')
    assert hasattr(settings, 'rate_limit_enable_burst_protection')
    assert hasattr(settings, 'rate_limit_enable_monitoring')
    
    # Feature flags
    assert hasattr(settings, 'enable_database_monitoring')
    assert hasattr(settings, 'enable_prometheus_metrics')
    assert hasattr(settings, 'enable_security_monitoring')
    assert hasattr(settings, 'enable_auto_recovery')
    
    # WebSocket configuration
    assert hasattr(settings, 'enable_websockets')
    assert hasattr(settings, 'websocket_timeout')
    assert hasattr(settings, 'max_websocket_connections')
    
    # Monitoring configuration
    assert hasattr(settings, 'db_health_check_interval')
    assert hasattr(settings, 'db_security_check_interval')
    assert hasattr(settings, 'db_max_recovery_attempts')
    assert hasattr(settings, 'db_recovery_delay')
    
    # Metrics configuration
    assert hasattr(settings, 'metrics_server_port')
    assert hasattr(settings, 'enable_metrics_server')
    print("✓ Comprehensive configuration sections")


def run_all_tests():
    """Run all configuration tests."""
    tests = [
        test_settings_creation_success,
        test_all_fields_accessible,
        test_environment_validation,
        test_environment_variable_override,
        test_type_coercion,
        test_secret_field_types,
        test_secret_value_access,
        test_secret_masking,
        test_environment_properties,
        test_effective_postgres_url_explicit,
        test_effective_postgres_url_scheme_conversion,
        test_effective_postgres_url_test_supabase,
        test_env_file_basic_loading,
        test_validation_error_messages,
        test_core_defaults,
        test_database_defaults,
        test_rate_limiting_defaults,
        test_websocket_defaults,
        test_get_settings_function,
        test_settings_creation_performance,
        test_concurrent_access,
        test_websocket_uppercase_setters,
        test_postgres_url_conversion_scenarios,
        test_comprehensive_configuration_sections,
    ]
    
    passed = 0
    failed = 0
    
    print("Running standalone configuration tests...\n")
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Configuration module working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the output above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)