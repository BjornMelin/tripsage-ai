"""Agent API configuration settings.

This module provides agent-specific configuration settings that extend
the CoreAppSettings from tripsage_core.config.base_app_settings.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

from tripsage_core.config.base_app_settings import CoreAppSettings


class Settings(CoreAppSettings):
    """Agent API configuration settings.

    Extends CoreAppSettings with settings specific to the agent API,
    including agent-specific rate limits, CORS origins, and API key expiration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRIPSAGE_API_",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Agent API specific settings
    api_prefix: str = Field(
        default="/api/agent", description="API prefix for agent endpoints"
    )

    # CORS settings for agent access
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "https://tripsage.app"],
        description="CORS origins for agent API access",
    )

    # Agent-specific JWT expiration settings
    token_expiration_minutes: int = Field(
        default=120, description="Agent JWT token expiration in minutes"
    )
    refresh_token_expiration_days: int = Field(
        default=30, description="Agent refresh token expiration in days"
    )

    # Agent-specific rate limiting
    rate_limit_requests: int = Field(
        default=1000, description="Rate limit requests per timeframe for agents"
    )
    rate_limit_timeframe: int = Field(
        default=60, description="Rate limit timeframe in seconds"
    )

    # Agent API key expiration
    api_key_expiration_days: int = Field(
        default=365, description="Agent API key expiration in days"
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: List[str], info) -> List[str]:
        """Validate and process CORS origins.

        In production, wildcard origins should not be used.
        """
        # Access environment from the model data if available
        if info.data and "environment" in info.data:
            environment = info.data["environment"]
            if environment == "production" and "*" in v:
                raise ValueError("Wildcard CORS origin not allowed in production")
        return v

    @property
    def secret_key(self) -> str:
        """Get the JWT secret key from CoreAppSettings."""
        return self.jwt_secret_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache for performance optimization.

    Returns:
        Settings instance
    """
    return Settings()
