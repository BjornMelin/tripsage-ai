"""
Unified, modern configuration for TripSage application.

Following 2025 best practices with a single, flat configuration structure.
No backwards compatibility concerns - only optimal patterns.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Modern, unified application configuration.

    Single configuration class following 2025 best practices:
    - Flat structure (no nested configs)
    - Environment-based feature toggles
    - Clear validation and defaults
    - No backwards compatibility code
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Environment & Core
    environment: Literal["development", "production", "test", "testing"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API Configuration (flattened from separate APISettings)
    api_title: str = "TripSage API"
    api_version: str = "1.0.0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    cors_credentials: bool = True

    # Database (Supabase)
    database_url: str = Field(..., description="Supabase database URL")
    database_public_key: SecretStr = Field(..., description="Supabase public anon key")
    database_service_key: SecretStr = Field(
        ..., description="Supabase service role key"
    )
    database_jwt_secret: SecretStr = Field(
        ..., description="Supabase JWT secret for token validation"
    )

    # Application Security
    secret_key: SecretStr = Field(
        ..., description="Application secret key for encryption and signing"
    )

    # Redis/Cache (DragonflyDB)
    redis_url: str | None = None
    redis_password: str | None = None
    redis_max_connections: int = Field(
        default=50, description="Maximum Redis connections"
    )

    # AI Services
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    openai_model: str = "gpt-4o"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "production", "test", "testing"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
