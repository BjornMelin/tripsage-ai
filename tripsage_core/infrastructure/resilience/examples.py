"""Examples demonstrating configurable circuit breaker patterns.

This module provides examples of how to use the configurable circuit breaker
with both simple and enterprise modes, showcasing the different behaviors
and capabilities.
"""

import asyncio
import os
import random
import time
from typing import Any, Dict

from tripsage_core.config import apply_preset, get_enterprise_config
from tripsage_core.infrastructure.resilience import (
    circuit_breaker,
    get_circuit_breaker_status,
)


class MockService:
    """Mock service that can simulate failures for testing circuit breakers."""

    def __init__(self, name: str, failure_rate: float = 0.3):
        self.name = name
        self.failure_rate = failure_rate
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def unreliable_operation(self, operation_id: str) -> Dict[str, Any]:
        """Simulate an unreliable operation that may fail."""
        self.call_count += 1

        # Simulate processing time
        await asyncio.sleep(0.1)

        # Randomly fail based on failure rate
        if random.random() < self.failure_rate:
            self.failure_count += 1
            raise ConnectionError(
                f"Service {self.name} failed for operation {operation_id}"
            )

        self.success_count += 1
        return {
            "service": self.name,
            "operation_id": operation_id,
            "timestamp": time.time(),
            "status": "success",
            "call_count": self.call_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "name": self.name,
            "total_calls": self.call_count,
            "successes": self.success_count,
            "failures": self.failure_count,
            "success_rate": self.success_count / self.call_count
            if self.call_count > 0
            else 0,
        }


async def demonstrate_simple_mode():
    """Demonstrate circuit breaker in simple mode."""
    print("\n=== SIMPLE MODE DEMONSTRATION ===")

    # Set enterprise config to simple mode
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "false"
    os.environ["ENTERPRISE_CIRCUIT_BREAKER_MODE"] = "simple"

    # Apply development preset
    apply_preset("development")

    # Create mock service
    service = MockService("simple_service", failure_rate=0.7)  # High failure rate

    # Create circuit breaker
    breaker = circuit_breaker(
        name="simple_demo",
        max_retries=2,
        base_delay=0.5,
        max_delay=2.0,
        exceptions=[ConnectionError],
    )

    # Decorate the service method
    @breaker
    async def protected_operation(operation_id: str):
        return await service.unreliable_operation(operation_id)

    print(f"Enterprise config mode: {get_enterprise_config().circuit_breaker_mode}")
    print("Circuit breaker type: Simple (retry with backoff)")

    # Make several calls to demonstrate behavior
    for i in range(10):
        try:
            result = await protected_operation(f"op_{i}")
            print(f"✅ Operation {i} succeeded: {result['status']}")
        except Exception as e:
            print(f"❌ Operation {i} failed: {type(e).__name__}: {e}")

        await asyncio.sleep(0.2)

    print(f"\nService stats: {service.get_stats()}")
    print(f"Circuit breaker stats: {breaker.metrics.get_summary()}")


async def demonstrate_enterprise_mode():
    """Demonstrate circuit breaker in enterprise mode."""
    print("\n=== ENTERPRISE MODE DEMONSTRATION ===")

    # Set enterprise config to enterprise mode
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "true"
    os.environ["ENTERPRISE_CIRCUIT_BREAKER_MODE"] = "enterprise"

    # Apply portfolio demo preset
    apply_preset("portfolio_demo")

    # Create mock service
    service = MockService(
        "enterprise_service", failure_rate=0.8
    )  # Very high failure rate

    # Create circuit breaker
    breaker = circuit_breaker(
        name="enterprise_demo",
        failure_threshold=3,  # Open after 3 failures
        success_threshold=2,  # Close after 2 successes
        timeout=5.0,  # Wait 5s before half-open
        max_retries=2,
        base_delay=0.5,
        exceptions=[ConnectionError],
    )

    # Decorate the service method
    @breaker
    async def protected_operation(operation_id: str):
        return await service.unreliable_operation(operation_id)

    print(f"Enterprise config mode: {get_enterprise_config().circuit_breaker_mode}")
    print("Circuit breaker type: Enterprise (state management)")
    print("Failure threshold: 3, Success threshold: 2, Timeout: 5s")

    # Make several calls to demonstrate circuit opening
    for i in range(15):
        try:
            result = await protected_operation(f"op_{i}")
            print(f"✅ Operation {i} succeeded: {result['status']}")
        except Exception as e:
            if "Circuit breaker" in str(e):
                print(f"🔴 Operation {i} blocked by circuit breaker: {e}")
            else:
                print(f"❌ Operation {i} failed: {type(e).__name__}: {e}")

        # Show circuit breaker state
        if hasattr(breaker, "get_state"):
            state = breaker.get_state()
            print(
                f"   Circuit state: {state['state']} (failures: {state['failure_count']}, successes: {state['success_count']})"
            )

        await asyncio.sleep(0.5)

    print(f"\nService stats: {service.get_stats()}")
    if hasattr(breaker, "get_state"):
        print(f"Circuit breaker state: {breaker.get_state()}")
    else:
        print(f"Circuit breaker stats: {breaker.metrics.get_summary()}")


async def demonstrate_recovery():
    """Demonstrate circuit breaker recovery in enterprise mode."""
    print("\n=== RECOVERY DEMONSTRATION ===")

    # Ensure enterprise mode
    os.environ["ENTERPRISE_ENABLE_ENTERPRISE_FEATURES"] = "true"
    os.environ["ENTERPRISE_CIRCUIT_BREAKER_MODE"] = "enterprise"

    # Create service that will recover
    service = MockService(
        "recovery_service", failure_rate=1.0
    )  # Start with 100% failure

    breaker = circuit_breaker(
        name="recovery_demo",
        failure_threshold=2,  # Open quickly
        success_threshold=2,  # Close after 2 successes
        timeout=3.0,  # Short timeout for demo
        max_retries=1,
        exceptions=[ConnectionError],
    )

    @breaker
    async def protected_operation(operation_id: str):
        return await service.unreliable_operation(operation_id)

    print("Phase 1: Triggering circuit breaker opening")

    # Trigger circuit opening
    for i in range(5):
        try:
            await protected_operation(f"fail_{i}")
        except Exception as e:
            print(f"❌ Operation fail_{i}: {type(e).__name__}")
            if hasattr(breaker, "get_state"):
                state = breaker.get_state()
                print(f"   Circuit state: {state['state']}")

    print("\nPhase 2: Circuit is open - calls will be blocked")

    # Show blocked calls
    for i in range(3):
        try:
            await protected_operation(f"blocked_{i}")
        except Exception as e:
            print(f"🔴 Operation blocked_{i}: {e}")

    print(f"\nPhase 3: Waiting for timeout ({breaker.timeout}s)...")
    await asyncio.sleep(breaker.timeout + 0.5)

    print("Phase 4: Service recovery - reducing failure rate")
    service.failure_rate = 0.1  # Much better success rate

    # Demonstrate recovery
    for i in range(8):
        try:
            await protected_operation(f"recovery_{i}")
            print(f"✅ Operation recovery_{i} succeeded")
        except Exception as e:
            print(f"❌ Operation recovery_{i} failed: {type(e).__name__}")

        if hasattr(breaker, "get_state"):
            state = breaker.get_state()
            print(
                f"   Circuit state: {state['state']} (failures: {state['failure_count']}, successes: {state['success_count']})"
            )

        await asyncio.sleep(0.5)

    print(f"\nFinal service stats: {service.get_stats()}")
    if hasattr(breaker, "get_state"):
        print(f"Final circuit state: {breaker.get_state()}")


async def main():
    """Run all demonstrations."""
    print("🔧 Configurable Circuit Breaker Demonstration")
    print("=" * 50)

    try:
        await demonstrate_simple_mode()
        await demonstrate_enterprise_mode()
        await demonstrate_recovery()

        print("\n=== GLOBAL CIRCUIT BREAKER STATUS ===")
        status = get_circuit_breaker_status()
        for name, state in status.items():
            print(f"{name}: {state}")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
