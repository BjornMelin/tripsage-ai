"""TripSage Infrastructure Deployment Module.

This module provides configurable deployment strategies for the TripSage application,
supporting both simple and enterprise deployment patterns based on the enterprise
configuration settings.

The module implements the "configurable complexity" pattern, allowing development
teams to use simple direct deployments while enabling enterprise-grade deployment
strategies for production and portfolio demonstration.
"""

from tripsage_core.infrastructure.deployment.orchestrator import (
    ConfigurableDeploymentOrchestrator,
    DeploymentResult,
    DeploymentStatus,
)
from tripsage_core.infrastructure.deployment.strategies import (
    BlueGreenDeploymentStrategy,
    CanaryDeploymentStrategy,
    DirectDeploymentStrategy,
    RollingDeploymentStrategy,
    get_deployment_strategy,
)


__all__ = [
    "BlueGreenDeploymentStrategy",
    "CanaryDeploymentStrategy",
    "ConfigurableDeploymentOrchestrator",
    "DeploymentResult",
    "DeploymentStatus",
    "DirectDeploymentStrategy",
    "RollingDeploymentStrategy",
    "get_deployment_strategy",
]
