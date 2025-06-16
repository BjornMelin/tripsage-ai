"""
Modern, consolidated configuration for TripSage application.

This module provides a clean, flat configuration structure following 2025 best
practices. All configuration is centralized here with environment-based feature
toggles.
"""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Main application configuration following 2025 best practices.

    Consolidates all configuration into a single, flat structure with
    environment-based feature toggles for configurable complexity.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Environment & Core
    environment: Literal["development", "production", "test", "testing"] = Field(
        default="development", description="Application environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database (Supabase)
    database_url: str = Field(
        default="https://test-project.supabase.co", description="Supabase database URL"
    )
    database_key: SecretStr = Field(
        default=SecretStr("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-service-role-key"),
        description="Supabase service role key",
    )
    database_public_key: SecretStr = Field(
        default=SecretStr("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-anon-key"),
        description="Supabase public anon key",
    )
    database_jwt_secret: SecretStr = Field(
        default=SecretStr("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-jwt-secret"),
        description="Supabase JWT secret",
    )

    # Redis/Cache (DragonflyDB)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis/DragonflyDB connection URL",
    )
    redis_password: Optional[str] = Field(
        default=None, description="Redis/DragonflyDB password"
    )
    redis_max_connections: int = Field(
        default=10000, description="Maximum concurrent connections"
    )
    cache_ttl_short: int = Field(
        default=300, description="TTL for short-lived data (5m)"
    )
    cache_ttl_medium: int = Field(
        default=3600, description="TTL for medium-lived data (1h)"
    )
    cache_ttl_long: int = Field(
        default=86400, description="TTL for long-lived data (24h)"
    )

    # AI Services
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="Default OpenAI model")

    # Feature Toggles (Configurable Complexity)
    enable_advanced_agents: bool = Field(
        default=False, description="Enable LangGraph agent orchestration"
    )
    enable_memory_system: bool = Field(
        default=True, description="Enable Mem0 AI memory system"
    )
    enable_real_time: bool = Field(
        default=True, description="Enable WebSocket real-time features"
    )
    enable_vector_search: bool = Field(
        default=True, description="Enable pgvector search capabilities"
    )
    enable_monitoring: bool = Field(
        default=False, description="Enable advanced monitoring and observability"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        if v not in ["development", "production", "test", "testing"]:
            raise ValueError(
                "Environment must be development, production, test, or testing"
            )
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
        return self.environment in ["test", "testing"]


class APISettings(BaseSettings):
    """API-specific configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="API_",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    title: str = Field(default="TripSage API", description="API title")
    version: str = Field(default="1.0.0", description="API version")
    prefix: str = Field(default="/api/v1", description="API prefix")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )
    cors_credentials: bool = Field(default=True, description="Allow credentials")

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100, description="Requests per minute per IP"
    )
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # Security
    allowed_hosts: List[str] = Field(default=["*"], description="Allowed host headers")


# Global settings instances
@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings instance."""
    return AppSettings()


@lru_cache
def get_api_settings() -> APISettings:
    """Get cached API settings instance."""
    return APISettings()


# Backward compatibility aliases
CoreAppSettings = AppSettings


def init_settings() -> AppSettings:
    """Initialize and validate application settings for compatibility."""
    return get_settings()


# Convenience exports
settings = get_settings()
api_settings = get_api_settings()

__all__ = [
    "AppSettings",
    "APISettings",
    "CoreAppSettings",  # Backward compatibility
    "get_settings",
    "get_api_settings",
    "init_settings",
    "settings",
    "api_settings",
]
