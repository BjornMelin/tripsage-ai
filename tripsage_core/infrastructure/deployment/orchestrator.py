"""Configurable Deployment Orchestrator.

This module provides the main orchestrator for managing deployments using
configurable strategies. It coordinates the deployment process, monitoring,
and rollback capabilities based on enterprise configuration.
"""

import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage_core.config import DeploymentStrategy, get_enterprise_config
from tripsage_core.infrastructure.deployment.strategies import (
    DeploymentMetrics,
    DeploymentPhase,
    get_deployment_strategy,
)

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Overall deployment status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentResult(BaseModel):
    """Result of a deployment operation."""

    deployment_id: str = Field(..., description="Unique deployment identifier")
    status: DeploymentStatus = Field(..., description="Overall deployment status")
    strategy: str = Field(..., description="Deployment strategy used")
    environment: str = Field(..., description="Target environment")
    image_tag: str = Field(..., description="Deployed image tag")

    start_time: float = Field(
        default_factory=time.time, description="Deployment start time"
    )
    end_time: Optional[float] = Field(default=None, description="Deployment end time")

    metrics: Optional[DeploymentMetrics] = Field(
        default=None, description="Deployment metrics"
    )
    rollback_metrics: Optional[DeploymentMetrics] = Field(
        default=None, description="Rollback metrics"
    )

    success: bool = Field(
        default=False, description="Whether deployment was successful"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )

    # Enterprise features
    monitoring_enabled: bool = Field(
        default=False, description="Whether monitoring is enabled"
    )
    auto_rollback_triggered: bool = Field(
        default=False, description="Whether auto-rollback was triggered"
    )

    def get_duration(self) -> float:
        """Get total deployment duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """Get deployment summary for reporting."""
        return {
            "deployment_id": self.deployment_id,
            "status": self.status.value,
            "strategy": self.strategy,
            "environment": self.environment,
            "duration": self.get_duration(),
            "success": self.success,
            "auto_rollback": self.auto_rollback_triggered,
            "monitoring": self.monitoring_enabled,
        }


class ConfigurableDeploymentOrchestrator:
    """Orchestrator for managing configurable deployment strategies.

    This orchestrator coordinates deployment operations using the appropriate
    strategy based on enterprise configuration. It provides monitoring,
    rollback capabilities, and enterprise-grade deployment management.
    """

    def __init__(self):
        self.enterprise_config = get_enterprise_config()
        self.active_deployments: Dict[str, DeploymentResult] = {}
        self.deployment_history: List[DeploymentResult] = []

        logger.info(
            f"Initialized deployment orchestrator with strategy: "
            f"{self.enterprise_config.deployment_strategy}"
        )

    async def deploy(
        self,
        image_tag: str,
        environment: str,
        config: Optional[Dict[str, Any]] = None,
        strategy: Optional[DeploymentStrategy] = None,
    ) -> DeploymentResult:
        """Execute a deployment using the configured strategy.

        Args:
            image_tag: Docker image tag to deploy
            environment: Target environment (e.g., 'staging', 'production')
            config: Deployment-specific configuration
            strategy: Override deployment strategy (optional)

        Returns:
            DeploymentResult with deployment status and metrics
        """
        deployment_id = str(uuid.uuid4())[:8]

        logger.info(
            f"Starting deployment {deployment_id}: {image_tag} to {environment}"
        )

        # Create deployment result
        result = DeploymentResult(
            deployment_id=deployment_id,
            status=DeploymentStatus.PENDING,
            strategy=strategy.value
            if strategy
            else self.enterprise_config.deployment_strategy.value,
            environment=environment,
            image_tag=image_tag,
            monitoring_enabled=self.enterprise_config.enable_deployment_monitoring,
        )

        # Register deployment
        self.active_deployments[deployment_id] = result

        try:
            # Get deployment strategy
            deployment_strategy = get_deployment_strategy(strategy, config)
            result.strategy = deployment_strategy.name

            # Update status
            result.status = DeploymentStatus.IN_PROGRESS

            # Execute deployment
            logger.info(
                f"Executing {deployment_strategy.name} deployment for {deployment_id}"
            )

            metrics = await deployment_strategy.deploy(
                deployment_id=deployment_id,
                image_tag=image_tag,
                environment=environment,
                config=config or {},
            )

            result.metrics = metrics

            # Determine final status
            if metrics.phase == DeploymentPhase.COMPLETED:
                result.status = DeploymentStatus.COMPLETED
                result.success = True
                logger.info(f"Deployment {deployment_id} completed successfully")
            else:
                result.status = DeploymentStatus.FAILED
                result.error_message = f"Deployment failed in phase: {metrics.phase}"
                logger.error(
                    f"Deployment {deployment_id} failed in phase: {metrics.phase}"
                )

                # Auto-rollback if enabled and not already rolled back
                if (
                    self.enterprise_config.enable_auto_rollback
                    and metrics.phase != DeploymentPhase.ROLLING_BACK
                ):
                    logger.info(
                        f"Triggering auto-rollback for deployment {deployment_id}"
                    )
                    result.auto_rollback_triggered = True

                    rollback_result = await self.rollback(
                        deployment_id=deployment_id,
                        previous_version="previous",
                        reason="Auto-rollback due to deployment failure",
                    )

                    if rollback_result.success:
                        result.status = DeploymentStatus.ROLLED_BACK
                        logger.info(
                            f"Auto-rollback successful for deployment {deployment_id}"
                        )
                    else:
                        logger.error(
                            f"Auto-rollback failed for deployment {deployment_id}"
                        )

            result.end_time = time.time()

            # Move to history
            self.deployment_history.append(result)
            if deployment_id in self.active_deployments:
                del self.active_deployments[deployment_id]

            return result

        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed with exception: {e}")

            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()

            # Move to history
            self.deployment_history.append(result)
            if deployment_id in self.active_deployments:
                del self.active_deployments[deployment_id]

            return result

    async def rollback(
        self,
        deployment_id: str,
        previous_version: str,
        reason: str = "Manual rollback",
    ) -> DeploymentResult:
        """Rollback a deployment to the previous version.

        Args:
            deployment_id: ID of deployment to rollback
            previous_version: Previous version to rollback to
            reason: Reason for rollback

        Returns:
            DeploymentResult for rollback operation
        """
        logger.info(f"Rolling back deployment {deployment_id}: {reason}")

        # Find the deployment to rollback
        deployment = None
        if deployment_id in self.active_deployments:
            deployment = self.active_deployments[deployment_id]
        else:
            # Check history
            for hist_deployment in self.deployment_history:
                if hist_deployment.deployment_id == deployment_id:
                    deployment = hist_deployment
                    break

        if not deployment:
            error_msg = f"Deployment {deployment_id} not found"
            logger.error(error_msg)
            return DeploymentResult(
                deployment_id=f"{deployment_id}_rollback",
                status=DeploymentStatus.FAILED,
                strategy="rollback",
                environment="unknown",
                image_tag=previous_version,
                error_message=error_msg,
                end_time=time.time(),
            )

        try:
            # Get the same strategy used for original deployment
            deployment_strategy = get_deployment_strategy(
                DeploymentStrategy(deployment.strategy)
            )

            logger.info(
                f"Executing {deployment_strategy.name} rollback for {deployment_id}"
            )

            # Execute rollback
            rollback_metrics = await deployment_strategy.rollback(
                deployment_id=deployment_id,
                previous_version=previous_version,
                environment=deployment.environment,
            )

            # Create rollback result
            rollback_result = DeploymentResult(
                deployment_id=f"{deployment_id}_rollback",
                status=DeploymentStatus.COMPLETED
                if rollback_metrics.phase == DeploymentPhase.COMPLETED
                else DeploymentStatus.FAILED,
                strategy=f"{deployment_strategy.name}_rollback",
                environment=deployment.environment,
                image_tag=previous_version,
                success=rollback_metrics.phase == DeploymentPhase.COMPLETED,
                end_time=time.time(),
                metrics=rollback_metrics,
            )

            # Update original deployment with rollback info
            deployment.rollback_metrics = rollback_metrics

            return rollback_result

        except Exception as e:
            logger.error(f"Rollback {deployment_id} failed with exception: {e}")

            return DeploymentResult(
                deployment_id=f"{deployment_id}_rollback",
                status=DeploymentStatus.FAILED,
                strategy="rollback",
                environment=deployment.environment,
                image_tag=previous_version,
                error_message=str(e),
                end_time=time.time(),
            )

    async def get_deployment_status(
        self, deployment_id: str
    ) -> Optional[DeploymentResult]:
        """Get status of a specific deployment.

        Args:
            deployment_id: ID of deployment to check

        Returns:
            DeploymentResult if found, None otherwise
        """
        # Check active deployments first
        if deployment_id in self.active_deployments:
            return self.active_deployments[deployment_id]

        # Check history
        for deployment in self.deployment_history:
            if deployment.deployment_id == deployment_id:
                return deployment

        return None

    async def list_active_deployments(self) -> List[DeploymentResult]:
        """Get list of currently active deployments.

        Returns:
            List of active DeploymentResult objects
        """
        return list(self.active_deployments.values())

    async def get_deployment_history(
        self,
        environment: Optional[str] = None,
        limit: int = 50,
    ) -> List[DeploymentResult]:
        """Get deployment history with optional filtering.

        Args:
            environment: Filter by environment (optional)
            limit: Maximum number of deployments to return

        Returns:
            List of historical DeploymentResult objects
        """
        history = self.deployment_history

        if environment:
            history = [d for d in history if d.environment == environment]

        # Return most recent first
        return sorted(history, key=lambda x: x.start_time, reverse=True)[:limit]

    async def get_deployment_statistics(self) -> Dict[str, Any]:
        """Get deployment statistics for monitoring and reporting.

        Returns:
            Dictionary with deployment statistics
        """
        total_deployments = len(self.deployment_history)

        if total_deployments == 0:
            return {
                "total_deployments": 0,
                "success_rate": 0.0,
                "active_deployments": len(self.active_deployments),
                "strategies": {},
                "environments": {},
            }

        successful_deployments = sum(1 for d in self.deployment_history if d.success)
        success_rate = successful_deployments / total_deployments

        # Strategy distribution
        strategy_counts = {}
        for deployment in self.deployment_history:
            strategy_counts[deployment.strategy] = (
                strategy_counts.get(deployment.strategy, 0) + 1
            )

        # Environment distribution
        env_counts = {}
        for deployment in self.deployment_history:
            env_counts[deployment.environment] = (
                env_counts.get(deployment.environment, 0) + 1
            )

        # Auto-rollback statistics
        auto_rollbacks = sum(
            1 for d in self.deployment_history if d.auto_rollback_triggered
        )

        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "failed_deployments": total_deployments - successful_deployments,
            "success_rate": round(success_rate * 100, 2),
            "active_deployments": len(self.active_deployments),
            "auto_rollbacks": auto_rollbacks,
            "auto_rollback_rate": round((auto_rollbacks / total_deployments) * 100, 2)
            if total_deployments > 0
            else 0,
            "strategies": strategy_counts,
            "environments": env_counts,
            "enterprise_features": {
                "monitoring_enabled": (
                    self.enterprise_config.enable_deployment_monitoring
                ),
                "auto_rollback_enabled": self.enterprise_config.enable_auto_rollback,
                "canary_analysis_enabled": (
                    self.enterprise_config.enable_canary_analysis
                ),
            },
        }

    async def monitor_deployment(
        self,
        deployment_id: str,
        check_interval: float = 10.0,
        max_duration: float = 300.0,
    ) -> None:
        """Monitor an active deployment with periodic health checks.

        Args:
            deployment_id: ID of deployment to monitor
            check_interval: Interval between health checks in seconds
            max_duration: Maximum monitoring duration in seconds
        """
        if not self.enterprise_config.enable_deployment_monitoring:
            logger.debug("Deployment monitoring is disabled")
            return

        deployment = await self.get_deployment_status(deployment_id)
        if not deployment:
            logger.warning(f"Deployment {deployment_id} not found for monitoring")
            return

        logger.info(f"Starting monitoring for deployment {deployment_id}")

        start_time = time.time()

        while time.time() - start_time < max_duration:
            # Check if deployment is still active
            if deployment_id not in self.active_deployments:
                logger.info(
                    f"Deployment {deployment_id} completed, stopping monitoring"
                )
                break

            # Perform monitoring checks
            try:
                # This would integrate with actual monitoring systems
                # For now, we'll simulate monitoring
                await asyncio.sleep(check_interval)

                logger.debug(f"Monitoring check for deployment {deployment_id}")

                # Check deployment status
                current_deployment = self.active_deployments.get(deployment_id)
                if (
                    current_deployment
                    and current_deployment.status == DeploymentStatus.FAILED
                ):
                    logger.warning(
                        f"Deployment {deployment_id} failed, stopping monitoring"
                    )
                    break

            except Exception as e:
                logger.error(f"Monitoring error for deployment {deployment_id}: {e}")
                break

        logger.info(f"Monitoring completed for deployment {deployment_id}")


# Global orchestrator instance
_orchestrator: Optional[ConfigurableDeploymentOrchestrator] = None


def get_deployment_orchestrator() -> ConfigurableDeploymentOrchestrator:
    """Get the global deployment orchestrator instance.

    Returns:
        Global ConfigurableDeploymentOrchestrator instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ConfigurableDeploymentOrchestrator()
    return _orchestrator
