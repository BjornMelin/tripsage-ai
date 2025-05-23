"""
Simple tests for the official Redis MCP wrapper (no complex settings dependencies).
"""

from unittest.mock import patch

import pytest

# Mock the settings import to avoid configuration issues
with patch("tripsage.config.mcp_settings.mcp_settings"):
    from tripsage.mcp_abstraction.wrappers.official_redis_wrapper import (
        OfficialRedisMCPClient,
        OfficialRedisMCPWrapper,
        RedisCacheStats,
    )


class TestOfficialRedisMCPClientSimple:
    """Simple test for the official Redis MCP client."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked config."""
        with patch("tripsage.config.mcp_settings.mcp_settings"):
            return OfficialRedisMCPClient()

    @pytest.mark.asyncio
    async def test_set_operation(self, client):
        """Test set operation."""
        with patch(
            "tripsage.mcp_abstraction.manager.mcp_manager.invoke"
        ) as mock_invoke:
            mock_invoke.return_value = {"success": True}

            result = await client.set("test_key", "test_value", 300)

            assert result is True
            assert client.stats.operations["sets"] == 1

    @pytest.mark.asyncio
    async def test_get_operation_success(self, client):
        """Test successful get operation."""
        with patch(
            "tripsage.mcp_abstraction.manager.mcp_manager.invoke"
        ) as mock_invoke:
            mock_invoke.return_value = {"value": "test_value"}

            result = await client.get("test_key")

            assert result == "test_value"
            assert client.stats.operations["gets"] == 1

    @pytest.mark.asyncio
    async def test_get_operation_not_found(self, client):
        """Test get operation for non-existent key."""
        with patch(
            "tripsage.mcp_abstraction.manager.mcp_manager.invoke"
        ) as mock_invoke:
            mock_invoke.return_value = {}

            result = await client.get("nonexistent_key")

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_operation(self, client):
        """Test delete operation."""
        with patch(
            "tripsage.mcp_abstraction.manager.mcp_manager.invoke"
        ) as mock_invoke:
            mock_invoke.return_value = {"deletedCount": 1}

            result = await client.delete("test_key")

            assert result == 1
            assert client.stats.operations["deletes"] == 1

    @pytest.mark.asyncio
    async def test_list_keys_operation(self, client):
        """Test list keys operation."""
        with patch(
            "tripsage.mcp_abstraction.manager.mcp_manager.invoke"
        ) as mock_invoke:
            mock_invoke.return_value = {"keys": ["key1", "key2"]}

            result = await client.list_keys("test:*")

            assert result == ["key1", "key2"]
            assert client.stats.total_keys == 2


class TestOfficialRedisMCPWrapperSimple:
    """Simple test for the official Redis MCP wrapper."""

    @pytest.fixture
    def wrapper(self):
        """Create a test wrapper with mocked config."""
        with patch("tripsage.config.mcp_settings.mcp_settings"):
            return OfficialRedisMCPWrapper()

    @pytest.mark.asyncio
    async def test_cache_set_string(self, wrapper):
        """Test cache set with string value."""
        with patch.object(wrapper._client, "set") as mock_set:
            mock_set.return_value = True

            result = await wrapper.cache_set("test_key", "test_value", 300)

            assert result is True
            mock_set.assert_called_once_with("test_key", "test_value", 300)

    @pytest.mark.asyncio
    async def test_cache_set_dict(self, wrapper):
        """Test cache set with dictionary value."""
        with patch.object(wrapper._client, "set") as mock_set:
            mock_set.return_value = True

            test_dict = {"key": "value", "number": 42}
            result = await wrapper.cache_set("test_key", test_dict)

            assert result is True
            # Should serialize dict to JSON
            mock_set.assert_called_once()
            args = mock_set.call_args[0]
            assert args[0] == "test_key"
            assert '"key": "value"' in args[1]

    @pytest.mark.asyncio
    async def test_cache_get_json(self, wrapper):
        """Test cache get with JSON value."""
        with patch.object(wrapper._client, "get") as mock_get:
            mock_get.return_value = '{"key": "value", "number": 42}'

            result = await wrapper.cache_get("test_key")

            assert result == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_cache_get_string(self, wrapper):
        """Test cache get with plain string value."""
        with patch.object(wrapper._client, "get") as mock_get:
            mock_get.return_value = "plain_string"

            result = await wrapper.cache_get("test_key")

            assert result == "plain_string"

    @pytest.mark.asyncio
    async def test_cache_exists(self, wrapper):
        """Test cache exists functionality."""
        # Test exists = True
        with patch.object(wrapper._client, "get") as mock_get:
            mock_get.return_value = "some_value"
            result = await wrapper.cache_exists("test_key")
            assert result is True

        # Test exists = False
        with patch.object(wrapper._client, "get") as mock_get:
            mock_get.return_value = None
            result = await wrapper.cache_exists("test_key")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, wrapper):
        """Test get cache statistics."""
        mock_stats = RedisCacheStats(
            total_keys=10, operations={"gets": 100, "sets": 50, "deletes": 5}
        )

        with patch.object(wrapper._client, "get_stats") as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            result = await wrapper.get_cache_stats()

            assert result["total_keys"] == 10
            assert result["operations"]["gets"] == 100
            assert result["server_type"] == "official_redis_mcp"


def test_redis_cache_stats_model():
    """Test RedisCacheStats model."""
    stats = RedisCacheStats()
    assert stats.total_keys == 0
    assert stats.operations["gets"] == 0
    assert stats.operations["sets"] == 0
    assert stats.operations["deletes"] == 0

    # Test with custom values
    stats = RedisCacheStats(
        total_keys=100, operations={"gets": 50, "sets": 25, "deletes": 10}
    )
    assert stats.total_keys == 100
    assert stats.operations["gets"] == 50
