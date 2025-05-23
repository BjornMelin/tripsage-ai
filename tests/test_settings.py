"""Test settings configuration for isolated testing environment."""

import os
from typing import Dict
from unittest.mock import patch

from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Test-specific settings that override production settings."""

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=False,  # Don't validate defaults to avoid errors
        extra="ignore",  # Ignore extra environment variables
    )

    # Database Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "test_user"
    neo4j_password: str = "test_password"
    neo4j_database: str = "test_db"

    # Supabase Configuration
    supabase_url: str = "https://test-project.supabase.co"
    supabase_key: str = "test_key"
    supabase_jwt_secret: str = "test_jwt_secret"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/15"

    # API Keys
    openai_api_key: str = "test_openai_key"
    anthropic_api_key: str = "test_anthropic_key"

    # Application Settings
    environment: str = "test"
    debug: bool = True
    secret_key: str = "test_secret_key_not_for_production"

    # MCP Settings
    mcp_timeout: int = 30


def get_test_env_vars() -> Dict[str, str]:
    """Get test environment variables as a dictionary."""
    test_settings = TestSettings()
    return {
        "NEO4J_URI": test_settings.neo4j_uri,
        "NEO4J_USER": test_settings.neo4j_user,
        "NEO4J_PASSWORD": test_settings.neo4j_password,
        "NEO4J_DATABASE": test_settings.neo4j_database,
        "SUPABASE_URL": test_settings.supabase_url,
        "SUPABASE_KEY": test_settings.supabase_key,
        "SUPABASE_JWT_SECRET": test_settings.supabase_jwt_secret,
        "REDIS_URL": test_settings.redis_url,
        "OPENAI_API_KEY": test_settings.openai_api_key,
        "ANTHROPIC_API_KEY": test_settings.anthropic_api_key,
        "ENVIRONMENT": test_settings.environment,
        "DEBUG": str(test_settings.debug),
        "SECRET_KEY": test_settings.secret_key,
        "MCP_TIMEOUT": str(test_settings.mcp_timeout),
        # Override system USER variable that was causing issues
        "USER": "test_user",
    }


def mock_settings_patch():
    """Create a patch for environment variables with test values."""
    return patch.dict(os.environ, get_test_env_vars(), clear=False)
