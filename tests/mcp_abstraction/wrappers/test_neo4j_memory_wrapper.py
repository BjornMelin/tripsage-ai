from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper import Neo4jMemoryMCPWrapper


@pytest.fixture
def mock_mcp_settings():
    """Mock mcp_settings configuration."""
    with patch(
        "tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper.mcp_settings"
    ) as mock_settings:
        mock_settings.neo4j_memory = MagicMock()
        mock_settings.neo4j_memory.enabled = True
        mock_settings.neo4j_memory.url = "localhost"
        mock_settings.neo4j_memory.port = 7687
        mock_settings.neo4j_memory.use_tls = True
        yield mock_settings


@pytest.fixture
def mock_memory_client():
    """Mock MemoryMCPClient."""
    with patch(
        "tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper.MemoryMCPClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client


class TestNeo4jMemoryMCPWrapper:
    """Test Neo4jMemoryMCPWrapper functionality."""

    async def test_init_enabled(self, mock_mcp_settings, mock_memory_client):
        """Test initialization with enabled configuration."""
        wrapper = Neo4jMemoryMCPWrapper()

        assert wrapper.is_available
        assert wrapper.client is not None
        wrapper.client.initialize.assert_called_once()

    async def test_init_disabled(self):
        """Test initialization with disabled configuration."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper.mcp_settings"
        ) as mock_settings:
            mock_settings.neo4j_memory = MagicMock()
            mock_settings.neo4j_memory.enabled = False

            wrapper = Neo4jMemoryMCPWrapper()

            assert not wrapper.is_available
            assert wrapper.client is None

    def test_build_method_map(self, mock_mcp_settings, mock_memory_client):
        """Test method map building with appropriate mappings."""
        wrapper = Neo4jMemoryMCPWrapper()

        expected_mappings = {
            # Create entities mappings
            "add_node": "create_entities",
            "create_node": "create_entities",
            "create_entities": "create_entities",
            # Create relations mappings
            "add_relationship": "create_relations",
            "create_relationship": "create_relations",
            "create_relations": "create_relations",
            # Open nodes mappings
            "get_node": "open_nodes",
            "open_nodes": "open_nodes",
            # Search mappings
            "search_nodes": "search_nodes",
            "query_graph": "search_nodes",
            # Read graph mappings
            "read_graph": "read_graph",
            "get_graph": "read_graph",
            "get_memory_summary": "read_graph",
            # Standard operations
            "add_observations": "add_observations",
            # Delete operations
            "delete_entities": "delete_entities",
            "delete_nodes": "delete_entities",
            "delete_relations": "delete_relations",
            "delete_relationships": "delete_relations",
            "delete_observations": "delete_observations",
        }

        assert wrapper.method_map == expected_mappings

    @pytest.mark.parametrize(
        "method_alias,standard_method",
        [
            ("add_node", "create_entities"),
            ("create_node", "create_entities"),
            ("add_relationship", "create_relations"),
            ("create_relationship", "create_relations"),
            ("get_node", "open_nodes"),
            ("query_graph", "search_nodes"),
            ("get_graph", "read_graph"),
            ("get_memory_summary", "read_graph"),
            ("delete_nodes", "delete_entities"),
            ("delete_relationships", "delete_relations"),
        ],
    )
    async def test_method_aliases(
        self, mock_mcp_settings, mock_memory_client, method_alias, standard_method
    ):
        """Test that method aliases correctly call standard methods."""
        wrapper = Neo4jMemoryMCPWrapper()

        # Mock the standard method
        mock_standard_method = AsyncMock(return_value={"success": True})
        setattr(mock_memory_client, standard_method, mock_standard_method)

        # Call through the alias
        result = await wrapper.call_tool(method_alias, {"test": "params"})

        # Verify the standard method was called
        mock_standard_method.assert_called_once_with({"test": "params"})
        assert result == {"success": True}

    @pytest.mark.parametrize(
        "method_name,params",
        [
            ("create_entities", {"entities": [{"name": "Test", "type": "Entity"}]}),
            (
                "create_relations",
                {"relations": [{"from": "A", "to": "B", "type": "relates"}]},
            ),
            ("open_nodes", {"names": ["Node1", "Node2"]}),
            ("search_nodes", {"query": "test search"}),
            ("read_graph", {}),
            (
                "add_observations",
                {"observations": [{"entity": "Test", "observation": "data"}]},
            ),
            ("delete_entities", {"names": ["Entity1"]}),
            ("delete_relations", {"relations": [{"from": "A", "to": "B"}]}),
            (
                "delete_observations",
                {"deletions": [{"entity": "Test", "observations": ["obs1"]}]},
            ),
        ],
    )
    async def test_standard_method_invocation(
        self, mock_mcp_settings, mock_memory_client, method_name, params
    ):
        """Test standard method invocation."""
        wrapper = Neo4jMemoryMCPWrapper()

        # Mock the method on the client
        mock_method = AsyncMock(return_value={"success": True})
        setattr(mock_memory_client, method_name, mock_method)

        # Call the method
        result = await wrapper.call_tool(method_name, params)

        # Verify the call
        mock_method.assert_called_once_with(params)
        assert result == {"success": True}

    async def test_disabled_service_error(self):
        """Test error handling when service is disabled."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper.mcp_settings"
        ) as mock_settings:
            mock_settings.neo4j_memory = MagicMock()
            mock_settings.neo4j_memory.enabled = False

            wrapper = Neo4jMemoryMCPWrapper()

            with pytest.raises(
                ValueError, match="Neo4J Memory service is not available"
            ):
                await wrapper.call_tool("read_graph", {})

    async def test_method_not_found_error(self, mock_mcp_settings, mock_memory_client):
        """Test error when calling non-existent method."""
        wrapper = Neo4jMemoryMCPWrapper()

        with pytest.raises(
            AttributeError,
            match="Neo4jMemoryMCPWrapper does not support method: invalid_method",
        ):
            await wrapper.call_tool("invalid_method", {})

    async def test_async_method_compatibility(
        self, mock_mcp_settings, mock_memory_client
    ):
        """Test async method compatibility."""
        wrapper = Neo4jMemoryMCPWrapper()

        # Test with async method
        async_method = AsyncMock(return_value={"async": True})
        mock_memory_client.read_graph = async_method

        result = await wrapper.call_tool("read_graph", {})
        assert result == {"async": True}

        # Test with sync method (should be wrapped)
        sync_method = MagicMock(return_value={"sync": True})
        mock_memory_client.read_graph = sync_method

        result = await wrapper.call_tool("read_graph", {})
        assert result == {"sync": True}

    async def test_get_available_methods(self, mock_mcp_settings, mock_memory_client):
        """Test getting available methods."""
        wrapper = Neo4jMemoryMCPWrapper()

        methods = await wrapper.get_available_methods()

        expected_methods = [
            "add_node",
            "create_node",
            "create_entities",
            "add_relationship",
            "create_relationship",
            "create_relations",
            "get_node",
            "open_nodes",
            "search_nodes",
            "query_graph",
            "read_graph",
            "get_graph",
            "get_memory_summary",
            "add_observations",
            "delete_entities",
            "delete_nodes",
            "delete_relations",
            "delete_relationships",
            "delete_observations",
        ]

        assert sorted(methods) == sorted(expected_methods)

    async def test_endpoint_url_construction(
        self, mock_mcp_settings, mock_memory_client
    ):
        """Test that endpoint URL is constructed correctly from config values."""
        mock_settings = mock_mcp_settings.neo4j_memory

        # Test with TLS enabled
        mock_settings.use_tls = True
        mock_settings.url = "memory.example.com"
        mock_settings.port = 7687
        wrapper = Neo4jMemoryMCPWrapper()
        assert wrapper.endpoint_url == "neo4j://memory.example.com:7687"

        # Test with TLS disabled
        mock_settings.use_tls = False
        wrapper = Neo4jMemoryMCPWrapper()
        assert wrapper.endpoint_url == "neo4j://memory.example.com:7687"

        # Test with different port
        mock_settings.port = 8080
        wrapper = Neo4jMemoryMCPWrapper()
        assert wrapper.endpoint_url == "neo4j://memory.example.com:8080"
