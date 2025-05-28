"""
Application settings module for TripSage.

This module provides the main application settings class using Pydantic
for validation and loading from environment variables.

Architecture Updates (V2):
- Replaced Redis with DragonflyDB for improved performance
- Removed Neo4j (deferred to V2) in favor of Mem0 for memory management
- Added LangGraph for agent orchestration
- Added Crawl4AI for web crawling (replacing WebCrawl MCP)
- Only Airbnb MCP remains as the sole MCP integration
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import (
    Field,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# MCP Configuration Classes
class MCPConfig(BaseSettings):
    """Base configuration for MCP servers."""

    endpoint: str = Field(default="http://localhost:3000")
    api_key: Optional[SecretStr] = None


class AirbnbMCPConfig(MCPConfig):
    """OpenBnB Airbnb MCP server configuration."""

    endpoint: str = Field(
        default="http://localhost:3000", description="OpenBnB MCP server endpoint"
    )
    api_key: Optional[SecretStr] = None  # OpenBnB Airbnb MCP doesn't use API keys
    ignore_robots_txt: bool = Field(
        default=False, description="Whether to ignore robots.txt restrictions"
    )
    server_type: str = Field(
        default="openbnb/mcp-server-airbnb", description="Server implementation type"
    )


class AccommodationsMCPConfig(BaseSettings):
    """Accommodations MCP server configuration (Airbnb only)."""

    airbnb: AirbnbMCPConfig = AirbnbMCPConfig()


# Database Configuration Classes
class WebCacheTTLConfig(BaseSettings):
    """TTL configuration for different content types in the web cache."""

    realtime: int = Field(default=100, description="TTL for real-time data (100s)")
    time_sensitive: int = Field(
        default=300, description="TTL for time-sensitive data (5m)"
    )
    daily: int = Field(default=3600, description="TTL for daily-changing data (1h)")
    semi_static: int = Field(default=28800, description="TTL for semi-static data (8h)")
    static: int = Field(default=86400, description="TTL for static data (24h)")


class DragonflyConfig(BaseSettings):
    """DragonflyDB configuration settings (Redis-compatible with better performance)."""

    url: str = Field(default="redis://localhost:6379/0", description="DragonflyDB connection URL")
    ttl_short: int = Field(default=300)  # 5 minutes
    ttl_medium: int = Field(default=3600)  # 1 hour
    ttl_long: int = Field(default=86400)  # 24 hours
    web_cache: WebCacheTTLConfig = WebCacheTTLConfig()
    
    # DragonflyDB specific optimizations
    max_memory_policy: str = Field(default="allkeys-lru", description="Memory eviction policy")
    max_connections: int = Field(default=10000, description="Maximum concurrent connections")
    thread_count: int = Field(default=4, description="Number of worker threads")


class DatabaseConfig(BaseSettings):
    """Database configuration for Supabase PostgreSQL connections."""

    # Supabase configuration
    supabase_url: str = Field(default="https://test-project.supabase.co")
    supabase_anon_key: SecretStr = Field(default=SecretStr("test-anon-key"))
    supabase_service_role_key: Optional[SecretStr] = Field(default=None)
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
    vector_store_type: str = Field(default="pgvector", description="Vector store backend (pgvector)")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    embedding_dimensions: int = Field(default=1536, description="Embedding vector dimensions")
    
    # Memory configuration
    memory_types: List[str] = Field(
        default=["user_preferences", "trip_history", "search_patterns", "conversation_context"],
        description="Types of memories to track"
    )
    max_memories_per_user: int = Field(default=1000, description="Maximum memories per user")
    memory_ttl_days: int = Field(default=365, description="Memory retention period in days")
    
    # Search configuration
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity score for memory retrieval")
    max_search_results: int = Field(default=10, description="Maximum memories to return in search")
    
    # Performance settings
    batch_size: int = Field(default=100, description="Batch size for bulk operations")
    async_processing: bool = Field(default=True, description="Enable async memory processing")


class LangGraphConfig(BaseSettings):
    """LangGraph agent orchestration configuration."""

    # Graph configuration
    checkpoint_storage: str = Field(default="postgresql", description="Checkpoint storage backend")
    enable_streaming: bool = Field(default=True, description="Enable streaming responses")
    max_graph_depth: int = Field(default=20, description="Maximum depth of agent graph execution")
    
    # Agent coordination
    default_agent_timeout: int = Field(default=300, description="Default timeout for agent execution (seconds)")
    enable_parallel_execution: bool = Field(default=True, description="Enable parallel agent execution")
    max_parallel_agents: int = Field(default=5, description="Maximum number of parallel agent executions")
    
    # Error handling
    max_retries: int = Field(default=3, description="Maximum retries for failed agent nodes")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    enable_error_recovery: bool = Field(default=True, description="Enable automatic error recovery")
    
    # Performance monitoring
    enable_tracing: bool = Field(default=True, description="Enable execution tracing")
    trace_storage_days: int = Field(default=7, description="How long to keep execution traces")


class Crawl4AIConfig(BaseSettings):
    """Crawl4AI web crawling configuration (replacing WebCrawl MCP)."""

    # API configuration
    api_url: str = Field(default="http://localhost:8000/api", description="Crawl4AI API URL")
    api_key: Optional[SecretStr] = Field(default=None, description="Crawl4AI API key")
    
    # Crawling settings
    timeout: int = Field(default=30000, description="Request timeout in milliseconds")
    max_depth: int = Field(default=3, description="Maximum crawling depth")
    max_pages: int = Field(default=100, description="Maximum pages to crawl per session")
    
    # Content extraction
    default_format: str = Field(default="markdown", description="Default content format")
    extract_metadata: bool = Field(default=True, description="Extract page metadata")
    preserve_links: bool = Field(default=True, description="Preserve links in content")
    
    # Performance settings
    concurrent_requests: int = Field(default=5, description="Number of concurrent requests")
    rate_limit_delay: float = Field(default=0.5, description="Delay between requests in seconds")
    cache_enabled: bool = Field(default=True, description="Enable crawl result caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")


# Agent Configuration Classes
class AgentConfig(BaseSettings):
    """Configuration settings for TripSage agents."""

    model_name: str = Field(default="gpt-4o")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.7)
    agent_timeout: int = Field(default=120)  # seconds
    max_retries: int = Field(default=3)
    agent_memory_size: int = Field(default=10)  # number of messages

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


# Main Application Settings
class AppSettings(BaseSettings):
    """
    Main application settings for TripSage.

    This class centralizes all configuration across the application.
    Settings are loaded from environment variables or a .env file.

    Architecture (V2):
    - DragonflyDB replaces Redis for caching
    - Mem0 replaces Neo4j for memory management
    - LangGraph handles agent orchestration
    - Crawl4AI handles web crawling (replacing WebCrawl MCP)
    - Only Airbnb MCP remains as the sole MCP integration
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application settings
    app_name: str = "TripSage"
    debug: bool = Field(False, description="Enable debug mode")
    environment: str = Field(
        "development",
        description="Environment (development, testing, staging, production)",
    )
    log_level: str = Field("INFO", description="Logging level")
    port: int = Field(default=8000, description="API port")
    api_host: str = Field("0.0.0.0", description="API host")

    # Base paths
    base_dir: str = Field(
        str(Path(__file__).parent.parent.parent.absolute()),
        description="Base directory of the application",
    )

    # OpenAI settings
    openai_api_key: SecretStr = Field(
        default=SecretStr("test-openai-key"), description="OpenAI API key"
    )

    # Duffel Flights API
    duffel_api_key: Optional[SecretStr] = Field(
        default=None, description="Duffel API key for direct HTTP integration"
    )
    duffel_base_url: str = Field(
        default="https://api.duffel.com", description="Duffel API base URL"
    )
    duffel_timeout: float = Field(
        default=30.0, description="Duffel API request timeout in seconds"
    )
    duffel_max_retries: int = Field(
        default=3, description="Maximum retry attempts for Duffel API requests"
    )
    duffel_rate_limit_window: float = Field(
        default=60.0, description="Rate limit window in seconds for Duffel API"
    )
    duffel_max_requests_per_minute: int = Field(
        default=100, description="Maximum requests per minute for Duffel API"
    )

    # Google Maps Direct API integration
    google_maps_api_key: Optional[SecretStr] = Field(
        default=None, description="Google Maps API key for direct SDK integration"
    )
    google_maps_timeout: float = Field(
        default=30.0, description="Google Maps API request timeout in seconds"
    )
    google_maps_retry_timeout: int = Field(
        default=60, description="Google Maps API retry timeout in seconds"
    )
    google_maps_queries_per_second: int = Field(
        default=10, description="Google Maps API queries per second limit"
    )

    # Weather API Direct integration
    openweathermap_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenWeatherMap API key for direct integration"
    )
    visual_crossing_api_key: Optional[SecretStr] = Field(
        default=None, description="Visual Crossing Weather API key"
    )


    # Google Calendar Direct integration
    google_client_id: Optional[SecretStr] = Field(
        default=None, description="Google OAuth client ID"
    )
    google_client_secret: Optional[SecretStr] = Field(
        default=None, description="Google OAuth client secret"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:3000/callback",
        description="Google OAuth redirect URI",
    )

    # Storage & Infrastructure
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dragonfly: DragonflyConfig = Field(default_factory=DragonflyConfig)
    mem0: Mem0Config = Field(default_factory=Mem0Config)
    
    # Agent Orchestration & Tools
    langgraph: LangGraphConfig = Field(default_factory=LangGraphConfig)
    crawl4ai: Crawl4AIConfig = Field(default_factory=Crawl4AIConfig)

    # Cache settings
    use_cache: bool = Field(True, description="Enable caching")

    # Remaining MCP Server (Airbnb only)
    accommodations_mcp: AccommodationsMCPConfig = Field(
        default_factory=AccommodationsMCPConfig
    )

    # Agent configuration
    agent: AgentConfig = Field(default_factory=AgentConfig)

    # OpenTelemetry configuration
    opentelemetry: OpenTelemetryConfig = Field(default_factory=OpenTelemetryConfig)

    @field_validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        allowed_environments = {"development", "testing", "staging", "production"}
        if v not in allowed_environments:
            raise ValueError(
                f"Environment must be one of {allowed_environments}, got {v}"
            )
        return v

    def get_airbnb_mcp_url(self) -> str:
        """Get the Airbnb MCP endpoint URL.

        Returns:
            The Airbnb MCP endpoint URL.
        """
        return self.accommodations_mcp.airbnb.endpoint

    def get_airbnb_mcp_api_key(self) -> Optional[str]:
        """Get the Airbnb MCP API key.

        Returns:
            The API key or None if not available.
        """
        api_key = self.accommodations_mcp.airbnb.api_key
        return api_key.get_secret_value() if api_key else None


@lru_cache()
def get_settings() -> AppSettings:
    """Get the application settings.

    Returns:
        Application settings instance
    """
    return AppSettings()


# Export settings for convenience
settings = get_settings()


def init_settings() -> AppSettings:
    """
    Initialize and validate application settings.

    This function should be called at application startup to ensure
    all required settings are available and valid.

    Returns:
        The validated AppSettings instance.

    Raises:
        ValidationError: If settings are missing or invalid.
    """
    # Log settings initialization
    logging.info("Initializing application settings")

    # Check environment
    env = settings.environment
    logging.info(f"Application environment: {env}")

    # Validate critical settings
    _validate_critical_settings(settings)

    # Additional initialization for specific environments
    if env == "development":
        logging.debug("Development mode enabled")
    elif env == "testing":
        logging.debug("Test mode enabled")
    elif env == "production":
        logging.info("Production mode enabled")
        _validate_production_settings(settings)

    logging.info("Settings initialization completed successfully")
    return settings


def _validate_critical_settings(settings: AppSettings) -> None:
    """
    Validate critical settings required for the application to function.

    Args:
        settings: The AppSettings instance to validate.

    Raises:
        ValueError: If any critical setting is missing or invalid.
    """
    critical_errors: List[str] = []

    # Check OpenAI API key
    if not settings.openai_api_key.get_secret_value():
        critical_errors.append("OpenAI API key is missing")

    # Check database configuration (Supabase only)
    if not settings.database.supabase_url:
        critical_errors.append("Supabase URL is missing")
    if not settings.database.supabase_anon_key.get_secret_value():
        critical_errors.append("Supabase anonymous key is missing")

    # Raise an error with all validation issues if any were found
    if critical_errors:
        error_message = "Critical settings validation failed:\n- " + "\n- ".join(
            critical_errors
        )
        logging.error(error_message)
        raise ValueError(error_message)


def _validate_production_settings(settings: AppSettings) -> None:
    """
    Validate additional settings required for production environments.

    Args:
        settings: The AppSettings instance to validate.

    Raises:
        ValueError: If any production-required setting is missing or invalid.
    """
    production_errors: List[str] = []

    # Debug mode should be disabled in production
    if settings.debug:
        production_errors.append("Debug mode should be disabled in production")

    # Validate direct API keys for production
    if not settings.duffel_api_key or not settings.duffel_api_key.get_secret_value():
        production_errors.append("Duffel API key is missing for flights integration")

    if (
        not settings.google_maps_api_key
        or not settings.google_maps_api_key.get_secret_value()
    ):
        production_errors.append("Google Maps API key is missing")

    if (
        not settings.openweathermap_api_key
        or not settings.openweathermap_api_key.get_secret_value()
    ):
        production_errors.append("OpenWeatherMap API key is missing")

    # Validate new architecture components
    if settings.dragonfly.url == "redis://localhost:6379/0":
        production_errors.append(
            "DragonflyDB is using localhost in production. "
            "Should be set to deployed DragonflyDB URL."
        )
    
    if settings.crawl4ai.api_url == "http://localhost:8000/api":
        production_errors.append(
            "Crawl4AI is using localhost in production. "
            "Should be set to deployed Crawl4AI API URL."
        )
    
    if not settings.crawl4ai.api_key or not settings.crawl4ai.api_key.get_secret_value():
        production_errors.append("Crawl4AI API key is missing for production")

    if (
        not settings.google_client_id
        or not settings.google_client_id.get_secret_value()
    ):
        production_errors.append("Google Client ID is missing for calendar integration")

    if (
        not settings.google_client_secret
        or not settings.google_client_secret.get_secret_value()
    ):
        production_errors.append(
            "Google Client Secret is missing for calendar integration"
        )

    # Validate Airbnb MCP configuration
    if settings.accommodations_mcp.airbnb.endpoint == "http://localhost:3000":
        production_errors.append(
            "Airbnb MCP endpoint is using localhost in production. "
            "Should be set to deployed OpenBnB MCP server URL."
        )

    # Additional production-specific validations
    if production_errors:
        warning_message = "Production settings validation warnings:\n- " + "\n- ".join(
            production_errors
        )
        logging.warning(warning_message)


def get_settings_dict() -> Dict[str, Any]:
    """
    Get a dictionary representation of the application settings.

    This function returns a sanitized dictionary with all settings,
    masking sensitive values like API keys and passwords.

    Returns:
        A dictionary representation of the settings.
    """
    settings_dict = settings.model_dump()

    # Sanitize sensitive fields
    _sanitize_sensitive_data(settings_dict)

    return settings_dict


def _sanitize_sensitive_data(data: Dict[str, Any], path: str = "") -> None:
    """
    Recursively sanitize sensitive data in a dictionary.

    Args:
        data: The dictionary to sanitize.
        path: The current path in the dictionary (for nested dicts).
    """
    sensitive_keywords = {"password", "api_key", "secret", "key", "token"}

    for key, value in list(data.items()):
        current_path = f"{path}.{key}" if path else key

        # Check if this is a sensitive field
        is_sensitive = any(keyword in key.lower() for keyword in sensitive_keywords)

        if isinstance(value, dict):
            _sanitize_sensitive_data(value, current_path)
        elif is_sensitive and value:
            data[key] = "********" if value else None
