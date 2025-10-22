#!/usr/bin/env python3
"""Script to verify DragonflyDB connection and configuration.

Run from project root: python scripts/verification/verify_dragonfly.py
"""

import asyncio
import sys
from pathlib import Path


# If running as a script, add project root to path
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.cache_service import CacheService


async def verify_dragonfly_connection():
    """Verify DragonflyDB is properly configured and accessible."""
    print("Verifying DragonflyDB Configuration...")

    try:
        # Get settings (flat structure)
        settings = get_settings()
        print("\nConfiguration:")
        print(f"   URL: {settings.redis_url}")
        pwd_status = "***" if settings.redis_password else "Not configured"
        print(f"   Password: {pwd_status}")
        print(f"   Max Connections: {settings.redis_max_connections}")
        # Note: DragonflyDB specific settings removed from flat config

        # Initialize cache service
        cache_service = CacheService(settings)

        print("\nAttempting to connect to DragonflyDB...")
        await cache_service.connect()

        print("✅ Successfully connected to DragonflyDB!")

        # Test basic operations
        print("\nTesting basic operations...")

        # Set a test value
        test_key = "dragonfly_test_key"
        test_value = {"status": "connected", "timestamp": "2025-06-04"}

        print(f"   Setting test value: {test_key} = {test_value}")
        await cache_service.set_json(test_key, test_value, ttl=60)

        # Get the test value
        retrieved = await cache_service.get_json(test_key)
        print(f"   Retrieved value: {retrieved}")

        if retrieved == test_value:
            print("   ✅ Read/Write operations working correctly!")
        else:
            print("   ❌ Read/Write operations failed!")
            return False

        # Delete the test value
        deleted = await cache_service.delete(test_key)
        print(f"   Deleted test key: {'✅' if deleted else '❌'}")

        # Show connection status
        print("\nCache Status:")
        print(f"   Connected: {cache_service.is_connected}")
        print("   ✅ All operations completed successfully!")

        # Disconnect
        await cache_service.disconnect()
        print("\n✅ DragonflyDB verification complete!")
        return True

    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Error: {e!s}")
        print("\nTroubleshooting tips:")
        print("   1. Ensure DragonflyDB container is running:")
        print("      docker-compose up -d dragonfly")
        print("   2. Check if port 6379 is available: lsof -i :6379")
        print("   3. Verify environment variables are set correctly")
        print("   4. Check docker logs: docker logs tripsage-dragonfly")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_dragonfly_connection())
    sys.exit(0 if success else 1)
