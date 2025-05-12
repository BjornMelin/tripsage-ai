"""
TripSage settings initialization module.

This module provides functions to initialize and validate the application settings
at startup time. It ensures all required settings are available and valid.
"""

import logging
from typing import Any, Dict, List

from src.utils.settings import AppSettings, settings

logger = logging.getLogger(__name__)


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
    logger.info("Initializing application settings")

    # Check environment
    env = settings.environment
    logger.info(f"Application environment: {env}")

    # Validate critical settings
    _validate_critical_settings(settings)

    # Additional initialization for specific environments
    if env == "development":
        logger.debug("Development mode enabled")
    elif env == "testing":
        logger.debug("Test mode enabled")
    elif env == "production":
        logger.info("Production mode enabled")
        _validate_production_settings(settings)

    logger.info("Settings initialization completed successfully")
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

    # Check database configuration based on provider
    if settings.database.db_provider == "supabase":
        if not settings.database.supabase_url:
            critical_errors.append("Supabase URL is missing")
        if not settings.database.supabase_anon_key.get_secret_value():
            critical_errors.append("Supabase anonymous key is missing")
    elif settings.database.db_provider == "neon":
        if not settings.database.neon_connection_string:
            critical_errors.append("Neon connection string is missing")
    else:
        critical_errors.append(
            f"Invalid database provider: {settings.database.db_provider}"
        )

    # Check Neo4j configuration
    if not settings.neo4j.password.get_secret_value():
        critical_errors.append("Neo4j password is missing")

    # Raise an error with all validation issues if any were found
    if critical_errors:
        error_message = "Critical settings validation failed:\n- " + "\n- ".join(
            critical_errors
        )
        logger.error(error_message)
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

    # In production, most MCP servers should have API keys configured
    for server_name in [
        "weather_mcp",
        "webcrawl_mcp",
        "flights_mcp",
        "google_maps_mcp",
        "playwright_mcp",
        "stagehand_mcp",
        "time_mcp",
        "docker_mcp",
        "openapi_mcp",
    ]:
        server_config = getattr(settings, server_name)
        if hasattr(server_config, "api_key") and server_config.api_key is None:
            production_errors.append(f"{server_name.upper()} API key is missing")

    # Validate Airbnb MCP configuration
    if settings.accommodations_mcp.airbnb.endpoint == "http://localhost:3000":
        production_errors.append(
            "DEFAULT_AIRBNB_MCP_ENDPOINT is using localhost in production. "
            "Should be set to deployed OpenBnB MCP server URL."
        )

    # Validate Duffel API key for Flights MCP
    if not settings.flights_mcp.duffel_api_key.get_secret_value():
        production_errors.append("DUFFEL_API_KEY is missing for flights_mcp")

    # Validate Crawl4AI API key for WebCrawl MCP
    if not settings.webcrawl_mcp.crawl4ai_api_key.get_secret_value():
        production_errors.append("CRAWL4AI_API_KEY is missing for webcrawl_mcp")

    # Validate Browserbase API key for Stagehand MCP
    if not settings.stagehand_mcp.browserbase_api_key.get_secret_value():
        production_errors.append("BROWSERBASE_API_KEY is missing for stagehand_mcp")

    # Validate Browserbase Project ID for Stagehand MCP
    if not settings.stagehand_mcp.browserbase_project_id:
        production_errors.append("BROWSERBASE_PROJECT_ID is missing for stagehand_mcp")

    # Additional production-specific validations
    if production_errors:
        warning_message = "Production settings validation warnings:\n- " + "\n- ".join(
            production_errors
        )
        logger.warning(warning_message)


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
