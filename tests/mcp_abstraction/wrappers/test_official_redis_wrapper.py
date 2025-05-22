"""
Tests for the official Redis MCP wrapper.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tripsage.mcp_abstraction.wrappers.official_redis_wrapper import (
    OfficialRedisMCPWrapper,
    OfficialRedisMCPClient,
    RedisCacheStats,
)


class TestOfficialRedisMCPClient:
    """Test the official Redis MCP client."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return OfficialRedisMCPClient()

    @pytest.mark.asyncio
    async def test_connect(self, client):
        """Test client connection."""
        await client.connect()
        # Connection is handled by MCP manager, so this should succeed
        assert True

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Test client disconnection."""
        await client.disconnect()
        # Disconnection is handled by MCP manager, so this should succeed
        assert True

    @pytest.mark.asyncio
    async def test_set_success(self, client):
        """Test successful set operation."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"success": True}
            
            result = await client.set("test_key", "test_value", 300)
            
            assert result is True
            assert client.stats.operations["sets"] == 1
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="set",
                key="test_key",
                value="test_value",
                expireSeconds=300
            )

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, client):
        """Test set operation without TTL."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"success": True}
            
            result = await client.set("test_key", "test_value")
            
            assert result is True
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="set",
                key="test_key",
                value="test_value"
            )

    @pytest.mark.asyncio
    async def test_get_success(self, client):
        """Test successful get operation."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"value": "test_value"}
            
            result = await client.get("test_key")
            
            assert result == "test_value"
            assert client.stats.operations["gets"] == 1
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="get",
                key="test_key"
            )

    @pytest.mark.asyncio
    async def test_get_not_found(self, client):
        """Test get operation for non-existent key."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {}
            
            result = await client.get("nonexistent_key")
            
            assert result is None
            assert client.stats.operations["gets"] == 1

    @pytest.mark.asyncio
    async def test_get_error(self, client):
        """Test get operation with error."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.side_effect = Exception("Redis error")
            
            result = await client.get("test_key")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_single_key(self, client):
        """Test delete operation with single key."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"deletedCount": 1}
            
            result = await client.delete("test_key")
            
            assert result == 1
            assert client.stats.operations["deletes"] == 1
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="delete",
                key="test_key"
            )

    @pytest.mark.asyncio
    async def test_delete_multiple_keys(self, client):
        """Test delete operation with multiple keys."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"deletedCount": 2}
            
            keys = ["key1", "key2"]
            result = await client.delete(keys)
            
            assert result == 2
            assert client.stats.operations["deletes"] == 2
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="delete",
                key=keys
            )

    @pytest.mark.asyncio
    async def test_list_keys(self, client):
        """Test list keys operation."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"keys": ["key1", "key2", "key3"]}
            
            result = await client.list_keys("test:*")
            
            assert result == ["key1", "key2", "key3"]
            assert client.stats.total_keys == 3
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="list",
                pattern="test:*"
            )

    @pytest.mark.asyncio
    async def test_list_keys_default_pattern(self, client):
        """Test list keys with default pattern."""
        with patch('tripsage.mcp_abstraction.manager.mcp_manager.invoke') as mock_invoke:
            mock_invoke.return_value = {"keys": ["key1"]}
            
            result = await client.list_keys()
            
            assert result == ["key1"]
            mock_invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="list",
                pattern="*"
            )

    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        """Test get statistics."""
        # Set some initial stats
        client.stats.operations["sets"] = 5
        client.stats.operations["gets"] = 10
        
        with patch.object(client, 'list_keys') as mock_list:
            mock_list.return_value = ["key1", "key2"]
            
            stats = await client.get_stats()
            
            assert isinstance(stats, RedisCacheStats)
            assert stats.total_keys == 2
            assert stats.operations["sets"] == 5
            assert stats.operations["gets"] == 10


class TestOfficialRedisMCPWrapper:
    """Test the official Redis MCP wrapper."""

    @pytest.fixture
    def wrapper(self):
        """Create a test wrapper."""
        return OfficialRedisMCPWrapper()

    @pytest.mark.asyncio
    async def test_initialize_success(self, wrapper):
        """Test successful initialization."""
        with patch.object(wrapper._client, 'connect') as mock_connect:
            mock_connect.return_value = None
            
            result = await wrapper.initialize()
            
            assert result is True
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_failure(self, wrapper):
        """Test initialization failure."""
        with patch.object(wrapper._client, 'connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = await wrapper.initialize()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_cleanup(self, wrapper):
        """Test cleanup."""
        with patch.object(wrapper._client, 'disconnect') as mock_disconnect:
            await wrapper.cleanup()
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_set_string(self, wrapper):
        """Test cache set with string value."""
        with patch.object(wrapper._client, 'set') as mock_set:
            mock_set.return_value = True
            
            result = await wrapper.cache_set("test_key", "test_value", 300)
            
            assert result is True
            mock_set.assert_called_once_with("test_key", "test_value", 300)

    @pytest.mark.asyncio
    async def test_cache_set_dict(self, wrapper):
        """Test cache set with dictionary value."""
        with patch.object(wrapper._client, 'set') as mock_set:
            mock_set.return_value = True
            
            test_dict = {"key": "value", "number": 42}
            result = await wrapper.cache_set("test_key", test_dict)
            
            assert result is True
            # Should serialize dict to JSON
            mock_set.assert_called_once()
            args = mock_set.call_args[0]
            assert args[0] == "test_key"
            assert '"key": "value"' in args[1]
            assert '"number": 42' in args[1]

    @pytest.mark.asyncio
    async def test_cache_get_json(self, wrapper):
        """Test cache get with JSON value."""
        with patch.object(wrapper._client, 'get') as mock_get:
            mock_get.return_value = '{"key": "value", "number": 42}'
            
            result = await wrapper.cache_get("test_key")
            
            assert result == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_cache_get_string(self, wrapper):
        """Test cache get with plain string value."""
        with patch.object(wrapper._client, 'get') as mock_get:
            mock_get.return_value = "plain_string"
            
            result = await wrapper.cache_get("test_key")
            
            assert result == "plain_string"

    @pytest.mark.asyncio
    async def test_cache_exists_true(self, wrapper):
        """Test cache exists returns True."""
        with patch.object(wrapper._client, 'get') as mock_get:
            mock_get.return_value = "some_value"
            
            result = await wrapper.cache_exists("test_key")
            
            assert result is True

    @pytest.mark.asyncio
    async def test_cache_exists_false(self, wrapper):
        """Test cache exists returns False."""
        with patch.object(wrapper._client, 'get') as mock_get:
            mock_get.return_value = None
            
            result = await wrapper.cache_exists("test_key")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_cache_clear_pattern(self, wrapper):
        """Test cache clear by pattern."""
        with patch.object(wrapper._client, 'list_keys') as mock_list:
            with patch.object(wrapper._client, 'delete') as mock_delete:
                mock_list.return_value = ["test:key1", "test:key2"]
                mock_delete.return_value = 2
                
                result = await wrapper.cache_clear_pattern("test:*")
                
                assert result == 2
                mock_list.assert_called_once_with("test:*")
                mock_delete.assert_called_once_with(["test:key1", "test:key2"])

    @pytest.mark.asyncio
    async def test_cache_clear_pattern_no_keys(self, wrapper):
        """Test cache clear by pattern with no matching keys."""
        with patch.object(wrapper._client, 'list_keys') as mock_list:
            mock_list.return_value = []
            
            result = await wrapper.cache_clear_pattern("test:*")
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, wrapper):
        """Test get cache statistics."""
        mock_stats = RedisCacheStats(
            total_keys=10,
            operations={"gets": 100, "sets": 50, "deletes": 5}
        )
        
        with patch.object(wrapper._client, 'get_stats') as mock_get_stats:
            mock_get_stats.return_value = mock_stats
            
            result = await wrapper.get_cache_stats()
            
            assert result["total_keys"] == 10
            assert result["operations"]["gets"] == 100
            assert result["operations"]["sets"] == 50
            assert result["operations"]["deletes"] == 5
            assert result["server_type"] == "official_redis_mcp"

    @pytest.mark.asyncio
    async def test_redis_tools_passthrough(self, wrapper):
        """Test direct Redis tool methods."""
        # Test redis_set
        with patch.object(wrapper._client, 'set') as mock_set:
            mock_set.return_value = True
            result = await wrapper.redis_set("key", "value", 300)
            assert result is True
            mock_set.assert_called_once_with("key", "value", 300)

        # Test redis_get
        with patch.object(wrapper._client, 'get') as mock_get:
            mock_get.return_value = "value"
            result = await wrapper.redis_get("key")
            assert result == "value"
            mock_get.assert_called_once_with("key")

        # Test redis_delete
        with patch.object(wrapper._client, 'delete') as mock_delete:
            mock_delete.return_value = 1
            result = await wrapper.redis_delete("key")
            assert result == 1
            mock_delete.assert_called_once_with("key")

        # Test redis_list
        with patch.object(wrapper._client, 'list_keys') as mock_list:
            mock_list.return_value = ["key1", "key2"]
            result = await wrapper.redis_list("pattern")
            assert result == ["key1", "key2"]
            mock_list.assert_called_once_with("pattern")