"""API configuration using the new consolidated settings.

This module re-exports the new configuration for backward compatibility
during the transition period.
"""

from tripsage_core.config import AppSettings, get_api_settings, get_settings

# Re-export for compatibility
Settings = AppSettings
get_settings_instance = get_settings

# New patterns
settings = get_settings()
api_settings = get_api_settings()

__all__ = [
    "Settings",
    "get_settings_instance",
    "settings",
    "api_settings",
    "get_settings",
    "get_api_settings",
]
