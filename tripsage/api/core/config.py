"""Unified API configuration settings.

This module provides unified configuration settings for the TripSage API layer,
extending CoreAppSettings with settings specific to the unified API including
JWT authentication, CORS, rate limiting, and BYOK functionality.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

from tripsage_core.config.base_app_settings import CoreAppSettings


class Settings(CoreAppSettings):
    """Unified API configuration settings.

    Extends CoreAppSettings with settings specific to the unified API,
    including JWT authentication, CORS origins, rate limiting, and BYOK settings.
    This serves as the single configuration source for the entire API layer.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRIPSAGE_API_",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # API Configuration
    api_prefix: str = Field(
        default="/api/v1", description="API prefix for all endpoints"
    )
    api_title: str = Field(
        default="TripSage API", description="API title for OpenAPI documentation"
    )
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(
        default="TripSage AI Travel Planning API",
        description="API description for OpenAPI documentation",
    )

    # JWT Authentication Settings
    access_token_expire_minutes: int = Field(
        default=60, description="JWT access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="JWT refresh token expiration in days"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")

    # CORS Configuration (supports both Next.js frontend and direct API access)
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",  # Next.js development
            "http://localhost:3001",  # Alternative dev port
            "https://tripsage.app",  # Production frontend
            "https://app.tripsage.ai",  # Alternative production domain
        ],
        description="CORS origins for API access",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests"
    )
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed HTTP methods for CORS",
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], description="Allowed headers for CORS"
    )

    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests per minute for general API"
    )
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # Higher limits for authenticated users
    rate_limit_authenticated_requests: int = Field(
        default=1000,
        description="Rate limit requests per minute for authenticated users",
    )

    # API-specific rate limits
    rate_limit_chat_requests: int = Field(
        default=50, description="Rate limit for chat endpoints per minute"
    )
    rate_limit_search_requests: int = Field(
        default=200, description="Rate limit for search endpoints per minute"
    )

    # BYOK (Bring Your Own Key) Configuration
    enable_byok: bool = Field(
        default=True, description="Enable Bring Your Own Key functionality"
    )
    byok_services: List[str] = Field(
        default=["openai", "google_maps", "duffel", "openweathermap", "firecrawl"],
        description="Services that support BYOK",
    )
    byok_encryption_enabled: bool = Field(
        default=True, description="Enable encryption for stored BYOK keys"
    )

    # API Key Management
    api_key_expiration_days: int = Field(
        default=365, description="API key expiration in days"
    )
    api_key_max_per_user: int = Field(
        default=10, description="Maximum API keys per user"
    )

    # WebSocket Configuration
    websocket_max_connections: int = Field(
        default=1000, description="Maximum concurrent WebSocket connections"
    )
    websocket_heartbeat_interval: int = Field(
        default=30, description="WebSocket heartbeat interval in seconds"
    )

    # Request/Response Configuration
    request_timeout: int = Field(
        default=30, description="Default request timeout in seconds"
    )
    max_request_size: int = Field(
        default=10485760, description="Maximum request size in bytes (10MB)"
    )

    # File upload limits
    max_file_size: int = Field(
        default=52428800, description="Maximum file upload size in bytes (50MB)"
    )
    allowed_file_types: List[str] = Field(
        default=[
            "image/jpeg",
            "image/png",
            "image/gif",
            "application/pdf",
            "text/plain",
            "text/csv",
        ],
        description="Allowed file MIME types for uploads",
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: List[str], info) -> List[str]:
        """Validate and process CORS origins.

        In production, wildcard origins should not be used for security.
        """
        # Access environment from the model data if available
        if info.data and "environment" in info.data:
            environment = info.data["environment"]
            if environment == "production" and "*" in v:
                raise ValueError("Wildcard CORS origin not allowed in production")
        return v

    @field_validator("byok_services")
    @classmethod
    def validate_byok_services(cls, v: List[str]) -> List[str]:
        """Validate BYOK service names."""
        allowed_services = {
            "openai",
            "google_maps",
            "duffel",
            "openweathermap",
            "firecrawl",
            "airbnb",
            "visual_crossing",
        }
        for service in v:
            if service not in allowed_services:
                raise ValueError(f"Unknown BYOK service: {service}")
        return v

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in allowed_algorithms:
            raise ValueError(f"Unsupported JWT algorithm: {v}")
        return v

    @property
    def secret_key(self) -> str:
        """Get the JWT secret key from CoreAppSettings."""
        return self.jwt_secret_key.get_secret_value()

    @property
    def algorithm(self) -> str:
        """Get the JWT algorithm."""
        return self.jwt_algorithm

    def get_cors_config(self) -> dict:
        """Get CORS configuration as a dictionary for FastAPI."""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": self.cors_allow_methods,
            "allow_headers": self.cors_allow_headers,
        }

    def is_byok_service_enabled(self, service: str) -> bool:
        """Check if a service supports BYOK."""
        return self.enable_byok and service in self.byok_services

    def get_rate_limit_for_endpoint(self, endpoint_type: str = "general") -> int:
        """Get rate limit for specific endpoint type."""
        if not self.rate_limit_enabled:
            return 0  # No limit

        limits = {
            "general": self.rate_limit_requests,
            "authenticated": self.rate_limit_authenticated_requests,
            "chat": self.rate_limit_chat_requests,
            "search": self.rate_limit_search_requests,
        }
        return limits.get(endpoint_type, self.rate_limit_requests)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache for performance optimization.

    Returns:
        Settings instance
    """
    return Settings()
