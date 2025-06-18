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
    database_url: str = Field(
        default="https://test.supabase.com", description="Supabase database URL"
    )
    database_public_key: SecretStr = Field(
        default="test-public-key", description="Supabase public anon key"
    )
    database_service_key: SecretStr = Field(
        default="test-service-key", description="Supabase service role key"
    )
    database_jwt_secret: SecretStr = Field(
        default="test-jwt-secret-for-testing-only",
        description="Supabase JWT secret for token validation",
    )

    # PostgreSQL Connection URL (optional)
    postgres_url: str | None = Field(
        default=None,
        description="PostgreSQL connection URL (overrides database_url if provided)",
    )

    # Read Replica Configuration
    database_region: str = Field(
        default="us-east-1", description="Primary database region"
    )
    enable_read_replicas: bool = Field(
        default=False, description="Enable read replica load balancing"
    )
    read_replica_strategy: Literal[
        "round_robin",
        "least_connections",
        "latency_based",
        "geographic",
        "query_type",
        "weighted_random",
    ] = Field(
        default="round_robin", description="Load balancing strategy for read replicas"
    )
    read_replica_health_check_interval: float = Field(
        default=30.0, description="Read replica health check interval in seconds"
    )
    read_replica_fallback_to_primary: bool = Field(
        default=True, description="Fallback to primary when replicas are unhealthy"
    )
    read_replica_max_retry_attempts: int = Field(
        default=3, description="Maximum retry attempts for replica connections"
    )

    # Application Security
    secret_key: SecretStr = Field(
        default="test-application-secret-key-for-testing-only",
        description="Application secret key for encryption and signing",
    )

    # Redis/Cache (DragonflyDB)
    redis_url: str | None = None
    redis_password: str | None = None
    redis_max_connections: int = Field(
        default=50, description="Maximum Redis connections"
    )

    # AI Services
    openai_api_key: SecretStr = Field(
        default="sk-test-1234567890", description="OpenAI API key"
    )
    openai_model: str = "gpt-4o"

    # Rate Limiting & Security
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Enhanced Security Configuration
    enable_security_monitoring: bool = Field(
        default=True, description="Enable comprehensive security event monitoring"
    )
    enable_timing_attack_protection: bool = Field(
        default=True, description="Enable timing attack protection for auth operations"
    )
    enable_audit_logging: bool = Field(
        default=True, description="Enable detailed audit logging for security events"
    )
    enable_threat_detection: bool = Field(
        default=True, description="Enable automated threat detection and response"
    )

    # Security Thresholds
    max_failed_auth_attempts: int = Field(
        default=5, description="Maximum failed authentication attempts before blocking"
    )
    auth_attempt_window: int = Field(
        default=3600,
        description="Time window for tracking failed auth attempts (seconds)",
    )
    suspicious_ip_threshold: int = Field(
        default=10, description="Rate limit violations before marking IP as suspicious"
    )

    # Security Headers Configuration
    enable_security_headers: bool = Field(
        default=True, description="Enable comprehensive security headers"
    )
    csp_policy: str = Field(
        default="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        description="Content Security Policy",
    )
    hsts_max_age: int = Field(
        default=31536000, description="HTTP Strict Transport Security max age"
    )

    # Feature Flags for Database Hardening
    enable_database_monitoring: bool = Field(
        default=True, description="Enable database connection monitoring"
    )
    enable_prometheus_metrics: bool = Field(
        default=True, description="Enable Prometheus metrics collection"
    )
    enable_security_monitoring: bool = Field(
        default=True, description="Enable security event monitoring"
    )
    enable_auto_recovery: bool = Field(
        default=True, description="Enable automatic database recovery"
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

    # Metrics Configuration
    metrics_server_port: int = Field(
        default=8000, description="Prometheus metrics server port"
    )
    enable_metrics_server: bool = Field(
        default=False, description="Enable standalone metrics server"
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
        return self.environment == "test"

    @property
    def read_replicas(self) -> dict[str, dict[str, any]]:
        """Parse read replica configurations from environment variables.

        Environment variables should follow the pattern:
        READ_REPLICA_<ID>_URL=https://...
        READ_REPLICA_<ID>_API_KEY=key
        READ_REPLICA_<ID>_REGION=us-west-1
        READ_REPLICA_<ID>_PRIORITY=1
        READ_REPLICA_<ID>_WEIGHT=1.0
        READ_REPLICA_<ID>_MAX_CONNECTIONS=100
        READ_REPLICA_<ID>_ENABLED=true

        Returns:
            Dictionary of replica configurations keyed by replica ID
        """
        import os

        replicas = {}

        # Find all READ_REPLICA_*_URL environment variables
        for key in os.environ:
            if key.startswith("READ_REPLICA_") and key.endswith("_URL"):
                # Extract replica ID from environment variable name
                # READ_REPLICA_WEST_URL -> WEST
                replica_id = key[13:-4].lower()  # Remove "READ_REPLICA_" and "_URL"

                url = os.environ[key]
                api_key_var = f"READ_REPLICA_{replica_id.upper()}_API_KEY"
                api_key = os.environ.get(api_key_var)

                if url and api_key:
                    replicas[replica_id] = {
                        "url": url,
                        "api_key": api_key,
                        "name": os.environ.get(
                            f"READ_REPLICA_{replica_id.upper()}_NAME",
                            f"Read Replica {replica_id}",
                        ),
                        "region": os.environ.get(
                            f"READ_REPLICA_{replica_id.upper()}_REGION", "us-east-1"
                        ),
                        "priority": int(
                            os.environ.get(
                                f"READ_REPLICA_{replica_id.upper()}_PRIORITY", "1"
                            )
                        ),
                        "weight": float(
                            os.environ.get(
                                f"READ_REPLICA_{replica_id.upper()}_WEIGHT", "1.0"
                            )
                        ),
                        "max_connections": int(
                            os.environ.get(
                                f"READ_REPLICA_{replica_id.upper()}_MAX_CONNECTIONS",
                                "100",
                            )
                        ),
                        "read_only": os.environ.get(
                            f"READ_REPLICA_{replica_id.upper()}_READ_ONLY", "true"
                        ).lower()
                        == "true",
                        "enabled": os.environ.get(
                            f"READ_REPLICA_{replica_id.upper()}_ENABLED", "true"
                        ).lower()
                        == "true",
                    }

        return replicas

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
            # In test environment, return a mock PostgreSQL URL
            if self.environment in ["test", "testing"]:
                url = "postgresql://test_user:test_pass@localhost:5432/test_db"
            else:
                # Convert Supabase URL to PostgreSQL URL
                import re

                match = re.match(r"https://([^.]+)\.supabase\.co", self.database_url)
                if match:
                    project_ref = match.group(1)
                    # Construct PostgreSQL URL from Supabase project reference
                    # Format: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
                    url = f"postgresql://postgres.{project_ref}:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres"
                else:
                    # Fallback: assume database_url is already a PostgreSQL URL
                    url = self.database_url

        # Ensure URL uses asyncpg driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
