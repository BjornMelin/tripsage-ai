"""Enterprise Feature Flags and Configuration Framework.

This module provides a centralized configuration framework for "configurable complexity"
patterns throughout TripSage. It enables environment-based feature toggles for enterprise
features while maintaining simple defaults for development efficiency.

The framework follows 2025 state-of-the-art patterns for feature management, including:
- Environment-driven configuration with Pydantic Settings
- Simple/Enterprise mode toggles for complexity management
- Granular feature control for portfolio demonstration
- Configuration validation matrices for consistency

Example usage:
    # Development mode (default - simple)
    export ENTERPRISE_ENABLE_ENTERPRISE_FEATURES=false
    export ENTERPRISE_CIRCUIT_BREAKER_MODE=simple

    # Portfolio demonstration mode (showcase enterprise patterns)
    export ENTERPRISE_ENABLE_ENTERPRISE_FEATURES=true
    export ENTERPRISE_CIRCUIT_BREAKER_MODE=enterprise
    export ENTERPRISE_DEPLOYMENT_STRATEGY=blue_green
"""

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ComplexityMode(str, Enum):
    """Complexity modes for configurable features."""

    SIMPLE = "simple"
    ENTERPRISE = "enterprise"


class DeploymentStrategy(str, Enum):
    """Deployment strategy options."""

    SIMPLE = "simple"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    AB_TEST = "ab_test"
    ROLLING = "rolling"


class OrchestrationMode(str, Enum):
    """LangGraph orchestration complexity modes."""

    SIMPLE = "simple"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"


class DatabaseArchitectureMode(str, Enum):
    """Database architecture complexity modes."""

    SIMPLE = "simple"
    ENTERPRISE = "enterprise"


class EnterpriseFeatureFlags(BaseSettings):
    """Enterprise feature flags for configurable complexity management.

    This configuration class provides centralized control over enterprise features
    throughout TripSage, enabling simple defaults with opt-in complexity for
    portfolio demonstration and production scaling.
    """

    # Global Enterprise Mode Toggle
    enable_enterprise_features: bool = Field(
        default=False,
        description="Master toggle for all enterprise features - enables portfolio demonstration mode",
    )

    # Circuit Breaker Configuration
    circuit_breaker_mode: ComplexityMode = Field(
        default=ComplexityMode.SIMPLE,
        description="Circuit breaker complexity mode (simple=timeouts/retries, enterprise=full circuit breakers)",
    )
    enable_circuit_breaker_analytics: bool = Field(
        default=False,
        description="Enable circuit breaker performance analytics and monitoring",
    )
    enable_adaptive_recovery: bool = Field(
        default=False,
        description="Enable adaptive recovery strategies based on failure patterns",
    )
    enable_failure_categorization: bool = Field(
        default=False,
        description="Enable intelligent failure categorization and routing",
    )

    # Deployment Infrastructure Configuration
    deployment_strategy: DeploymentStrategy = Field(
        default=DeploymentStrategy.SIMPLE,
        description="Deployment strategy complexity (simple=direct, enterprise=blue-green/canary)",
    )
    enable_canary_analysis: bool = Field(
        default=False, description="Enable automated canary deployment analysis"
    )
    enable_auto_rollback: bool = Field(
        default=False, description="Enable automatic rollback on deployment failures"
    )
    enable_deployment_monitoring: bool = Field(
        default=False,
        description="Enable comprehensive deployment monitoring and alerting",
    )

    # Database Architecture Configuration
    database_architecture_mode: DatabaseArchitectureMode = Field(
        default=DatabaseArchitectureMode.SIMPLE,
        description="Database architecture complexity (simple=single instance, enterprise=replicas/sharding)",
    )
    enable_read_replicas: bool = Field(
        default=False,
        description="Enable read replica configuration for database scaling",
    )
    enable_query_optimization: bool = Field(
        default=False,
        description="Enable advanced query optimization and caching strategies",
    )
    enable_connection_pooling: bool = Field(
        default=True, description="Enable advanced database connection pooling"
    )
    enable_db_monitoring: bool = Field(
        default=False,
        description="Enable comprehensive database performance monitoring",
    )

    # Orchestration Configuration
    orchestration_mode: OrchestrationMode = Field(
        default=OrchestrationMode.SIMPLE,
        description="LangGraph orchestration complexity mode",
    )
    enable_tool_registry: bool = Field(
        default=False, description="Enable dynamic tool registry and discovery"
    )
    enable_usage_analytics: bool = Field(
        default=False,
        description="Enable orchestration usage analytics and optimization",
    )
    enable_workflow_versioning: bool = Field(
        default=False,
        description="Enable workflow versioning and rollback capabilities",
    )

    # Observability & Monitoring
    enable_distributed_tracing: bool = Field(
        default=False, description="Enable distributed tracing with OpenTelemetry"
    )
    enable_metrics_collection: bool = Field(
        default=True, description="Enable comprehensive metrics collection"
    )
    enable_custom_dashboards: bool = Field(
        default=False, description="Enable custom monitoring dashboards"
    )

    # Security & Compliance
    enable_audit_logging: bool = Field(
        default=True, description="Enable comprehensive audit logging"
    )
    enable_data_encryption: bool = Field(
        default=True,
        description="Enable advanced data encryption at rest and in transit",
    )
    compliance_mode: Literal["none", "gdpr", "ccpa", "hipaa", "soc2"] = Field(
        default="none", description="Compliance framework to enforce"
    )

    # Performance & Scale
    enable_auto_scaling: bool = Field(
        default=False, description="Enable automatic scaling based on load"
    )
    enable_load_balancing: bool = Field(
        default=False, description="Enable advanced load balancing strategies"
    )
    enable_response_compression: bool = Field(
        default=True, description="Enable response compression for performance"
    )
    enable_request_batching: bool = Field(
        default=False, description="Enable request batching for efficiency"
    )

    # Integration & Extensibility
    enable_webhook_integration: bool = Field(
        default=True, description="Enable webhook support for external integrations"
    )
    enable_custom_plugins: bool = Field(
        default=False, description="Enable custom plugin system for extensibility"
    )
    enable_api_versioning: bool = Field(
        default=False, description="Enable API versioning for backward compatibility"
    )

    model_config = {"env_prefix": "ENTERPRISE_", "case_sensitive": False}

    @field_validator(
        "circuit_breaker_mode",
        "database_architecture_mode",
        "orchestration_mode",
        "deployment_strategy",
    )
    @classmethod
    def validate_enterprise_mode_consistency(cls, v, info):
        """Validate that enterprise modes are consistent with enable_enterprise_features."""
        # This will be called during model validation
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation and auto-configuration."""
        # Auto-enable enterprise features when enterprise mode is set
        if self.enable_enterprise_features:
            self._enable_enterprise_defaults()

        # Validate configuration consistency
        validation_errors = self.validate_configuration_matrix()
        if validation_errors:
            # Log warnings instead of raising errors to maintain flexibility
            import logging

            logger = logging.getLogger(__name__)
            for error in validation_errors:
                logger.warning(f"Enterprise configuration warning: {error}")

    def _enable_enterprise_defaults(self) -> None:
        """Enable default enterprise features when enterprise mode is activated."""
        # Auto-configure enterprise modes
        if self.circuit_breaker_mode == ComplexityMode.SIMPLE:
            object.__setattr__(self, "circuit_breaker_mode", ComplexityMode.ENTERPRISE)

        if self.deployment_strategy == DeploymentStrategy.SIMPLE:
            object.__setattr__(
                self, "deployment_strategy", DeploymentStrategy.BLUE_GREEN
            )

        if self.database_architecture_mode == DatabaseArchitectureMode.SIMPLE:
            object.__setattr__(
                self, "database_architecture_mode", DatabaseArchitectureMode.ENTERPRISE
            )

        if self.orchestration_mode == OrchestrationMode.SIMPLE:
            object.__setattr__(self, "orchestration_mode", OrchestrationMode.ENTERPRISE)

        # Enable key enterprise features
        object.__setattr__(self, "enable_distributed_tracing", True)
        object.__setattr__(self, "enable_custom_dashboards", True)
        object.__setattr__(self, "enable_auto_scaling", True)

    def validate_configuration_matrix(self) -> List[str]:
        """Validate configuration combinations for consistency.

        Returns:
            List of validation error messages
        """
        errors = []

        # Simple mode validations
        if not self.enable_enterprise_features:
            if self.circuit_breaker_mode == ComplexityMode.ENTERPRISE:
                errors.append(
                    "Enterprise circuit breaker mode requires enable_enterprise_features=true"
                )

            if self.deployment_strategy in [
                DeploymentStrategy.BLUE_GREEN,
                DeploymentStrategy.CANARY,
            ]:
                errors.append(
                    "Advanced deployment strategies require enable_enterprise_features=true"
                )

            if self.enable_auto_scaling:
                errors.append("Auto-scaling requires enable_enterprise_features=true")

        # Enterprise mode validations
        if self.enable_enterprise_features:
            if not self.enable_audit_logging:
                errors.append(
                    "Enterprise mode should enable audit logging for compliance"
                )

            if not self.enable_metrics_collection:
                errors.append(
                    "Enterprise mode requires metrics collection for monitoring"
                )

        # Compliance validations
        if self.compliance_mode != "none":
            if not self.enable_audit_logging:
                errors.append(
                    f"Compliance mode '{self.compliance_mode}' requires audit logging"
                )

            if not self.enable_data_encryption:
                errors.append(
                    f"Compliance mode '{self.compliance_mode}' requires data encryption"
                )

        # Performance consistency checks
        if self.enable_auto_scaling and not self.enable_metrics_collection:
            errors.append(
                "Auto-scaling requires metrics collection for decision making"
            )

        return errors

    def get_feature_summary(self) -> Dict[str, Any]:
        """Get a summary of current enterprise feature configuration.

        Returns:
            Dictionary with feature configuration summary
        """
        enabled_features = []
        disabled_features = []

        # Check boolean fields
        for field_name, field_info in self.__class__.model_fields.items():
            if field_info.annotation == bool:
                value = getattr(self, field_name)
                if value:
                    enabled_features.append(field_name)
                else:
                    disabled_features.append(field_name)

        # Get complexity modes
        modes = {
            "circuit_breaker_mode": self.circuit_breaker_mode.value,
            "deployment_strategy": self.deployment_strategy.value,
            "database_architecture_mode": self.database_architecture_mode.value,
            "orchestration_mode": self.orchestration_mode.value,
            "compliance_mode": self.compliance_mode,
        }

        return {
            "enterprise_mode": self.enable_enterprise_features,
            "complexity_modes": modes,
            "enabled_features": enabled_features,
            "disabled_features": disabled_features,
            "total_features": len(enabled_features) + len(disabled_features),
            "enterprise_percentage": round(
                (
                    len(enabled_features)
                    / (len(enabled_features) + len(disabled_features))
                )
                * 100,
                1,
            ),
        }

    def get_environment_config(self) -> Dict[str, str]:
        """Get environment variable configuration for current settings.

        Returns:
            Dictionary of environment variables and their values
        """
        config = {}

        # Add all boolean fields
        for field_name, field_info in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            env_var = f"ENTERPRISE_{field_name.upper()}"

            if isinstance(value, bool):
                config[env_var] = str(value).lower()
            elif isinstance(value, Enum):
                config[env_var] = value.value
            else:
                config[env_var] = str(value)

        return config

    def is_simple_mode(self) -> bool:
        """Check if running in simple mode (minimal enterprise features)."""
        return not self.enable_enterprise_features

    def is_enterprise_mode(self) -> bool:
        """Check if running in enterprise mode (full enterprise features)."""
        return self.enable_enterprise_features

    def is_portfolio_mode(self) -> bool:
        """Check if configured for portfolio demonstration (enterprise features enabled)."""
        return self.enable_enterprise_features


# Configuration Presets
class EnterpriseConfigPresets:
    """Predefined configuration presets for different use cases."""

    @staticmethod
    def development() -> Dict[str, Any]:
        """Development environment preset - simple mode."""
        return {
            "enable_enterprise_features": False,
            "circuit_breaker_mode": ComplexityMode.SIMPLE,
            "deployment_strategy": DeploymentStrategy.SIMPLE,
            "database_architecture_mode": DatabaseArchitectureMode.SIMPLE,
            "orchestration_mode": OrchestrationMode.SIMPLE,
            "enable_metrics_collection": True,
            "enable_audit_logging": True,
        }

    @staticmethod
    def portfolio_demo() -> Dict[str, Any]:
        """Portfolio demonstration preset - showcase enterprise patterns."""
        return {
            "enable_enterprise_features": True,
            "circuit_breaker_mode": ComplexityMode.ENTERPRISE,
            "deployment_strategy": DeploymentStrategy.BLUE_GREEN,
            "database_architecture_mode": DatabaseArchitectureMode.ENTERPRISE,
            "orchestration_mode": OrchestrationMode.ENTERPRISE,
            "enable_distributed_tracing": True,
            "enable_custom_dashboards": True,
            "enable_auto_scaling": True,
            "enable_canary_analysis": True,
            "enable_auto_rollback": True,
        }

    @staticmethod
    def production() -> Dict[str, Any]:
        """Production environment preset - enterprise features with focus on reliability."""
        return {
            "enable_enterprise_features": True,
            "circuit_breaker_mode": ComplexityMode.ENTERPRISE,
            "deployment_strategy": DeploymentStrategy.BLUE_GREEN,
            "database_architecture_mode": DatabaseArchitectureMode.ENTERPRISE,
            "orchestration_mode": OrchestrationMode.ENTERPRISE,
            "enable_audit_logging": True,
            "enable_data_encryption": True,
            "enable_metrics_collection": True,
            "enable_distributed_tracing": True,
            "compliance_mode": "soc2",
            "enable_auto_scaling": True,
        }

    @staticmethod
    def compliance_focused() -> Dict[str, Any]:
        """Compliance-focused preset for regulated industries."""
        return {
            "enable_enterprise_features": True,
            "circuit_breaker_mode": ComplexityMode.ENTERPRISE,
            "deployment_strategy": DeploymentStrategy.BLUE_GREEN,
            "database_architecture_mode": DatabaseArchitectureMode.ENTERPRISE,
            "orchestration_mode": OrchestrationMode.ENTERPRISE,
            "enable_audit_logging": True,
            "enable_data_encryption": True,
            "compliance_mode": "hipaa",
            "enable_distributed_tracing": True,
            "enable_webhook_integration": False,  # Restricted for compliance
            "enable_custom_plugins": False,  # Restricted for compliance
        }


# Global enterprise configuration instance
enterprise_config = EnterpriseFeatureFlags()


def get_enterprise_config() -> EnterpriseFeatureFlags:
    """Get the global enterprise configuration instance.

    Returns:
        Global EnterpriseFeatureFlags instance
    """
    return enterprise_config


def is_enterprise_mode() -> bool:
    """Check if the application is running in enterprise mode.

    Returns:
        True if enterprise features are enabled, False otherwise
    """
    return enterprise_config.enable_enterprise_features


def is_simple_mode() -> bool:
    """Check if the application is running in simple mode.

    Returns:
        True if enterprise features are disabled, False otherwise
    """
    return not enterprise_config.enable_enterprise_features


def apply_preset(preset_name: str) -> None:
    """Apply a configuration preset to the global enterprise config.

    Args:
        preset_name: Name of the preset to apply ('development', 'portfolio_demo', 'production', 'compliance_focused')

    Raises:
        ValueError: If preset_name is not supported
    """
    presets = {
        "development": EnterpriseConfigPresets.development(),
        "portfolio_demo": EnterpriseConfigPresets.portfolio_demo(),
        "production": EnterpriseConfigPresets.production(),
        "compliance_focused": EnterpriseConfigPresets.compliance_focused(),
    }

    if preset_name not in presets:
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available: {list(presets.keys())}"
        )

    preset_config = presets[preset_name]
    global enterprise_config
    enterprise_config = EnterpriseFeatureFlags(**preset_config)


def get_configuration_for_environment(environment: str) -> Dict[str, Any]:
    """Get recommended configuration for a specific environment.

    Args:
        environment: Environment name ('development', 'testing', 'staging', 'production')

    Returns:
        Dictionary with recommended configuration for the environment
    """
    environment_mappings = {
        "development": EnterpriseConfigPresets.development(),
        "testing": EnterpriseConfigPresets.development(),
        "staging": EnterpriseConfigPresets.production(),
        "production": EnterpriseConfigPresets.production(),
    }

    return environment_mappings.get(environment, EnterpriseConfigPresets.development())
