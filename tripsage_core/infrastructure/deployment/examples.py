"""Examples demonstrating configurable deployment strategies.

This module provides examples of how to use the configurable deployment
orchestrator with different strategies, showcasing the enterprise features
and deployment patterns.
"""

import asyncio
import os

from tripsage_core.config import apply_preset, get_enterprise_config
from tripsage_core.infrastructure.deployment import (
    ConfigurableDeploymentOrchestrator,
)


async def demonstrate_simple_deployment():
    """Demonstrate simple deployment strategy."""
    print("\n=== SIMPLE DEPLOYMENT DEMONSTRATION ===")

    # Configure for simple mode
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "false"
    os.environ["ENTERPRISE_DEPLOYMENT_STRATEGY"] = "simple"

    apply_preset("development")

    orchestrator = ConfigurableDeploymentOrchestrator()

    print(f"Enterprise mode: {get_enterprise_config().enable_enterprise_features}")
    print(f"Deployment strategy: {get_enterprise_config().deployment_strategy}")

    # Deploy with simple strategy
    result = await orchestrator.deploy(
        image_tag="tripsage:v1.2.3",
        environment="development",
        config={"replicas": 1},
    )

    print("\nDeployment Result:")
    print(f"  ID: {result.deployment_id}")
    print(f"  Status: {result.status}")
    print(f"  Strategy: {result.strategy}")
    print(f"  Duration: {result.get_duration():.2f}s")
    print(f"  Success: {result.success}")

    if result.metrics:
        print(f"  Phase: {result.metrics.phase}")
        print(f"  Health checks: {len(result.metrics.health_checks)}")
        print(f"  Success rate: {result.metrics.get_success_rate():.2%}")

    return result


async def demonstrate_blue_green_deployment():
    """Demonstrate blue-green deployment strategy."""
    print("\n=== BLUE-GREEN DEPLOYMENT DEMONSTRATION ===")

    # Configure for enterprise mode with blue-green
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "true"
    os.environ["ENTERPRISE_DEPLOYMENT_STRATEGY"] = "blue_green"
    os.environ["ENTERPRISE_ENABLE_AUTO_ROLLBACK"] = "true"
    os.environ["ENTERPRISE_ENABLE_DEPLOYMENT_MONITORING"] = "true"

    apply_preset("portfolio_demo")

    orchestrator = ConfigurableDeploymentOrchestrator()

    print(f"Enterprise mode: {get_enterprise_config().enable_enterprise_features}")
    print(f"Deployment strategy: {get_enterprise_config().deployment_strategy}")
    print(f"Auto-rollback: {get_enterprise_config().enable_auto_rollback}")

    # Deploy with blue-green strategy
    result = await orchestrator.deploy(
        image_tag="tripsage:v2.0.0",
        environment="production",
        config={
            "switch_delay": 3.0,
            "health_check_timeout": 30.0,
        },
    )

    print("\nBlue-Green Deployment Result:")
    print(f"  ID: {result.deployment_id}")
    print(f"  Status: {result.status}")
    print(f"  Strategy: {result.strategy}")
    print(f"  Duration: {result.get_duration():.2f}s")
    print(f"  Success: {result.success}")
    print(f"  Auto-rollback triggered: {result.auto_rollback_triggered}")
    print(f"  Monitoring enabled: {result.monitoring_enabled}")

    if result.metrics:
        print(f"  Final phase: {result.metrics.phase}")
        print(f"  Traffic percentage: {result.metrics.traffic_percentage}%")
        print(f"  Health checks: {len(result.metrics.health_checks)}")
        print(f"  Success rate: {result.metrics.get_success_rate():.2%}")

        # Show health check details
        if result.metrics.health_checks:
            latest_check = result.metrics.health_checks[-1]
            print(
                f"  Latest health check: {latest_check.healthy} ({latest_check.response_time:.3f}s)"
            )

    return result


async def demonstrate_canary_deployment():
    """Demonstrate canary deployment strategy."""
    print("\n=== CANARY DEPLOYMENT DEMONSTRATION ===")

    # Configure for enterprise mode with canary
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "true"
    os.environ["ENTERPRISE_DEPLOYMENT_STRATEGY"] = "canary"
    os.environ["ENTERPRISE_ENABLE_CANARY_ANALYSIS"] = "true"
    os.environ["ENTERPRISE_ENABLE_AUTO_ROLLBACK"] = "true"

    apply_preset("portfolio_demo")

    orchestrator = ConfigurableDeploymentOrchestrator()

    print(f"Enterprise mode: {get_enterprise_config().enable_enterprise_features}")
    print(f"Deployment strategy: {get_enterprise_config().deployment_strategy}")
    print(f"Canary analysis: {get_enterprise_config().enable_canary_analysis}")

    # Deploy with canary strategy
    result = await orchestrator.deploy(
        image_tag="tripsage:v2.1.0",
        environment="production",
        config={
            "canary_steps": [5, 15, 30, 50, 100],
            "step_duration": 2.0,
        },
    )

    print("\nCanary Deployment Result:")
    print(f"  ID: {result.deployment_id}")
    print(f"  Status: {result.status}")
    print(f"  Strategy: {result.strategy}")
    print(f"  Duration: {result.get_duration():.2f}s")
    print(f"  Success: {result.success}")
    print(f"  Auto-rollback triggered: {result.auto_rollback_triggered}")

    if result.metrics:
        print(f"  Final phase: {result.metrics.phase}")
        print(f"  Final traffic: {result.metrics.traffic_percentage}%")
        print(f"  Health checks: {len(result.metrics.health_checks)}")
        print(f"  Success rate: {result.metrics.get_success_rate():.2%}")

        # Show progression through canary steps
        print("  Canary progression:")
        for i, check in enumerate(result.metrics.health_checks):
            print(
                f"    Step {i + 1}: {'✅' if check.healthy else '❌'} ({check.response_time:.3f}s)"
            )

    return result


async def demonstrate_rolling_deployment():
    """Demonstrate rolling deployment strategy."""
    print("\n=== ROLLING DEPLOYMENT DEMONSTRATION ===")

    # Configure for enterprise mode with rolling
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "true"
    os.environ["ENTERPRISE_DEPLOYMENT_STRATEGY"] = "rolling"
    os.environ["ENTERPRISE_ENABLE_AUTO_ROLLBACK"] = "true"

    apply_preset("portfolio_demo")

    orchestrator = ConfigurableDeploymentOrchestrator()

    print(f"Enterprise mode: {get_enterprise_config().enable_enterprise_features}")
    print(f"Deployment strategy: {get_enterprise_config().deployment_strategy}")

    # Deploy with rolling strategy
    result = await orchestrator.deploy(
        image_tag="tripsage:v2.2.0",
        environment="production",
        config={
            "instance_count": 5,
            "update_delay": 1.5,
        },
    )

    print("\nRolling Deployment Result:")
    print(f"  ID: {result.deployment_id}")
    print(f"  Status: {result.status}")
    print(f"  Strategy: {result.strategy}")
    print(f"  Duration: {result.get_duration():.2f}s")
    print(f"  Success: {result.success}")

    if result.metrics:
        print(f"  Final phase: {result.metrics.phase}")
        print(f"  Instances deployed: {result.metrics.instances_deployed}")
        print(f"  Instances healthy: {result.metrics.instances_healthy}")
        print(f"  Final traffic: {result.metrics.traffic_percentage}%")
        print(f"  Health checks: {len(result.metrics.health_checks)}")
        print(f"  Success rate: {result.metrics.get_success_rate():.2%}")

    return result


async def demonstrate_rollback_scenario():
    """Demonstrate rollback scenario with failed deployment."""
    print("\n=== ROLLBACK SCENARIO DEMONSTRATION ===")

    # Configure enterprise mode with auto-rollback
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "true"
    os.environ["ENTERPRISE_DEPLOYMENT_STRATEGY"] = "blue_green"
    os.environ["ENTERPRISE_ENABLE_AUTO_ROLLBACK"] = "true"

    apply_preset("portfolio_demo")

    orchestrator = ConfigurableDeploymentOrchestrator()

    print("Simulating deployment that will trigger auto-rollback...")

    # This deployment has a higher chance of failure to demonstrate rollback
    # In real scenarios, failures would be due to actual health check failures
    result = await orchestrator.deploy(
        image_tag="tripsage:v2.3.0-buggy",
        environment="production",
        config={
            "switch_delay": 2.0,
            "simulate_failure": True,  # This would be handled by health checks
        },
    )

    print("\nDeployment with Rollback Result:")
    print(f"  ID: {result.deployment_id}")
    print(f"  Status: {result.status}")
    print(f"  Strategy: {result.strategy}")
    print(f"  Duration: {result.get_duration():.2f}s")
    print(f"  Success: {result.success}")
    print(f"  Auto-rollback triggered: {result.auto_rollback_triggered}")

    if result.rollback_metrics:
        print(f"  Rollback phase: {result.rollback_metrics.phase}")
        print(f"  Rollback duration: {result.rollback_metrics.get_duration():.2f}s")
        print(
            f"  Rollback success: {result.rollback_metrics.phase.value == 'completed'}"
        )

    # Demonstrate manual rollback
    if not result.auto_rollback_triggered:
        print("\nDemonstrating manual rollback...")
        rollback_result = await orchestrator.rollback(
            deployment_id=result.deployment_id,
            previous_version="tripsage:v2.0.0",
            reason="Manual rollback due to performance issues",
        )

        print("Manual Rollback Result:")
        print(f"  ID: {rollback_result.deployment_id}")
        print(f"  Status: {rollback_result.status}")
        print(f"  Success: {rollback_result.success}")

    return result


async def demonstrate_deployment_monitoring():
    """Demonstrate deployment monitoring and statistics."""
    print("\n=== DEPLOYMENT MONITORING DEMONSTRATION ===")

    orchestrator = ConfigurableDeploymentOrchestrator()

    # Show deployment statistics
    stats = await orchestrator.get_deployment_statistics()

    print("Deployment Statistics:")
    print(f"  Total deployments: {stats['total_deployments']}")
    print(f"  Success rate: {stats['success_rate']}%")
    print(f"  Active deployments: {stats['active_deployments']}")
    print(f"  Auto-rollback rate: {stats['auto_rollback_rate']}%")

    print("\nStrategy Distribution:")
    for strategy, count in stats["strategies"].items():
        print(f"  {strategy}: {count}")

    print("\nEnvironment Distribution:")
    for env, count in stats["environments"].items():
        print(f"  {env}: {count}")

    print("\nEnterprise Features:")
    for feature, enabled in stats["enterprise_features"].items():
        print(f"  {feature}: {'✅' if enabled else '❌'}")

    # Show deployment history
    history = await orchestrator.get_deployment_history(limit=5)

    print("\nRecent Deployment History:")
    for deployment in history:
        duration = deployment.get_duration()
        status_emoji = "✅" if deployment.success else "❌"
        print(
            f"  {status_emoji} {deployment.deployment_id}: {deployment.strategy} → {deployment.environment} ({duration:.1f}s)"
        )


async def main():
    """Run all deployment demonstrations."""
    print("🚀 Configurable Deployment Strategy Demonstration")
    print("=" * 60)

    try:
        # Run different deployment strategies
        await demonstrate_simple_deployment()
        await demonstrate_blue_green_deployment()
        await demonstrate_canary_deployment()
        await demonstrate_rolling_deployment()

        # Demonstrate rollback scenarios
        await demonstrate_rollback_scenario()

        # Show monitoring and statistics
        await demonstrate_deployment_monitoring()

        print("\n" + "=" * 60)
        print("✅ All deployment demonstrations completed successfully!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
