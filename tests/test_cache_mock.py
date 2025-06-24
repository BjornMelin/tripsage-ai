"""
Mock cache service for testing to avoid DragonflyDB connection issues.

This module provides a mock implementation of the CacheService that can be used
in tests without requiring a real DragonflyDB connection.
"""

import json
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock


class MockCacheService:
    """Mock implementation of CacheService for testing."""

    def __init__(self):
        """Initialize the mock cache service."""
        self._storage: Dict[str, str] = {}
        self._ttls: Dict[str, float] = {}
        self._is_connected = True
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.health_check = AsyncMock(return_value=True)

    @property
    def is_connected(self) -> bool:
        """Mock connected status."""
        return self._is_connected

    async def ensure_connected(self) -> None:
        """Mock ensure connected."""
        pass

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Mock set_json."""
        self._storage[key] = json.dumps(value)
        if ttl:
            self._ttls[key] = ttl
        return True

    async def get_json(self, key: str) -> Optional[Any]:
        """Mock get_json."""
        if key in self._storage:
            return json.loads(self._storage[key])
        return None

    async def delete(self, *keys: str) -> int:
        """Mock delete."""
        count = 0
        for key in keys:
            if key in self._storage:
                del self._storage[key]
                if key in self._ttls:
                    del self._ttls[key]
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        """Mock exists."""
        return sum(1 for key in keys if key in self._storage)

    async def expire(self, key: str, ttl: int) -> bool:
        """Mock expire."""
        if key in self._storage:
            self._ttls[key] = ttl
            return True
        return False

    async def ttl(self, key: str) -> int:
        """Mock ttl."""
        return int(self._ttls.get(key, -1))

    async def keys(self, pattern: str = "*") -> List[str]:
        """Mock keys."""
        if pattern == "*":
            return list(self._storage.keys())
        # Simple pattern matching for tests
        import fnmatch

        return [k for k in self._storage.keys() if fnmatch.fnmatch(k, pattern)]

    async def delete_pattern(self, pattern: str) -> int:
        """Mock delete_pattern."""
        keys = await self.keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0

    async def flushdb(self) -> bool:
        """Mock flushdb."""
        self._storage.clear()
        self._ttls.clear()
        return True

    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Mock info."""
        return {
            "server": {"version": "mock-1.0.0"},
            "clients": {"connected_clients": 1},
            "memory": {"used_memory": len(str(self._storage))},
        }

    # Convenience methods
    async def set_short(self, key: str, value: Any) -> bool:
        """Mock set_short."""
        return await self.set_json(key, value, ttl=300)

    async def set_medium(self, key: str, value: Any) -> bool:
        """Mock set_medium."""
        return await self.set_json(key, value, ttl=3600)

    async def set_long(self, key: str, value: Any) -> bool:
        """Mock set_long."""
        return await self.set_json(key, value, ttl=86400)

    # Batch operations
    async def mget_json(self, keys: List[str]) -> List[Optional[Any]]:
        """Mock mget_json."""
        return [await self.get_json(key) for key in keys]

    async def mset_json(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Mock mset_json."""
        for key, value in mapping.items():
            await self.set_json(key, value, ttl)
        return True

    # Additional methods for compatibility
    async def set(
        self, key: str, value: Union[str, bytes], ttl: Optional[int] = None
    ) -> bool:
        """Mock set method."""
        self._storage[key] = value if isinstance(value, str) else value.decode("utf-8")
        if ttl:
            self._ttls[key] = ttl
        return True

    async def get(self, key: str) -> Optional[Union[str, bytes]]:
        """Mock get method."""
        return self._storage.get(key)

    async def incr(self, key: str) -> int:
        """Mock incr method."""
        current = int(self._storage.get(key, "0"))
        new_value = current + 1
        self._storage[key] = str(new_value)
        return new_value


def create_mock_cache_service():
    """Create a mock cache service instance."""
    return MockCacheService()


async def mock_get_cache_service():
    """Mock get_cache_service function that returns a mock instance."""
    return create_mock_cache_service()
