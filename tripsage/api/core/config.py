"""API configuration settings using Pydantic V2.

This module provides a Pydantic Settings class for API configuration,
following Pydantic V2 patterns and best practices.
"""

import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API configuration settings.

    This class uses Pydantic V2 and includes settings for API configuration,
    including environment, database connections, authentication, and security.
    """

    # Application settings
    app_name: str = "TripSage API"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    api_prefix: str = Field(default="/api")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"])
    
    # Security settings
    secret_key: str = Field(default="supersecret")
    token_expiration_minutes: int = Field(default=60)
    refresh_token_expiration_days: int = Field(default=7)
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_timeframe: int = Field(default=60)  # seconds
    
    # Database settings
    # (Using MCP settings, but adding direct connection options for flexibility)
    db_url: str = Field(default="")
    redis_url: str = Field(default="")
    
    # API Keys
    api_key_expiration_days: int = Field(default=90)
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v, values):
        """Validate and process CORS origins.
        
        In production, wildcard origins should not be used.
        """
        if values.data.get("environment") == "production" and "*" in v:
            raise ValueError("Wildcard CORS origin not allowed in production")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "TRIPSAGE_API_",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Uses LRU cache for performance optimization.
    
    Returns:
        Settings instance
    """
    return Settings()