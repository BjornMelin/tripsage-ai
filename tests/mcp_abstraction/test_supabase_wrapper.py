"""
Tests for Supabase MCP Wrapper.

This module contains comprehensive tests for the SupabaseMCPWrapper,
including configuration validation, method mapping, and integration tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.config.mcp_settings import SupabaseMCPConfig
from tripsage.mcp_abstraction.wrappers.supabase_wrapper import (
    ExternalMCPClient,
    SupabaseMCPWrapper,
)


class TestExternalMCPClient:
    """Tests for the ExternalMCPClient mock client."""

    def test_client_initialization(self):
        """Test that ExternalMCPClient initializes correctly."""
        config = MagicMock()
        config.enabled = True

        client = ExternalMCPClient("supabase", config)

        assert client.mcp_name == "supabase"
        assert client.config == config
        assert client.enabled is True

    def test_client_with_disabled_config(self):
        """Test ExternalMCPClient with disabled config."""
        config = MagicMock()
        config.enabled = False

        client = ExternalMCPClient("supabase", config)

        assert client.enabled is False

    @pytest.mark.asyncio
    async def test_client_method_calls_raise_not_implemented(self):
        """Test that method calls on ExternalMCPClient raise NotImplementedError."""
        config = MagicMock()
        config.enabled = True

        client = ExternalMCPClient("supabase", config)

        # Access any method
        method = client.some_method

        # Calling the method should raise NotImplementedError
        with pytest.raises(NotImplementedError) as exc_info:
            await method("arg1", key="value")

        assert "External MCP server communication not yet implemented" in str(
            exc_info.value
        )
        assert "supabase.some_method" in str(exc_info.value)


class TestSupabaseMCPWrapper:
    """Tests for the SupabaseMCPWrapper."""

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_wrapper_initialization_success(self, mock_settings):
        """Test successful wrapper initialization."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        wrapper = SupabaseMCPWrapper()

        assert wrapper._mcp_name == "supabase"
        assert isinstance(wrapper._client, ExternalMCPClient)
        assert wrapper._client.mcp_name == "supabase"

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_wrapper_initialization_disabled(self, mock_settings):
        """Test wrapper initialization with disabled config."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = False
        mock_settings.supabase = mock_config

        with pytest.raises(ValueError) as exc_info:
            SupabaseMCPWrapper()

        assert "Supabase MCP is not enabled in configuration" in str(exc_info.value)

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_wrapper_initialization_no_token(self, mock_settings):
        """Test wrapper initialization without access token."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token = None
        mock_settings.supabase = mock_config

        with pytest.raises(ValueError) as exc_info:
            SupabaseMCPWrapper()

        assert "Supabase MCP requires an access token to be configured" in str(
            exc_info.value
        )

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_get_available_methods(self, mock_settings):
        """Test getting available methods."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        wrapper = SupabaseMCPWrapper()
        methods = wrapper.get_available_methods()

        # Check that core methods are available
        expected_methods = [
            "list_organizations",
            "get_organization",
            "list_projects",
            "get_project",
            "create_project",
            "execute_sql",
            "apply_migration",
            "list_tables",
            "get_project_url",
            "get_anon_key",
        ]

        for method in expected_methods:
            assert method in methods

        # Check convenience aliases
        assert "select_data" in methods
        assert "run_sql" in methods
        assert "query" in methods

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_method_mapping(self, mock_settings):
        """Test that method mapping is correctly configured."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        wrapper = SupabaseMCPWrapper()
        method_map = wrapper._method_map

        # Test direct mappings
        assert method_map["list_organizations"] == "list_organizations"
        assert method_map["execute_sql"] == "execute_sql"
        assert method_map["create_project"] == "create_project"

        # Test convenience aliases
        assert method_map["select_data"] == "execute_sql"
        assert method_map["run_sql"] == "execute_sql"
        assert method_map["query"] == "execute_sql"
        assert method_map["start_project"] == "restore_project"
        assert method_map["stop_project"] == "pause_project"

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_wrapper_with_custom_client(self, mock_settings):
        """Test wrapper initialization with custom client."""
        mock_client = MagicMock()

        # Should ignore mock_settings since client is provided
        wrapper = SupabaseMCPWrapper(client=mock_client)

        assert wrapper._client == mock_client
        assert wrapper._mcp_name == "supabase"

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_wrapper_with_custom_mcp_name(self, mock_settings):
        """Test wrapper initialization with custom MCP name."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        wrapper = SupabaseMCPWrapper(mcp_name="custom-supabase")

        assert wrapper._mcp_name == "custom-supabase"
        assert wrapper._client.mcp_name == "custom-supabase"


class TestSupabaseMCPWrapperIntegration:
    """Integration tests for SupabaseMCPWrapper."""

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    @pytest.mark.asyncio
    async def test_invoke_method_not_implemented(self, mock_settings):
        """Test that invoke_method raises NotImplementedError for external server calls."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        wrapper = SupabaseMCPWrapper()

        # Try to invoke a method - should fail because ExternalMCPClient raises NotImplementedError
        with pytest.raises(Exception):  # Either MCPClientError or NotImplementedError
            await wrapper.invoke_method("list_organizations")

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_invoke_invalid_method(self, mock_settings):
        """Test invoking an invalid method name."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        wrapper = SupabaseMCPWrapper()

        # Try to invoke an invalid method
        with pytest.raises(ValueError) as exc_info:
            wrapper.invoke_method("invalid_method")

        assert "Method 'invalid_method' not available for supabase" in str(
            exc_info.value
        )
        assert "Available methods:" in str(exc_info.value)


@pytest.mark.integration
class TestSupabaseMCPWrapperWithMocks:
    """Integration tests using mocks for the external MCP communication."""

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    @pytest.mark.asyncio
    async def test_wrapper_method_calls_with_mock_client(self, mock_settings):
        """Test wrapper method calls with a mocked external client."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        # Create a mock client that supports async calls
        mock_client = MagicMock()
        mock_client.list_organizations = AsyncMock(return_value={"organizations": []})

        wrapper = SupabaseMCPWrapper(client=mock_client)

        # Test method call
        result = await wrapper.invoke_method("list_organizations")

        # Verify the mock was called
        mock_client.list_organizations.assert_called_once()
        assert result == {"organizations": []}

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    @pytest.mark.asyncio
    async def test_convenience_method_mapping(self, mock_settings):
        """Test that convenience methods map to the correct underlying methods."""
        # Setup mock config
        mock_config = MagicMock(spec=SupabaseMCPConfig)
        mock_config.enabled = True
        mock_config.access_token.get_secret_value.return_value = "test-token"
        mock_settings.supabase = mock_config

        # Create a mock client that supports async calls
        mock_client = MagicMock()
        mock_client.execute_sql = AsyncMock(return_value={"rows": [], "columns": []})

        wrapper = SupabaseMCPWrapper(client=mock_client)

        # Test convenience method calls
        await wrapper.invoke_method("select_data", query="SELECT * FROM users")
        await wrapper.invoke_method("run_sql", query="SELECT 1")
        await wrapper.invoke_method("query", query="SELECT NOW()")

        # Verify all calls went to execute_sql
        assert mock_client.execute_sql.call_count == 3

        # Check call arguments
        calls = mock_client.execute_sql.call_args_list
        assert calls[0][1]["query"] == "SELECT * FROM users"
        assert calls[1][1]["query"] == "SELECT 1"
        assert calls[2][1]["query"] == "SELECT NOW()"


def test_module_imports():
    """Test that all required modules can be imported."""
    from tripsage.config.mcp_settings import SupabaseMCPConfig, mcp_settings
    from tripsage.mcp_abstraction.wrappers.supabase_wrapper import (
        ExternalMCPClient,
        SupabaseMCPWrapper,
    )

    assert ExternalMCPClient is not None
    assert SupabaseMCPWrapper is not None
    assert SupabaseMCPConfig is not None
    assert mcp_settings is not None
