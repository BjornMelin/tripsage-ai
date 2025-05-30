"""
API Configuration module.

This module extends the core application settings with frontend API-specific
configuration.
"""

from typing import List

from pydantic import Field, model_validator

from tripsage_core.config.base_app_settings import CoreAppSettings


class APISettings(CoreAppSettings):
    """Frontend API-specific settings extending the core application settings."""

    # JWT token expiration settings (frontend API specific)
    access_token_expire_minutes: int = Field(
        default=30, description="Minutes until access token expires"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Days until refresh token expires"
    )

    # CORS settings (frontend specific)
    cors_origins: List[str] = Field(
        default=[
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

    @model_validator(mode="after")
    def set_cors_origins_for_debug(self) -> "APISettings":
        """Set CORS origins to wildcard in debug mode."""
        if self.debug:
            self.cors_origins = ["*"]
        return self

    # API Rate limiting (frontend API specific)
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(
        default=60, description="Maximum requests per minute"
    )

    # BYOK (Bring Your Own Key) settings (frontend API specific)
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
        description="Services that support Bring Your Own Key in frontend API",
    )

    @property
    def secret_key(self) -> str:
        """Get JWT secret key from inherited core settings."""
        return self.jwt_secret_key.get_secret_value()

    @property
    def algorithm(self) -> str:
        """JWT algorithm for token encoding."""
        return "HS256"

    model_config = {
        "extra": "allow"  # Allow extra fields from environment
    }


# Create settings instance
settings = APISettings()
