"""Tests for SupabaseMCPWrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import (
    MCPClientError,
    MCPInvocationError,
    MCPTimeoutError,
    TripSageMCPError,
)
from tripsage.mcp_abstraction.wrappers.supabase_wrapper import SupabaseMCPWrapper


class TestSupabaseMCPWrapper:
    """Test cases for SupabaseMCPWrapper."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock SupabaseMCPClient."""
        client = MagicMock()
        # Setup common methods
        client.list_organizations = AsyncMock(
            return_value={"organizations": [{"id": "org1"}]}
        )
        client.list_projects = AsyncMock(
            return_value={"projects": [{"id": "proj1", "name": "Test"}]}
        )
        client.get_project = AsyncMock(
            return_value={"project": {"id": "proj1", "status": "active"}}
        )
        client.execute_sql = AsyncMock(
            return_value={"rows": [{"id": 1, "name": "Test"}]}
        )
        client.list_tables = AsyncMock(return_value={"tables": ["users", "trips"]})
        client.apply_migration = AsyncMock(return_value={"success": True})
        client.list_edge_functions = AsyncMock(
            return_value={"functions": ["hello", "auth"]}
        )
        client.get_logs = AsyncMock(
            return_value={"logs": ["Log entry 1", "Log entry 2"]}
        )
        return client

    @pytest.fixture
    def wrapper(self, mock_client):
        """Create a SupabaseMCPWrapper with mocked client."""
        return SupabaseMCPWrapper(client=mock_client, mcp_name="supabase-test")

    def test_initialization_with_client(self, mock_client):
        """Test wrapper initialization with provided client."""
        wrapper = SupabaseMCPWrapper(client=mock_client, mcp_name="supabase-test")
        assert wrapper.client == mock_client
        assert wrapper.mcp_name == "supabase-test"

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.SupabaseMCPClient")
    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_initialization_without_client_enabled(
        self, mock_settings, MockSupabaseClient
    ):
        """Test wrapper initialization without provided client when enabled."""
        # Setup mock settings
        mock_settings.supabase.enabled = True
        mock_settings.supabase.url = "https://supabase.example.com"
        mock_settings.supabase.api_key.get_secret_value.return_value = "test-key"
        mock_settings.supabase.timeout = 30
        mock_settings.supabase.retry_attempts = 3

        # Setup mock client class
        mock_client_instance = MagicMock()
        MockSupabaseClient.return_value = mock_client_instance

        # Create wrapper
        wrapper = SupabaseMCPWrapper()

        # Verify client creation
        MockSupabaseClient.assert_called_once_with(
            endpoint="https://supabase.example.com",
            api_key="test-key",
            timeout=30,
            use_cache=True,
        )
        assert wrapper.client == mock_client_instance
        assert wrapper.mcp_name == "supabase"

    @patch("tripsage.mcp_abstraction.wrappers.supabase_wrapper.mcp_settings")
    def test_initialization_without_client_disabled(self, mock_settings):
        """Test wrapper initialization raises error when Supabase is disabled."""
        mock_settings.supabase.enabled = False

        with pytest.raises(
            ValueError, match="Supabase MCP is not enabled in configuration"
        ):
            SupabaseMCPWrapper()

    def test_method_map(self, wrapper):
        """Test method mapping is correctly built."""
        method_map = wrapper._method_map

        # Verify core methods
        assert method_map["list_organizations"] == "list_organizations"
        assert method_map["list_projects"] == "list_projects"
        assert method_map["execute_sql"] == "execute_sql"
        assert method_map["list_tables"] == "list_tables"

        # Verify SQL aliases
        assert method_map["select_data"] == "execute_sql"
        assert method_map["insert_data"] == "execute_sql"
        assert method_map["update_data"] == "execute_sql"
        assert method_map["delete_data"] == "execute_sql"
        assert method_map["call_rpc"] == "execute_sql"

        # Verify branch operations
        assert method_map["create_branch"] == "create_branch"
        assert method_map["list_branches"] == "list_branches"
        assert method_map["merge_branch"] == "merge_branch"

    def test_get_available_methods(self, wrapper):
        """Test getting available methods."""
        methods = wrapper.get_available_methods()

        # Check core methods exist
        assert "list_organizations" in methods
        assert "list_projects" in methods
        assert "execute_sql" in methods
        assert "select_data" in methods
        assert "create_branch" in methods

        # Check count matches expected
        assert len(methods) > 25  # We have many methods defined

    @pytest.mark.asyncio
    async def test_invoke_list_organizations(self, wrapper):
        """Test invoking list_organizations method."""
        result = await wrapper.invoke_method("list_organizations")
        assert result == {"organizations": [{"id": "org1"}]}
        wrapper.client.list_organizations.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_execute_sql(self, wrapper):
        """Test invoking execute_sql method."""
        result = await wrapper.invoke_method(
            "execute_sql", sql="SELECT * FROM users WHERE id = $1", params=[1]
        )
        assert result == {"rows": [{"id": 1, "name": "Test"}]}
        wrapper.client.execute_sql.assert_called_once_with(
            sql="SELECT * FROM users WHERE id = $1", params=[1]
        )

    @pytest.mark.asyncio
    async def test_invoke_sql_aliases(self, wrapper):
        """Test invoking SQL operation aliases."""
        # Test select_data alias
        await wrapper.invoke_method("select_data", sql="SELECT * FROM users")
        wrapper.client.execute_sql.assert_called_with(sql="SELECT * FROM users")

        # Test insert_data alias
        await wrapper.invoke_method(
            "insert_data", sql="INSERT INTO users (name) VALUES ($1)", params=["John"]
        )
        wrapper.client.execute_sql.assert_called_with(
            sql="INSERT INTO users (name) VALUES ($1)", params=["John"]
        )

    @pytest.mark.asyncio
    async def test_invoke_project_operations(self, wrapper):
        """Test invoking project-related operations."""
        result = await wrapper.invoke_method("get_project", project_id="proj1")
        assert result == {"project": {"id": "proj1", "status": "active"}}
        wrapper.client.get_project.assert_called_once_with(project_id="proj1")

    @pytest.mark.asyncio
    async def test_invoke_migration_operations(self, wrapper):
        """Test invoking migration operations."""
        result = await wrapper.invoke_method(
            "apply_migration",
            migration_sql="CREATE TABLE new_table (id SERIAL PRIMARY KEY)",
        )
        assert result == {"success": True}
        wrapper.client.apply_migration.assert_called_once_with(
            migration_sql="CREATE TABLE new_table (id SERIAL PRIMARY KEY)"
        )

    @pytest.mark.asyncio
    async def test_invoke_unknown_method(self, wrapper):
        """Test invoking unknown method raises error."""
        with pytest.raises(MCPInvocationError, match="Method unknown_method not found"):
            await wrapper.invoke_method("unknown_method")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, wrapper):
        """Test connection error handling."""
        wrapper.client.list_projects.side_effect = ConnectionError("Network error")

        with pytest.raises(MCPClientError):
            await wrapper.invoke_method("list_projects")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, wrapper):
        """Test timeout error handling."""
        wrapper.client.list_projects.side_effect = TimeoutError("Request timed out")

        with pytest.raises(MCPTimeoutError):
            await wrapper.invoke_method("list_projects")

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, wrapper):
        """Test generic error handling."""
        wrapper.client.list_projects.side_effect = Exception("Something went wrong")

        with pytest.raises(TripSageMCPError):
            await wrapper.invoke_method("list_projects")

    @pytest.mark.asyncio
    async def test_complex_method_invocation(self, wrapper):
        """Test complex method invocation with multiple parameters."""
        # Mock create_project method
        wrapper.client.create_project = AsyncMock(
            return_value={"project": {"id": "new-proj", "name": "New Project"}}
        )

        result = await wrapper.invoke_method(
            "create_project",
            name="New Project",
            organization_id="org1",
            db_pass="secure_pass",
            region="us-east-1",
        )

        assert result == {"project": {"id": "new-proj", "name": "New Project"}}
        wrapper.client.create_project.assert_called_once_with(
            name="New Project",
            organization_id="org1",
            db_pass="secure_pass",
            region="us-east-1",
        )

    def test_context_manager(self, wrapper):
        """Test wrapper can be used as context manager."""
        with wrapper as w:
            assert w == wrapper

        # Verify no errors are raised
        assert True

    def test_repr(self, wrapper):
        """Test string representation."""
        assert repr(wrapper) == "<SupabaseMCPWrapper(mcp_name='supabase-test')>"
