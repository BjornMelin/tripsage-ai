"""
Standalone configuration testing for TripSage Core.

This module tests the configuration system without any pytest fixtures
or conftest.py interference. Run with: python -m pytest tests/unit/test_config_standalone.py
"""

import os
from unittest.mock import patch

from pydantic import SecretStr, ValidationError

from tripsage_core.config import Settings


def test_settings_creation_success():
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None)
        assert isinstance(settings, Settings)
        assert settings.environment == "development"


def test_all_fields_accessible():
    settings = Settings(_env_file=None)
    assert hasattr(settings, "environment")
    assert hasattr(settings, "debug")
    assert hasattr(settings, "log_level")
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "database_public_key")
    assert hasattr(settings, "postgres_url")
    assert hasattr(settings, "openai_api_key")
    assert hasattr(settings, "openai_model")
    assert hasattr(settings, "rate_limit_enabled")
    assert hasattr(settings, "rate_limit_requests_per_minute")
    assert hasattr(settings, "enable_websockets")
    assert hasattr(settings, "websocket_timeout")


def test_environment_validation():
    for env in ["development", "production", "test", "testing"]:
        settings = Settings(environment=env, _env_file=None)
        assert settings.environment == env
    try:
        Settings(environment="invalid", _env_file=None)
        raise AssertionError("Should have raised ValidationError")
    except ValidationError as e:
        error = e.errors()[0]
        assert error["type"] == "literal_error" and "development" in str(e)


def test_environment_variable_override():
    env_vars = {
        "ENVIRONMENT": "production",
        "DEBUG": "true",
        "LOG_LEVEL": "ERROR",
        "API_TITLE": "Test API",
        "DATABASE_URL": "https://test.supabase.co",
        "OPENAI_MODEL": "gpt-3.5-turbo",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings(_env_file=None)
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.log_level == "ERROR"
        assert settings.api_title == "Test API"
        assert settings.database_url == "https://test.supabase.co"
        assert settings.openai_model == "gpt-3.5-turbo"


def test_type_coercion():
    env_vars = {
        "DEBUG": "true",
        "REDIS_MAX_CONNECTIONS": "75",
        "DB_HEALTH_CHECK_INTERVAL": "45.5",
        "RATE_LIMIT_ENABLED": "false",
        "ENABLE_WEBSOCKETS": "1",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings(_env_file=None)
        assert settings.debug is True
        assert settings.redis_max_connections == 75
        assert settings.db_health_check_interval == 45.5
        assert settings.rate_limit_enabled is False
        assert settings.enable_websockets is True


def test_secret_field_types():
    settings = Settings(
        openai_api_key=SecretStr("secret-key"),
        database_public_key=SecretStr("public-key"),
        database_service_key=SecretStr("service-key"),
        database_jwt_secret=SecretStr("jwt-secret"),
        secret_key=SecretStr("app-secret"),
        _env_file=None,
    )
    assert isinstance(settings.openai_api_key, SecretStr)
    assert isinstance(settings.database_public_key, SecretStr)
    assert isinstance(settings.database_service_key, SecretStr)
    assert isinstance(settings.database_jwt_secret, SecretStr)
    assert isinstance(settings.secret_key, SecretStr)


def test_secret_value_access():
    settings = Settings(openai_api_key=SecretStr("test-openai-key"), _env_file=None)
    assert settings.openai_api_key.get_secret_value() == "test-openai-key"


def test_secret_masking():
    settings = Settings(
        openai_api_key=SecretStr("very-secret-key"),
        secret_key=SecretStr("app-secret"),
        _env_file=None,
    )
    settings_repr = repr(settings)
    assert "very-secret-key" not in settings_repr
    assert "app-secret" not in settings_repr


def test_environment_properties():
    dev_settings = Settings(environment="development", _env_file=None)
    assert dev_settings.is_development is True
    assert dev_settings.is_production is False
    assert dev_settings.is_testing is False
    prod_settings = Settings(environment="production", _env_file=None)
    assert prod_settings.is_development is False
    assert prod_settings.is_production is True
    assert prod_settings.is_testing is False
    test_settings = Settings(environment="test", _env_file=None)
    assert test_settings.is_development is False
    assert test_settings.is_production is False
    assert test_settings.is_testing is True


def test_effective_postgres_url_explicit():
    settings = Settings(
        postgres_url="postgresql://user:pass@localhost:5432/db", _env_file=None
    )
    assert settings.effective_postgres_url == "postgresql://user:pass@localhost:5432/db"


def test_effective_postgres_url_scheme_conversion():
    settings = Settings(
        postgres_url="postgres://user:pass@localhost:5432/db", _env_file=None
    )
    assert settings.effective_postgres_url == "postgresql://user:pass@localhost:5432/db"

