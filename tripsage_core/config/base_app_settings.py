"""
Core application settings for TripSage.

This module provides the centralized CoreAppSettings class containing all settings
common across the entire TripSage application (frontend API, agent API, agents, tools).
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Core Configuration Classes
class DragonflyConfig(BaseSettings):
    """DragonflyDB configuration settings (Redis-compatible with better performance)."""

    url: str = Field(
        default="redis://localhost:6379/0", description="DragonflyDB connection URL"
    )
    password: Optional[str] = Field(
        default=None, description="DragonflyDB password for authentication"
    )
    ttl_short: int = Field(default=300, description="TTL for short-lived data (5m)")
    ttl_medium: int = Field(default=3600, description="TTL for medium-lived data (1h)")
    ttl_long: int = Field(default=86400, description="TTL for long-lived data (24h)")

    # DragonflyDB specific optimizations
    max_memory_policy: str = Field(
        default="allkeys-lru", description="Memory eviction policy"
    )
    max_memory: str = Field(default="4gb", description="Maximum memory allocation")
    max_connections: int = Field(
        default=10000, description="Maximum concurrent connections"
    )
    thread_count: int = Field(default=4, description="Number of worker threads")
    port: int = Field(default=6379, description="DragonflyDB port")

    model_config = SettingsConfigDict(
        env_prefix="DRAGONFLY_",
        case_sensitive=False,
    )


class DatabaseConfig(BaseSettings):
    """Database configuration for Supabase PostgreSQL connections."""

    # Supabase configuration
    supabase_url: str = Field(default="https://test-project.supabase.co")
    supabase_anon_key: SecretStr = Field(default=SecretStr("test-anon-key"))
    supabase_service_role_key: Optional[SecretStr] = Field(default=None)
    supabase_jwt_secret: SecretStr = Field(
        default=SecretStr("test-jwt-secret"),
        description="Supabase JWT secret for local token validation"
    )
    supabase_project_id: Optional[str] = Field(
        default=None, description="Supabase project ID"
    )
    supabase_timeout: float = Field(default=60.0)
    supabase_auto_refresh_token: bool = Field(default=True)
    supabase_persist_session: bool = Field(default=True)

    # pgvector configuration
    pgvector_enabled: bool = Field(
        default=True, description="Enable pgvector extension support"
    )
    vector_dimensions: int = Field(
        default=1536, description="Default vector dimensions for embeddings"
    )


class Mem0Config(BaseSettings):
    """Mem0 memory system configuration."""

    # Core configuration
    vector_store_type: str = Field(
        default="pgvector", description="Vector store backend (pgvector)"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )
    embedding_dimensions: int = Field(
        default=1536, description="Embedding vector dimensions"
    )

    # Memory configuration
    memory_types: List[str] = Field(
        default=[
            "user_preferences",
            "trip_history",
            "search_patterns",
            "conversation_context",
        ],
        description="Types of memories to track",
    )
    max_memories_per_user: int = Field(
        default=1000, description="Maximum memories per user"
    )
    memory_ttl_days: int = Field(
        default=365, description="Memory retention period in days"
    )

    # Search configuration
    similarity_threshold: float = Field(
        default=0.7, description="Minimum similarity score for memory retrieval"
    )
    max_search_results: int = Field(
        default=10, description="Maximum memories to return in search"
    )

    # Performance settings
    batch_size: int = Field(default=100, description="Batch size for bulk operations")
    async_processing: bool = Field(
        default=True, description="Enable async memory processing"
    )


class LangGraphConfig(BaseSettings):
    """LangGraph agent orchestration configuration."""

    # Graph configuration
    checkpoint_storage: str = Field(
        default="postgresql", description="Checkpoint storage backend"
    )
    enable_streaming: bool = Field(
        default=True, description="Enable streaming responses"
    )
    max_graph_depth: int = Field(
        default=20, description="Maximum depth of agent graph execution"
    )

    # Agent coordination
    default_agent_timeout: int = Field(
        default=300, description="Default timeout for agent execution (seconds)"
    )
    enable_parallel_execution: bool = Field(
        default=True, description="Enable parallel agent execution"
    )
    max_parallel_agents: int = Field(
        default=5, description="Maximum number of parallel agent executions"
    )

    # Error handling
    max_retries: int = Field(
        default=3, description="Maximum retries for failed agent nodes"
    )
    retry_delay: float = Field(
        default=1.0, description="Delay between retries in seconds"
    )
    enable_error_recovery: bool = Field(
        default=True, description="Enable automatic error recovery"
    )

    # Performance monitoring
    enable_tracing: bool = Field(default=True, description="Enable execution tracing")
    trace_storage_days: int = Field(
        default=7, description="How long to keep execution traces"
    )


class Crawl4AIConfig(BaseSettings):
    """Crawl4AI web crawling configuration."""

    # API configuration
    api_url: str = Field(
        default="http://localhost:8000/api", description="Crawl4AI API URL"
    )
    api_key: Optional[SecretStr] = Field(default=None, description="Crawl4AI API key")

    # Crawling settings
    timeout: int = Field(default=30000, description="Request timeout in milliseconds")
    max_depth: int = Field(default=3, description="Maximum crawling depth")
    max_pages: int = Field(
        default=100, description="Maximum pages to crawl per session"
    )

    # Content extraction
    default_format: str = Field(
        default="markdown", description="Default content format"
    )
    extract_metadata: bool = Field(default=True, description="Extract page metadata")
    preserve_links: bool = Field(default=True, description="Preserve links in content")

    # Performance settings
    concurrent_requests: int = Field(
        default=5, description="Number of concurrent requests"
    )
    rate_limit_delay: float = Field(
        default=0.5, description="Delay between requests in seconds"
    )
    cache_enabled: bool = Field(default=True, description="Enable crawl result caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")


class AgentConfig(BaseSettings):
    """Configuration settings for TripSage agents."""

    model_name: str = Field(default="gpt-4o")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.7)
    agent_timeout: int = Field(default=120, description="Agent timeout in seconds")
    max_retries: int = Field(default=3)
    agent_memory_size: int = Field(default=10, description="Number of messages")

    default_flight_preferences: Dict[str, Any] = Field(
        default={
            "seat_class": "economy",
            "max_stops": 1,
            "preferred_airlines": [],
            "avoid_airlines": [],
            "time_window": "flexible",
        }
    )

    default_accommodation_preferences: Dict[str, Any] = Field(
        default={
            "property_type": "hotel",
            "min_rating": 3.5,
            "amenities": ["wifi", "breakfast"],
            "location_preference": "city_center",
        }
    )


class FeatureFlags(BaseSettings):
    """Feature flags for TripSage application."""

    # Agent features
    enable_agent_memory: bool = Field(default=True, description="Enable agent memory")
    enable_parallel_agents: bool = Field(
        default=True, description="Enable parallel agent execution"
    )
    enable_streaming_responses: bool = Field(
        default=True, description="Enable streaming responses"
    )

    # API features
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    enable_caching: bool = Field(default=True, description="Enable response caching")
    enable_debug_mode: bool = Field(default=False, description="Enable debug mode")

    # External integrations
    enable_crawl4ai: bool = Field(default=True, description="Enable Crawl4AI")
    enable_mem0: bool = Field(default=True, description="Enable Mem0 memory")
    enable_langgraph: bool = Field(default=True, description="Enable LangGraph")


class OpenTelemetryConfig(BaseSettings):
    """OpenTelemetry configuration for distributed tracing."""

    enabled: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    service_name: str = Field(
        default="tripsage", description="Service name for tracing"
    )
    service_version: str = Field(default="1.0.0", description="Service version")
    otlp_endpoint: Optional[str] = Field(
        default=None,
        description="OTLP exporter endpoint (e.g., http://localhost:4318/v1/traces)",
    )
    use_console_exporter: bool = Field(
        default=True, description="Use console exporter for development"
    )
    export_timeout_millis: int = Field(
        default=30000, description="Export timeout in milliseconds"
    )
    max_queue_size: int = Field(
        default=2048, description="Maximum queue size for span export"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Headers for OTLP exporter (e.g., authentication)"
    )


# Main Core Application Settings
class CoreAppSettings(BaseSettings):
    """
    Core application settings for TripSage.

    This class centralizes all configuration common across the entire application:
    frontend API, agent API, agents, tools, etc.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application metadata
    app_name: str = Field(default="TripSage", description="Application name")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: Literal["development", "testing", "staging", "production"] = Field(
        default="development", description="Runtime environment"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # Base paths
    base_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Base directory of the application",
    )

    # Security secrets
    # JWT configuration removed - will be replaced with Supabase Auth
    api_key_master_secret: SecretStr = Field(
        default=SecretStr("master-secret-for-byok-encryption"),
        description="Master secret for BYOK encryption",
    )

    # Core external service API keys (NOT user-provided/BYOK)
    # OpenAI
    openai_api_key: SecretStr = Field(
        default=SecretStr("test-openai-key"), description="OpenAI API key"
    )

    # Google services
    google_maps_api_key: Optional[SecretStr] = Field(
        default=None, description="Google Maps API key for direct SDK integration"
    )
    google_client_id: Optional[SecretStr] = Field(
        default=None, description="Google OAuth client ID for calendar integration"
    )
    google_client_secret: Optional[SecretStr] = Field(
        default=None, description="Google OAuth client secret for calendar integration"
    )

    # Weather services
    openweathermap_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenWeatherMap API key for weather data"
    )
    visual_crossing_api_key: Optional[SecretStr] = Field(
        default=None, description="Visual Crossing Weather API key"
    )

    # Flight services
    duffel_api_key: Optional[SecretStr] = Field(
        default=None, description="Duffel API key for flight search and booking"
    )

    # Core configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dragonfly: DragonflyConfig = Field(default_factory=DragonflyConfig)
    mem0: Mem0Config = Field(default_factory=Mem0Config)
    langgraph: LangGraphConfig = Field(default_factory=LangGraphConfig)
    crawl4ai: Crawl4AIConfig = Field(default_factory=Crawl4AIConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    opentelemetry: OpenTelemetryConfig = Field(default_factory=OpenTelemetryConfig)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        allowed = {"development", "testing", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}, got {v}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level setting."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}, got {v}")
        return v.upper()

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"

    def get_secret_value(self, key: str) -> Optional[str]:
        """
        Safely get a secret value by key name.

        Args:
            key: The attribute name of the secret

        Returns:
            The secret value as a string, or None if not set
        """
        secret = getattr(self, key, None)
        if secret and isinstance(secret, SecretStr):
            return secret.get_secret_value()
        return None

    # JWT convenience properties removed - will be replaced with Supabase Auth

    def validate_critical_settings(self) -> List[str]:
        """
        Validate critical settings required for the application to function.

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        # Check OpenAI API key
        if not self.openai_api_key.get_secret_value():
            errors.append("OpenAI API key is missing")

        # Check Supabase configuration
        if not self.database.supabase_url:
            errors.append("Supabase URL is missing")
        if not self.database.supabase_anon_key.get_secret_value():
            errors.append("Supabase anonymous key is missing")
        if not self.database.supabase_jwt_secret.get_secret_value():
            errors.append("Supabase JWT secret is missing")

        # Production-specific validations
        if self.is_production():
            if self.debug:
                errors.append("Debug mode should be disabled in production")

            # Check critical API keys for production
            if not self.get_secret_value("duffel_api_key"):
                errors.append("Duffel API key is missing for production")

            if not self.get_secret_value("google_maps_api_key"):
                errors.append("Google Maps API key is missing for production")

            if not self.get_secret_value("openweathermap_api_key"):
                errors.append("OpenWeatherMap API key is missing for production")

            # Check service URLs
            if self.dragonfly.url == "redis://localhost:6379/0":
                errors.append("DragonflyDB is using localhost in production")

            if self.crawl4ai.api_url == "http://localhost:8000/api":
                errors.append("Crawl4AI is using localhost in production")

            # Check security secrets
            if self.api_key_master_secret.get_secret_value() in [
                "master-secret-for-byok-encryption"
            ]:
                errors.append("API key master secret must be changed in production")

            # Check Supabase JWT secret
            if self.database.supabase_jwt_secret.get_secret_value() in [
                "test-jwt-secret", "fallback-secret-for-development-only"
            ]:
                errors.append("Supabase JWT secret must be changed in production")

        return errors


@lru_cache()
def get_settings() -> CoreAppSettings:
    """
    Get the core application settings instance.

    Returns:
        Cached CoreAppSettings instance
    """
    return CoreAppSettings()


# Export convenience property for lazy loading
@property
def settings() -> CoreAppSettings:
    """Get the core application settings instance."""
    return get_settings()

# For backward compatibility, create a module-level attribute
class _SettingsProxy:
    """Proxy object that lazily loads settings on first access."""
    _instance = None
    
    def __getattr__(self, name):
        if self._instance is None:
            self._instance = get_settings()
        return getattr(self._instance, name)
    
    def __repr__(self):
        return f"<SettingsProxy({get_settings()})>"

settings = _SettingsProxy()


def init_settings() -> CoreAppSettings:
    """
    Initialize and validate core application settings.

    This function should be called at application startup to ensure
    all required settings are available and valid.

    Returns:
        The validated CoreAppSettings instance.

    Raises:
        ValidationError: If settings are missing or invalid.
    """
    # Log settings initialization
    logging.info("Initializing core application settings")

    # Check environment
    env = settings.environment
    logging.info(f"Application environment: {env}")

    # Validate critical settings
    errors = settings.validate_critical_settings()
    if errors:
        error_message = "Critical settings validation failed:\n- " + "\n- ".join(errors)
        logging.error(error_message)
        raise ValueError(error_message)

    # Additional initialization for specific environments
    if env == "development":
        logging.debug("Development mode enabled")
    elif env == "testing":
        logging.debug("Test mode enabled")
    elif env == "production":
        logging.info("Production mode enabled")

    logging.info("Core settings initialization completed successfully")
    return settings
