"""Configurable Deployment Strategies.

This module implements various deployment strategies that can be selected based on
the enterprise configuration. It provides both simple and enterprise deployment
patterns to support different operational requirements.
"""

import asyncio
import logging
import secrets
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from tripsage_core.config import DeploymentStrategy, get_enterprise_config


logger = logging.getLogger(__name__)


class DeploymentPhase(str, Enum):
    """Deployment phases for tracking progress."""

    PREPARING = "preparing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    SWITCHING = "switching"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"


class HealthCheckResult(BaseModel):
    """Result of a health check during deployment."""

    healthy: bool = Field(..., description="Whether the health check passed")
    response_time: float = Field(
        ..., description="Health check response time in seconds"
    )
    checks: dict[str, bool] = Field(
        default_factory=dict, description="Individual check results"
    )
    message: str = Field(default="", description="Health check message")
    timestamp: float = Field(default_factory=time.time, description="Check timestamp")


class DeploymentMetrics(BaseModel):
    """Metrics collected during deployment."""

    deployment_id: str = Field(..., description="Unique deployment identifier")
    strategy: str = Field(..., description="Deployment strategy used")
    start_time: float = Field(
        default_factory=time.time, description="Deployment start time"
    )
    end_time: float | None = Field(default=None, description="Deployment end time")
    phase: DeploymentPhase = Field(
        default=DeploymentPhase.PREPARING, description="Current phase"
    )

    # Health and performance metrics
    health_checks: list[HealthCheckResult] = Field(
        default_factory=list, description="Health check history"
    )
    error_rate: float = Field(default=0.0, description="Current error rate")
    response_time_p95: float = Field(
        default=0.0, description="95th percentile response time"
    )

    # Deployment progress
    instances_deployed: int = Field(
        default=0, description="Number of instances deployed"
    )
    instances_healthy: int = Field(default=0, description="Number of healthy instances")
    traffic_percentage: float = Field(
        default=0.0, description="Percentage of traffic routed"
    )

    def get_duration(self) -> float:
        """Get deployment duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    def get_success_rate(self) -> float:
        """Get deployment success rate based on health checks."""
        if not self.health_checks:
            return 0.0

        successful_checks = sum(1 for check in self.health_checks if check.healthy)
        return successful_checks / len(self.health_checks)


class BaseDeploymentStrategy(ABC):
    """Base class for deployment strategies."""

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self.name = name
        self.config = config or {}
        self.enterprise_config = get_enterprise_config()
        self._random = secrets.SystemRandom()

    @abstractmethod
    async def deploy(
        self,
        deployment_id: str,
        image_tag: str,
        environment: str,
        config: dict[str, Any],
    ) -> DeploymentMetrics:
        """Execute the deployment strategy."""

    @abstractmethod
    async def rollback(
        self,
        deployment_id: str,
        previous_version: str,
        environment: str,
    ) -> DeploymentMetrics:
        """Rollback to previous version."""

    async def health_check(
        self,
        environment: str,
        timeout: float = 30.0,
    ) -> HealthCheckResult:
        """Perform health check on deployment."""
        start_time = time.time()

        try:
            # Simulate health checks for different components
            await asyncio.sleep(0.1)  # Simulate check time

            checks = {
                "api_health": True,
                "database_connection": True,
                "cache_connection": True,
                "memory_usage": True,
                "cpu_usage": True,
            }

            # Simulate occasional failures for demo purposes
            if self._random.random() < 0.1:  # 10% chance of failure
                checks["api_health"] = False

            all_healthy = all(checks.values())
            response_time = time.time() - start_time

            return HealthCheckResult(
                healthy=all_healthy,
                response_time=response_time,
                checks=checks,
                message="All systems operational"
                if all_healthy
                else "Some checks failed",
            )

        except Exception as e:
            response_time = time.time() - start_time
            logger.exception(f"Health check failed: {e}")

            return HealthCheckResult(
                healthy=False,
                response_time=response_time,
                checks={},
                message=f"Health check error: {e!s}",
            )


class SimpleDeploymentStrategy(BaseDeploymentStrategy):
    """Simple deployment strategy for direct deployments.

    This strategy deploys directly to the target environment without
    complex orchestration. It's ideal for development and simple production
    environments where downtime is acceptable.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("simple", config)
        logger.info("Initialized simple deployment strategy")

    async def deploy(
        self,
        deployment_id: str,
        image_tag: str,
        environment: str,
        config: dict[str, Any],
    ) -> DeploymentMetrics:
        """Execute simple deployment."""
        logger.info(f"Starting simple deployment {deployment_id} to {environment}")

        metrics = DeploymentMetrics(
            deployment_id=deployment_id,
            strategy="simple",
            phase=DeploymentPhase.PREPARING,
        )

        try:
            # Phase 1: Preparing
            metrics.phase = DeploymentPhase.PREPARING
            logger.info(f"Preparing deployment {deployment_id}")
            await asyncio.sleep(1)  # Simulate preparation time

            # Phase 2: Deploying
            metrics.phase = DeploymentPhase.DEPLOYING
            logger.info(f"Deploying image {image_tag} to {environment}")
            await asyncio.sleep(2)  # Simulate deployment time

            metrics.instances_deployed = 1

            # Phase 3: Testing
            metrics.phase = DeploymentPhase.TESTING
            logger.info(f"Running health checks for deployment {deployment_id}")

            health_result = await self.health_check(environment)
            metrics.health_checks.append(health_result)

            if health_result.healthy:
                metrics.instances_healthy = 1
                metrics.traffic_percentage = 100.0
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(f"Simple deployment {deployment_id} completed successfully")
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(
                    f"Simple deployment {deployment_id} failed health check"
                )

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Simple deployment {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics

    async def rollback(
        self,
        deployment_id: str,
        previous_version: str,
        environment: str,
    ) -> DeploymentMetrics:
        """Rollback to previous version."""
        logger.info(f"Rolling back deployment {deployment_id} to {previous_version}")

        metrics = DeploymentMetrics(
            deployment_id=f"{deployment_id}_rollback",
            strategy="simple_rollback",
            phase=DeploymentPhase.ROLLING_BACK,
        )

        try:
            # Simulate rollback process
            await asyncio.sleep(1)

            health_result = await self.health_check(environment)
            metrics.health_checks.append(health_result)

            if health_result.healthy:
                metrics.instances_healthy = 1
                metrics.traffic_percentage = 100.0
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(f"Rollback {deployment_id} completed successfully")
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(f"Rollback {deployment_id} failed")

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Rollback {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics


class BlueGreenDeploymentStrategy(BaseDeploymentStrategy):
    """Blue-green deployment strategy for zero-downtime deployments.

    This strategy maintains two identical production environments (blue and green)
    and switches traffic between them. It provides instant rollback capabilities
    and zero-downtime deployments.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("blue_green", config)
        self.switch_delay = config.get("switch_delay", 5.0) if config else 5.0
        logger.info("Initialized blue-green deployment strategy")

    async def deploy(
        self,
        deployment_id: str,
        image_tag: str,
        environment: str,
        config: dict[str, Any],
    ) -> DeploymentMetrics:
        """Execute blue-green deployment."""
        logger.info(f"Starting blue-green deployment {deployment_id} to {environment}")

        metrics = DeploymentMetrics(
            deployment_id=deployment_id,
            strategy="blue_green",
            phase=DeploymentPhase.PREPARING,
        )

        try:
            # Phase 1: Preparing
            metrics.phase = DeploymentPhase.PREPARING
            logger.info(f"Preparing blue-green deployment {deployment_id}")
            await asyncio.sleep(1)

            # Phase 2: Deploying to inactive environment
            metrics.phase = DeploymentPhase.DEPLOYING
            logger.info(f"Deploying image {image_tag} to inactive environment")
            await asyncio.sleep(3)  # Blue-green takes longer to deploy

            metrics.instances_deployed = 1

            # Phase 3: Testing inactive environment
            metrics.phase = DeploymentPhase.TESTING
            logger.info(f"Testing inactive environment for deployment {deployment_id}")

            # Perform multiple health checks
            for i in range(3):
                health_result = await self.health_check(f"{environment}_inactive")
                metrics.health_checks.append(health_result)

                if not health_result.healthy:
                    metrics.phase = DeploymentPhase.FAILED
                    logger.exception(
                        f"Blue-green deployment {deployment_id} failed health check "
                        f"{i + 1}"
                    )
                    metrics.end_time = time.time()
                    return metrics

                await asyncio.sleep(1)

            metrics.instances_healthy = 1

            # Phase 4: Traffic switching
            metrics.phase = DeploymentPhase.SWITCHING
            logger.info(f"Switching traffic for deployment {deployment_id}")

            # Gradual traffic switch with monitoring
            for percentage in [25, 50, 75, 100]:
                await asyncio.sleep(self.switch_delay / 4)
                metrics.traffic_percentage = percentage

                # Monitor during switch
                health_result = await self.health_check(environment)
                metrics.health_checks.append(health_result)

                if (
                    not health_result.healthy
                    and self.enterprise_config.enable_auto_rollback
                ):
                    logger.warning(
                        f"Auto-rollback triggered for deployment {deployment_id}"
                    )
                    return await self.rollback(deployment_id, "previous", environment)

                logger.info(
                    f"Traffic switched to {percentage}% for deployment {deployment_id}"
                )

            # Phase 5: Monitoring
            metrics.phase = DeploymentPhase.MONITORING
            logger.info(f"Monitoring deployment {deployment_id}")
            await asyncio.sleep(2)

            # Final health check
            final_health = await self.health_check(environment)
            metrics.health_checks.append(final_health)

            if final_health.healthy:
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(
                    f"Blue-green deployment {deployment_id} completed successfully"
                )
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(
                    f"Blue-green deployment {deployment_id} failed final check"
                )

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Blue-green deployment {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics

    async def rollback(
        self,
        deployment_id: str,
        previous_version: str,
        environment: str,
    ) -> DeploymentMetrics:
        """Instant rollback by switching traffic back."""
        logger.info(f"Rolling back blue-green deployment {deployment_id}")

        metrics = DeploymentMetrics(
            deployment_id=f"{deployment_id}_rollback",
            strategy="blue_green_rollback",
            phase=DeploymentPhase.ROLLING_BACK,
        )

        try:
            # Instant traffic switch back
            await asyncio.sleep(0.5)  # Very fast rollback

            metrics.traffic_percentage = 100.0
            metrics.instances_healthy = 1

            health_result = await self.health_check(environment)
            metrics.health_checks.append(health_result)

            if health_result.healthy:
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(f"Blue-green rollback {deployment_id} completed")
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(f"Blue-green rollback {deployment_id} failed")

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Blue-green rollback {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics


class CanaryDeploymentStrategy(BaseDeploymentStrategy):
    """Canary deployment strategy for gradual rollouts.

    This strategy gradually rolls out the new version to a small percentage
    of traffic, monitors performance, and gradually increases traffic if
    the deployment is successful.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("canary", config)
        self.canary_steps = (
            config.get("canary_steps", [5, 10, 25, 50, 100])
            if config
            else [5, 10, 25, 50, 100]
        )
        self.step_duration = config.get("step_duration", 3.0) if config else 3.0
        logger.info(
            f"Initialized canary deployment strategy with steps: {self.canary_steps}"
        )

    async def deploy(
        self,
        deployment_id: str,
        image_tag: str,
        environment: str,
        config: dict[str, Any],
    ) -> DeploymentMetrics:
        """Execute canary deployment."""
        logger.info(f"Starting canary deployment {deployment_id} to {environment}")

        metrics = DeploymentMetrics(
            deployment_id=deployment_id,
            strategy="canary",
            phase=DeploymentPhase.PREPARING,
        )

        try:
            # Phase 1: Preparing
            metrics.phase = DeploymentPhase.PREPARING
            logger.info(f"Preparing canary deployment {deployment_id}")
            await asyncio.sleep(1)

            # Phase 2: Deploy canary instances
            metrics.phase = DeploymentPhase.DEPLOYING
            logger.info(f"Deploying canary instances for {deployment_id}")
            await asyncio.sleep(2)

            metrics.instances_deployed = 1  # Start with canary instance

            # Phase 3: Gradual traffic increase
            metrics.phase = DeploymentPhase.TESTING

            for step_percentage in self.canary_steps:
                logger.info(
                    f"Canary step: {step_percentage}% traffic for {deployment_id}"
                )
                metrics.traffic_percentage = step_percentage

                # Monitor for this step duration
                await asyncio.sleep(self.step_duration)

                # Perform health checks
                health_result = await self.health_check(environment)
                metrics.health_checks.append(health_result)

                if not health_result.healthy:
                    logger.exception(
                        f"Canary deployment {deployment_id} failed at "
                        f"{step_percentage}%"
                    )
                    metrics.phase = DeploymentPhase.FAILED

                    if self.enterprise_config.enable_auto_rollback:
                        return await self.rollback(
                            deployment_id, "previous", environment
                        )

                    metrics.end_time = time.time()
                    return metrics

                # Canary analysis if enabled
                if self.enterprise_config.enable_canary_analysis:
                    analysis_result = await self._analyze_canary_performance(
                        environment, step_percentage
                    )

                    if not analysis_result["continue"]:
                        logger.warning(
                            f"Canary analysis recommends stopping deployment "
                            f"{deployment_id}"
                        )
                        metrics.phase = DeploymentPhase.FAILED

                        if self.enterprise_config.enable_auto_rollback:
                            return await self.rollback(
                                deployment_id, "previous", environment
                            )

                        metrics.end_time = time.time()
                        return metrics

                logger.info(
                    f"Canary step {step_percentage}% successful for {deployment_id}"
                )

            # All steps completed successfully
            metrics.instances_healthy = metrics.instances_deployed
            metrics.phase = DeploymentPhase.COMPLETED
            logger.info(f"Canary deployment {deployment_id} completed successfully")

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Canary deployment {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics

    async def _analyze_canary_performance(
        self,
        environment: str,
        traffic_percentage: float,
    ) -> dict[str, Any]:
        """Analyze canary performance and decide whether to continue."""
        await asyncio.sleep(0.5)  # Simulate analysis time

        # Simulate performance analysis with secure randomness
        error_rate = self._random.uniform(0.0, 0.05)  # 0-5% error rate
        response_time = self._random.uniform(50, 200)  # 50-200ms response time

        # Decision logic
        continue_deployment = (
            error_rate < 0.02  # Less than 2% error rate
            and response_time < 150  # Less than 150ms response time
        )

        analysis = {
            "continue": continue_deployment,
            "error_rate": error_rate,
            "response_time": response_time,
            "traffic_percentage": traffic_percentage,
            "recommendation": "continue" if continue_deployment else "rollback",
        }

        logger.info(f"Canary analysis: {analysis}")
        return analysis

    async def rollback(
        self,
        deployment_id: str,
        previous_version: str,
        environment: str,
    ) -> DeploymentMetrics:
        """Rollback canary deployment."""
        logger.info(f"Rolling back canary deployment {deployment_id}")

        metrics = DeploymentMetrics(
            deployment_id=f"{deployment_id}_rollback",
            strategy="canary_rollback",
            phase=DeploymentPhase.ROLLING_BACK,
        )

        try:
            # Gradually reduce traffic to new version
            for percentage in [50, 25, 10, 0]:
                await asyncio.sleep(0.5)
                metrics.traffic_percentage = percentage
                logger.info(f"Reducing canary traffic to {percentage}%")

            health_result = await self.health_check(environment)
            metrics.health_checks.append(health_result)

            if health_result.healthy:
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(f"Canary rollback {deployment_id} completed")
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(f"Canary rollback {deployment_id} failed")

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Canary rollback {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics


class RollingDeploymentStrategy(BaseDeploymentStrategy):
    """Rolling deployment strategy for gradual instance updates.

    This strategy updates instances one by one, maintaining service availability
    throughout the deployment process. It's ideal for stateless applications
    with multiple instances.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("rolling", config)
        self.instance_count = config.get("instance_count", 3) if config else 3
        self.update_delay = config.get("update_delay", 2.0) if config else 2.0
        logger.info(
            f"Initialized rolling deployment strategy with "
            f"{self.instance_count} instances"
        )

    async def deploy(
        self,
        deployment_id: str,
        image_tag: str,
        environment: str,
        config: dict[str, Any],
    ) -> DeploymentMetrics:
        """Execute rolling deployment."""
        logger.info(f"Starting rolling deployment {deployment_id} to {environment}")

        metrics = DeploymentMetrics(
            deployment_id=deployment_id,
            strategy="rolling",
            phase=DeploymentPhase.PREPARING,
        )

        try:
            # Phase 1: Preparing
            metrics.phase = DeploymentPhase.PREPARING
            logger.info(f"Preparing rolling deployment {deployment_id}")
            await asyncio.sleep(1)

            # Phase 2: Rolling updates
            metrics.phase = DeploymentPhase.DEPLOYING

            for instance_num in range(1, self.instance_count + 1):
                logger.info(
                    f"Updating instance {instance_num}/{self.instance_count} "
                    f"for {deployment_id}"
                )

                # Update this instance
                await asyncio.sleep(self.update_delay)
                metrics.instances_deployed = instance_num

                # Health check after each instance
                health_result = await self.health_check(environment)
                metrics.health_checks.append(health_result)

                if health_result.healthy:
                    metrics.instances_healthy = instance_num
                    metrics.traffic_percentage = (
                        instance_num / self.instance_count
                    ) * 100
                    logger.info(
                        f"Instance {instance_num} healthy for deployment "
                        f"{deployment_id}"
                    )
                else:
                    logger.exception(
                        f"Instance {instance_num} failed health check for "
                        f"deployment {deployment_id}"
                    )
                    metrics.phase = DeploymentPhase.FAILED

                    if self.enterprise_config.enable_auto_rollback:
                        return await self.rollback(
                            deployment_id, "previous", environment
                        )

                    metrics.end_time = time.time()
                    return metrics

            # Phase 3: Final verification
            metrics.phase = DeploymentPhase.TESTING
            logger.info(f"Final verification for rolling deployment {deployment_id}")

            final_health = await self.health_check(environment)
            metrics.health_checks.append(final_health)

            if final_health.healthy:
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(
                    f"Rolling deployment {deployment_id} completed successfully"
                )
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(
                    f"Rolling deployment {deployment_id} failed final verification"
                )

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Rolling deployment {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics

    async def rollback(
        self,
        deployment_id: str,
        previous_version: str,
        environment: str,
    ) -> DeploymentMetrics:
        """Rollback rolling deployment."""
        logger.info(f"Rolling back deployment {deployment_id}")

        metrics = DeploymentMetrics(
            deployment_id=f"{deployment_id}_rollback",
            strategy="rolling_rollback",
            phase=DeploymentPhase.ROLLING_BACK,
        )

        try:
            # Roll back instances one by one
            for instance_num in range(1, self.instance_count + 1):
                logger.info(
                    f"Rolling back instance {instance_num}/{self.instance_count}"
                )
                await asyncio.sleep(self.update_delay / 2)  # Faster rollback

                metrics.instances_healthy = instance_num
                metrics.traffic_percentage = (instance_num / self.instance_count) * 100

            health_result = await self.health_check(environment)
            metrics.health_checks.append(health_result)

            if health_result.healthy:
                metrics.phase = DeploymentPhase.COMPLETED
                logger.info(f"Rolling rollback {deployment_id} completed")
            else:
                metrics.phase = DeploymentPhase.FAILED
                logger.exception(f"Rolling rollback {deployment_id} failed")

            metrics.end_time = time.time()
            return metrics

        except Exception as e:
            logger.exception(f"Rolling rollback {deployment_id} failed: {e}")
            metrics.phase = DeploymentPhase.FAILED
            metrics.end_time = time.time()
            return metrics


def get_deployment_strategy(
    strategy: DeploymentStrategy | None = None,
    config: dict[str, Any] | None = None,
) -> BaseDeploymentStrategy:
    """Get deployment strategy based on enterprise configuration.

    Args:
        strategy: Specific strategy to use (overrides enterprise config)
        config: Strategy-specific configuration

    Returns:
        Appropriate deployment strategy instance
    """
    enterprise_config = get_enterprise_config()

    # Use provided strategy or fall back to enterprise config
    target_strategy = strategy or enterprise_config.deployment_strategy

    logger.debug(f"Creating deployment strategy: {target_strategy}")

    if target_strategy == DeploymentStrategy.SIMPLE:
        return SimpleDeploymentStrategy(config)
    elif target_strategy == DeploymentStrategy.BLUE_GREEN:
        return BlueGreenDeploymentStrategy(config)
    elif target_strategy == DeploymentStrategy.CANARY:
        return CanaryDeploymentStrategy(config)
    elif target_strategy == DeploymentStrategy.ROLLING:
        return RollingDeploymentStrategy(config)
    else:
        logger.warning(
            f"Unknown deployment strategy {target_strategy}, falling back to simple"
        )
        return SimpleDeploymentStrategy(config)
