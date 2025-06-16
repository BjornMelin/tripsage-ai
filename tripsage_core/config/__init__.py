"""TripSage configuration module.

This module provides centralized access to all configuration classes and utilities
for the TripSage application, including the new Enterprise Feature Flags framework.
"""

from tripsage_core.config.base_app_settings import (
    CoreAppSettings,
    get_settings,
    init_settings,
)
from tripsage_core.config.enterprise_config import (
    EnterpriseFeatureFlags,
    EnterpriseConfigPresets,
    get_enterprise_config,
    is_enterprise_mode,
    is_simple_mode,
    apply_preset,
    get_configuration_for_environment,
)
from tripsage_core.config.feature_flags import (
    FeatureFlags as ServiceFeatureFlags,
    get_feature_flags,
    is_direct_integration,
)

__all__ = [
    # Core settings
    "CoreAppSettings",
    "get_settings",
    "init_settings",
    # Enterprise configuration
    "EnterpriseFeatureFlags",
    "EnterpriseConfigPresets", 
    "get_enterprise_config",
    "is_enterprise_mode",
    "is_simple_mode",
    "apply_preset",
    "get_configuration_for_environment",
    # Service feature flags
    "ServiceFeatureFlags",
    "get_feature_flags",
    "is_direct_integration",
]


def get_current_settings() -> CoreAppSettings:
    """Get current application settings with enterprise configuration.
    
    Returns:
        CoreAppSettings instance with access to enterprise configuration
    """
    return get_settings()


def configure_for_environment(environment: str) -> None:
    """Configure enterprise features for a specific environment.
    
    Args:
        environment: Environment name ('development', 'testing', 'staging', 'production')
    """
    config = get_configuration_for_environment(environment)
    apply_preset(environment if environment in ["development", "production"] else "development")


def is_portfolio_mode() -> bool:
    """Check if running in portfolio demonstration mode.
    
    Returns:
        True if enterprise features are enabled for portfolio showcase
    """
    return is_enterprise_mode()


def get_complexity_summary() -> dict:
    """Get a summary of current complexity configuration.
    
    Returns:
        Dictionary with complexity mode summary
    """
    enterprise_config = get_enterprise_config()
    return enterprise_config.get_feature_summary()
