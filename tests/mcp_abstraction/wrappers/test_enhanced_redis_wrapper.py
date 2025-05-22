"""
Tests for enhanced Redis MCP wrapper functionality (locking, pipelining, etc.).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the settings import to avoid configuration issues
with patch("tripsage.config.mcp_settings.mcp_settings"):
    from tripsage.mcp_abstraction.wrappers.official_redis_wrapper import (
        OfficialRedisMCPWrapper,
    )


class TestEnhancedRedisMCPWrapper:
    """Test enhanced Redis MCP wrapper functionality."""

    @pytest.fixture
    def wrapper(self):
        """Create a test wrapper with mocked config."""
        with patch("tripsage.config.mcp_settings.mcp_settings"):
            return OfficialRedisMCPWrapper()

    @pytest.mark.asyncio
    async def test_pipeline_execute_set_commands(self, wrapper):
        """Test pipeline execution with set commands."""
        with patch.object(wrapper, "cache_set") as mock_set:
            mock_set.return_value = True

            commands = [
                {"command": "set", "args": ["key1", "value1"], "kwargs": {"ttl": 300}},
                {"command": "set", "args": ["key2", "value2"], "kwargs": {"ex": 600}},
            ]

            results = await wrapper.pipeline_execute(commands)

            assert results == [True, True]
            assert mock_set.call_count == 2
            mock_set.assert_any_call("key1", "value1", 300)
            mock_set.assert_any_call("key2", "value2", 600)

    @pytest.mark.asyncio
    async def test_pipeline_execute_mixed_commands(self, wrapper):
        """Test pipeline execution with mixed commands."""
        with (
            patch.object(wrapper, "cache_set") as mock_set,
            patch.object(wrapper, "cache_get") as mock_get,
            patch.object(wrapper, "cache_delete") as mock_delete,
        ):
            mock_set.return_value = True
            mock_get.return_value = "cached_value"
            mock_delete.return_value = 1

            commands = [
                {"command": "set", "args": ["key1", "value1"]},
                {"command": "get", "args": ["key2"]},
                {"command": "delete", "args": ["key3"]},
                {"command": "unsupported", "args": ["key4"]},
            ]

            results = await wrapper.pipeline_execute(commands)

            assert results == [True, "cached_value", 1, None]
            mock_set.assert_called_once_with("key1", "value1", None)
            mock_get.assert_called_once_with("key2")
            mock_delete.assert_called_once_with("key3")

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, wrapper):
        """Test successful lock acquisition."""
        with (
            patch.object(wrapper, "cache_set") as mock_set,
            patch.object(wrapper, "cache_get") as mock_get,
        ):
            mock_set.return_value = True
            mock_get.return_value = "mock_token"

            # Mock uuid generation
            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value.return_value = "mock_token"
                mock_uuid.return_value.__str__ = lambda self: "mock_token"

                success, token = await wrapper.acquire_lock("test_lock", timeout=60)

                assert success is True
                assert token == "mock_token"
                mock_set.assert_called_once_with("lock:test_lock", "mock_token", 60)
                mock_get.assert_called_once_with("lock:test_lock")

    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self, wrapper):
        """Test failed lock acquisition."""
        with patch.object(wrapper, "cache_set") as mock_set:
            mock_set.return_value = False

            success, token = await wrapper.acquire_lock("test_lock", retry_count=2)

            assert success is False
            assert token == ""
            assert mock_set.call_count == 2  # Should retry

    @pytest.mark.asyncio
    async def test_acquire_lock_race_condition(self, wrapper):
        """Test lock acquisition with race condition."""
        with (
            patch.object(wrapper, "cache_set") as mock_set,
            patch.object(wrapper, "cache_get") as mock_get,
        ):
            mock_set.return_value = True
            mock_get.return_value = "different_token"  # Someone else got the lock

            with patch("uuid.uuid4") as mock_uuid:
                mock_uuid.return_value.__str__ = lambda self: "our_token"

                success, token = await wrapper.acquire_lock("test_lock", retry_count=1)

                assert success is False
                assert token == ""

    @pytest.mark.asyncio
    async def test_release_lock_success(self, wrapper):
        """Test successful lock release."""
        with (
            patch.object(wrapper, "cache_get") as mock_get,
            patch.object(wrapper, "cache_delete") as mock_delete,
        ):
            mock_get.return_value = "test_token"
            mock_delete.return_value = 1

            result = await wrapper.release_lock("test_lock", "test_token")

            assert result is True
            mock_get.assert_called_once_with("lock:test_lock")
            mock_delete.assert_called_once_with("lock:test_lock")

    @pytest.mark.asyncio
    async def test_release_lock_wrong_token(self, wrapper):
        """Test lock release with wrong token."""
        with patch.object(wrapper, "cache_get") as mock_get:
            mock_get.return_value = "different_token"

            result = await wrapper.release_lock("test_lock", "wrong_token")

            assert result is False

    @pytest.mark.asyncio
    async def test_extend_lock_success(self, wrapper):
        """Test successful lock extension."""
        with (
            patch.object(wrapper, "cache_get") as mock_get,
            patch.object(wrapper, "cache_set") as mock_set,
        ):
            mock_get.return_value = "test_token"
            mock_set.return_value = True

            result = await wrapper.extend_lock("test_lock", "test_token", 120)

            assert result is True
            mock_get.assert_called_once_with("lock:test_lock")
            mock_set.assert_called_once_with("lock:test_lock", "test_token", 120)

    @pytest.mark.asyncio
    async def test_extend_lock_wrong_token(self, wrapper):
        """Test lock extension with wrong token."""
        with patch.object(wrapper, "cache_get") as mock_get:
            mock_get.return_value = "different_token"

            result = await wrapper.extend_lock("test_lock", "wrong_token", 120)

            assert result is False

    @pytest.mark.asyncio
    async def test_prefetch_keys(self, wrapper):
        """Test key prefetching."""
        with (
            patch.object(wrapper, "cache_keys") as mock_keys,
            patch.object(wrapper, "cache_get") as mock_get,
        ):
            mock_keys.return_value = ["key1", "key2", "key3", "key4", "key5"]
            mock_get.side_effect = ["value1", "value2", None, "value4", "value5"]

            result = await wrapper.prefetch_keys("test:*", limit=3)

            assert result == 2  # Only key1 and key2 had values (key3 was None)
            mock_keys.assert_called_once_with("test:*")
            assert mock_get.call_count == 3  # Limited to 3 keys

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, wrapper):
        """Test pattern invalidation."""
        with (
            patch.object(wrapper, "cache_keys") as mock_keys,
            patch.object(wrapper, "cache_delete") as mock_delete,
        ):
            mock_keys.return_value = ["pattern:key1", "pattern:key2"]
            mock_delete.return_value = 2

            result = await wrapper.invalidate_pattern("pattern:*")

            assert result == 2
            mock_keys.assert_called_once_with("pattern:*")
            mock_delete.assert_called_once_with(["pattern:key1", "pattern:key2"])

    @pytest.mark.asyncio
    async def test_invalidate_pattern_no_keys(self, wrapper):
        """Test pattern invalidation with no matching keys."""
        with patch.object(wrapper, "cache_keys") as mock_keys:
            mock_keys.return_value = []

            result = await wrapper.invalidate_pattern("nonexistent:*")

            assert result == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self, wrapper):
        """Test error handling in pipeline execution."""
        with patch.object(wrapper, "cache_set") as mock_set:
            mock_set.side_effect = [True, Exception("Redis error"), True]

            commands = [
                {"command": "set", "args": ["key1", "value1"]},
                {"command": "set", "args": ["key2", "value2"]},
                {"command": "set", "args": ["key3", "value3"]},
            ]

            results = await wrapper.pipeline_execute(commands)

            assert results == [True, None, True]  # Middle command failed

    @pytest.mark.asyncio
    async def test_error_handling_in_lock_operations(self, wrapper):
        """Test error handling in lock operations."""
        with patch.object(wrapper, "cache_set") as mock_set:
            mock_set.side_effect = Exception("Redis error")

            success, token = await wrapper.acquire_lock("test_lock", retry_count=1)

            assert success is False
            assert token == ""

        with patch.object(wrapper, "cache_get") as mock_get:
            mock_get.side_effect = Exception("Redis error")

            result = await wrapper.release_lock("test_lock", "token")

            assert result is False

        with patch.object(wrapper, "cache_get") as mock_get:
            mock_get.side_effect = Exception("Redis error")

            result = await wrapper.extend_lock("test_lock", "token", 60)

            assert result is False
