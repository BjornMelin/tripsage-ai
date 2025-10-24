"""Final-only tests for CacheService in disabled (no-redis) mode.

These tests validate behavior when `settings.redis_url` is None, which the
final implementation treats as disabled mode: operations are no-ops that
either succeed (set) or return defaults (get).
"""

from unittest.mock import Mock

import pytest

from tripsage_core.services.infrastructure.cache_service import CacheService


@pytest.fixture
def disabled_settings():
    """Create settings object with redis disabled (None URL)."""
    s = Mock()
    s.redis_url = None
    s.redis_password = None
    s.redis_max_connections = 5
    return s


@pytest.mark.asyncio
async def test_connect_disabled_mode(disabled_settings):
    """CacheService stays disconnected when redis_url is None."""
    svc = CacheService(disabled_settings)
    await svc.connect()
    assert svc.is_connected is False


@pytest.mark.asyncio
async def test_set_get_json_disabled_mode(disabled_settings):
    """set_json returns True and get_json returns default in disabled mode."""
    svc = CacheService(disabled_settings)

    ok = await svc.set_json("k", {"a": 1}, ttl=10)
    assert ok is True

    val = await svc.get_json("k", default={})
    assert val == {}


@pytest.mark.asyncio
async def test_set_get_string_disabled_mode(disabled_settings):
    """set/get string operations work as no-ops without redis."""
    svc = CacheService(disabled_settings)
    ok = await svc.set("k", "v", ttl=5)
    assert ok is True
    # No redis: get_json is the only reader; strings are not read in disabled mode
    val = await svc.get_json("k", default=None)
    assert val is None
