"""Unified, modern configuration for TripSage application."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Crawl4AIMCPSettings(BaseSettings):
    """Crawl4AI MCP server configuration."""

    api_key: SecretStr | None = Field(
        default=None, description="Crawl4AI MCP API key (Bearer token authentication)"
    )
    endpoint: str = Field(
        default="http://localhost:11235", description="Crawl4AI MCP server endpoint URL"
    )
    timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Request timeout in seconds for Crawl4AI operations",
    )


class Settings(BaseSettings):
    """Modern, unified application configuration."""

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
    database_url: str = Field(
        default="https://test.supabase.com", description="Supabase database URL"
    )
    database_public_key: SecretStr = Field(
        default=SecretStr("test-public-key"), description="Supabase public anon key"
    )
    database_service_key: SecretStr = Field(
        default=SecretStr("test-service-key"), description="Supabase service role key"
    )
    database_jwt_secret: SecretStr = Field(
        default=SecretStr("test-jwt-secret-for-testing-only"),
        description="Supabase JWT secret for token validation",
    )

    # PostgreSQL Connection URL (optional)
    postgres_url: str | None = Field(
        default=None,
        description="PostgreSQL connection URL (overrides database_url if provided)",
    )

    # Application Security
    secret_key: SecretStr = Field(
        default=SecretStr("test-application-secret-key-for-testing-only"),
        description="Application secret key for encryption and signing",
    )

    # Redis/Cache (DragonflyDB)
    redis_url: str | None = None
    redis_password: str | None = None
    redis_max_connections: int = Field(
        default=50, description="Maximum Redis connections"
    )

    # Upstash Redis (HTTP) configuration (preferred in Vercel deployments)
    upstash_redis_rest_url: str | None = Field(
        default=None, description="Upstash Redis REST URL (UPSTASH_REDIS_REST_URL)"
    )
    upstash_redis_rest_token: SecretStr | None = Field(
        default=None,
        description="Upstash Redis REST token (UPSTASH_REDIS_REST_TOKEN)",
    )

    # AI Services
    openai_api_key: SecretStr = Field(
        default=SecretStr("sk-test-1234567890"), description="OpenAI API key"
    )
    openai_model: str = "gpt-4o"
    model_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for orchestrator LLMs",
    )

    # Crawl4AI MCP Configuration
    crawl4ai_mcp: Crawl4AIMCPSettings = Field(
        default_factory=Crawl4AIMCPSettings,
        description="Crawl4AI MCP server configuration",
    )

    # Rate limiting configuration
    rate_limit_enabled: bool = Field(
        default=True, description="Enable rate limiting middleware"
    )
    rate_limit_use_dragonfly: bool = Field(
        default=True, description="Use DragonflyDB for distributed rate limiting"
    )

    # Default rate limits (can be overridden per API key/user)
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Default requests per minute"
    )
    rate_limit_requests_per_hour: int = Field(
        default=1000, description="Default requests per hour"
    )
    rate_limit_requests_per_day: int = Field(
        default=10000, description="Default requests per day"
    )
    rate_limit_burst_size: int = Field(
        default=10, description="Default burst size for token bucket"
    )

    # Algorithm configuration
    rate_limit_enable_sliding_window: bool = Field(
        default=True, description="Enable sliding window rate limiting"
    )
    rate_limit_enable_token_bucket: bool = Field(
        default=True, description="Enable token bucket rate limiting"
    )
    rate_limit_enable_burst_protection: bool = Field(
        default=True, description="Enable burst protection"
    )

    # Integration with monitoring
    rate_limit_enable_monitoring: bool = Field(
        default=True, description="Enable rate limit monitoring and analytics"
    )

    # Feature Flags for Database Hardening
    enable_database_monitoring: bool = Field(
        default=True, description="Enable database connection monitoring"
    )
    enable_security_monitoring: bool = Field(
        default=True, description="Enable security event monitoring"
    )
    enable_auto_recovery: bool = Field(
        default=True, description="Enable automatic database recovery"
    )

    # WebSocket Configuration
    enable_websockets: bool = Field(
        default=True, description="Enable WebSocket functionality"
    )
    websocket_timeout: int = Field(
        default=300, description="WebSocket connection timeout in seconds"
    )
    max_websocket_connections: int = Field(
        default=1000, description="Maximum concurrent WebSocket connections"
    )

    # Monitoring Configuration
    db_health_check_interval: float = Field(
        default=30.0, description="Database health check interval in seconds"
    )
    db_security_check_interval: float = Field(
        default=60.0, description="Database security check interval in seconds"
    )
    db_max_recovery_attempts: int = Field(
        default=3, description="Maximum database recovery attempts"
    )
    db_recovery_delay: float = Field(
        default=5.0, description="Delay between recovery attempts in seconds"
    )

    # Metrics Configuration (OTEL-only)

    # OpenTelemetry Instrumentation Flags
    enable_fastapi_instrumentation: bool = Field(
        default=False, description="Enable FastAPI OTEL auto-instrumentation"
    )
    enable_asgi_instrumentation: bool = Field(
        default=False, description="Enable ASGI OTEL auto-instrumentation"
    )
    enable_httpx_instrumentation: bool = Field(
        default=False, description="Enable httpx OTEL auto-instrumentation"
    )
    enable_redis_instrumentation: bool = Field(
        default=False, description="Enable Redis OTEL auto-instrumentation"
    )

    # Google Maps Platform configuration
    google_maps_api_key: SecretStr | None = Field(
        default=None, description="Google Maps Platform API key"
    )
    google_maps_timeout: float = Field(
        default=10.0,
        ge=1.0,
        le=120.0,
        description="Combined connect+read timeout (seconds) for Google Maps requests",
    )
    google_maps_retry_timeout: int = Field(
        default=60,
        ge=1,
        le=600,
        description="Total retry timeout (s) across retriable Maps requests",
    )
    google_maps_queries_per_second: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Client-side QPS throttle for Google Maps requests",
    )

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
        return self.environment in ("test", "testing")

    @property
    def ENABLE_WEBSOCKETS(self) -> bool:
        """Uppercase alias for enable_websockets (for test compatibility)."""
        return self.enable_websockets

    @ENABLE_WEBSOCKETS.setter
    def ENABLE_WEBSOCKETS(self, value: bool):
        """Setter for uppercase alias."""
        self.enable_websockets = value

    @property
    def WEBSOCKET_TIMEOUT(self) -> int:
        """Uppercase alias for websocket_timeout (for test compatibility)."""
        return self.websocket_timeout

    @WEBSOCKET_TIMEOUT.setter
    def WEBSOCKET_TIMEOUT(self, value: int):
        """Setter for uppercase alias."""
        self.websocket_timeout = value

    @property
    def MAX_WEBSOCKET_CONNECTIONS(self) -> int:
        """Uppercase alias for max_websocket_connections (for test compatibility)."""
        return self.max_websocket_connections

    @MAX_WEBSOCKET_CONNECTIONS.setter
    def MAX_WEBSOCKET_CONNECTIONS(self, value: int):
        """Setter for uppercase alias."""
        self.max_websocket_connections = value

    @property
    def effective_postgres_url(self) -> str:
        """Get the effective PostgreSQL URL, converting from Supabase URL if needed.

        Returns:
            PostgreSQL connection URL in asyncpg format
        """
        # Use postgres_url if explicitly provided
        if self.postgres_url:
            url = self.postgres_url
        else:
            # Convert Supabase URL to PostgreSQL URL
            import re

            # Check test URL first to avoid regex matching issues
            db_url: str = str(self.database_url)
            if db_url.startswith("https://test.supabase.com"):
                # Special handling for test environment
                url = "postgresql://postgres:password@127.0.0.1:5432/test_database"
            elif db_url.startswith(("postgresql://", "postgres://")):
                # URL is already a PostgreSQL URL
                url = db_url
            else:
                # Try to match real Supabase URLs
                match = re.match(r"https://([^.]+)\.supabase\.co$", db_url)
                if match:
                    project_ref = match.group(1)
                    # Construct PostgreSQL URL from Supabase project reference
                    # Format: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
                    url = f"postgresql://postgres.{project_ref}:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres"
                else:
                    # Fallback for test/development environments
                    url = "postgresql://postgres:password@127.0.0.1:5432/test_database"

        # For testing, don't add asyncpg driver suffix as it may cause parsing issues
        # In production, the actual database service handles driver selection
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
