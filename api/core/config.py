"""
API Configuration module.

This module imports and extends the main application settings
for API-specific configuration.
"""

from typing import List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from tripsage.config.app_settings import settings as app_settings


class APISettings(BaseSettings):
    """API-specific settings extending the main application settings."""

    # JWT authentication settings
    secret_key: SecretStr = Field(
        default=SecretStr("your-secret-key-here-change-in-production"),
        description="Secret key for signing JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="Algorithm for JWT encoding")
    access_token_expire_minutes: int = Field(
        default=30, description="Minutes until access token expires"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Days until refresh token expires"
    )

    # CORS settings
    cors_origins: List[str] = Field(
        default=["*"]
        if app_settings.debug
        else [
            "https://tripsage.ai",
            "https://app.tripsage.ai",
            "https://api.tripsage.ai",
        ],
        description="List of allowed origins for CORS",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials for CORS"
    )
    cors_allow_methods: List[str] = Field(
        default=["*"], description="Allowed HTTP methods for CORS"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], description="Allowed HTTP headers for CORS"
    )

    # API Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        default=60, description="Maximum requests per minute"
    )

    # BYOK (Bring Your Own Key) settings
    enable_byok: bool = Field(
        default=True, description="Enable Bring Your Own Key functionality"
    )
    byok_services: List[str] = Field(
        default=[
            "openai",
            "weather",
            "flights",
            "googleMaps",
            "accommodation",
            "webCrawl",
        ],
        description="Services that support Bring Your Own Key",
    )

    class Config:
        # Don't read from .env file since we get settings from app_settings
        extra = "allow"  # Allow extra fields from environment


# Create settings instance without reading from .env
settings = APISettings()

# Augment with main application settings
# This allows accessing both API and application settings through the same object
for key, value in app_settings.model_dump().items():
    if not hasattr(settings, key):
        setattr(settings, key, value)
