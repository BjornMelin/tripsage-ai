"""
Tests for Supabase MCP client implementation.

This module contains tests for the Supabase MCP client which is used
in production environments to interact with Supabase PostgreSQL.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.mcp.supabase.client import SupabaseMCPClient, SupabaseService, get_client


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase MCP client for testing."""
    client = MagicMock(spec=SupabaseMCPClient)
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def supabase_service(mock_supabase_client):
    """Create a SupabaseService instance with a mock client."""
    return SupabaseService(client=mock_supabase_client)


class TestSupabaseMCPClient:
    """Tests for the SupabaseMCPClient class."""

    @patch("src.mcp.supabase.client.FastMCPClient.__init__")
    def test_init(self, mock_init):
        """Test initialization of SupabaseMCPClient."""
        # Mock settings
        with patch("src.mcp.supabase.client.settings") as mock_settings:
            mock_settings.supabase_mcp.endpoint = "http://test-endpoint"
            mock_settings.supabase_mcp.api_key = "test-api-key"
            
            # Initialize client
            client = SupabaseMCPClient()
            
            # Check FastMCPClient initialization
            mock_init.assert_called_once()
            args, kwargs = mock_init.call_args
            
            assert kwargs["server_name"] == "Supabase"
            assert kwargs["endpoint"] == "http://test-endpoint"
            assert kwargs["api_key"] == "test-api-key"
            assert kwargs["timeout"] == 60.0
            assert kwargs["use_cache"] is True
            assert kwargs["cache_ttl"] == 300  # 5 minutes

    @pytest.mark.asyncio
    async def test_list_organizations(self, mock_supabase_client):
        """Test list_organizations method."""
        # Setup mock response
        mock_response = {
            "organizations": [
                {"id": "org1", "name": "Organization 1"},
                {"id": "org2", "name": "Organization 2"}
            ]
        }
        mock_supabase_client.call_tool.return_value = mock_response
        
        # Create client instance with the mock
        client = SupabaseMCPClient()
        client.call_tool = mock_supabase_client.call_tool
        
        # Call method and check result
        result = await client.list_organizations()
        
        # Verify call to MCP tool
        mock_supabase_client.call_tool.assert_called_once_with(
            "list_organizations", 
            {}, 
            skip_cache=False
        )
        
        # Verify result
        assert result == mock_response
        assert len(result["organizations"]) == 2
        assert result["organizations"][0]["id"] == "org1"

    @pytest.mark.asyncio
    async def test_list_projects(self, mock_supabase_client):
        """Test list_projects method."""
        # Setup mock response
        mock_response = {
            "projects": [
                {"id": "project1", "name": "Project 1"},
                {"id": "project2", "name": "Project 2"}
            ]
        }
        mock_supabase_client.call_tool.return_value = mock_response
        
        # Create client instance with the mock
        client = SupabaseMCPClient()
        client.call_tool = mock_supabase_client.call_tool
        
        # Call method and check result
        result = await client.list_projects()
        
        # Verify call to MCP tool
        mock_supabase_client.call_tool.assert_called_once_with(
            "list_projects", 
            {}, 
            skip_cache=False
        )
        
        # Verify result
        assert result == mock_response
        assert len(result["projects"]) == 2
        assert result["projects"][0]["id"] == "project1"

    @pytest.mark.asyncio
    async def test_execute_sql(self, mock_supabase_client):
        """Test execute_sql method."""
        # Setup mock response
        mock_response = {
            "results": [{"column1": "value1"}, {"column1": "value2"}]
        }
        mock_supabase_client.call_tool.return_value = mock_response
        
        # Create client instance with the mock
        client = SupabaseMCPClient()
        client.call_tool = mock_supabase_client.call_tool
        
        # Call method and check result
        result = await client.execute_sql(
            project_id="test-project",
            query="SELECT * FROM test_table"
        )
        
        # Verify call to MCP tool
        mock_supabase_client.call_tool.assert_called_once_with(
            "execute_sql", 
            {
                "project_id": "test-project", 
                "query": "SELECT * FROM test_table"
            }
        )
        
        # Verify result
        assert result == mock_response
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_apply_migration(self, mock_supabase_client):
        """Test apply_migration method."""
        # Setup mock response
        mock_response = {
            "migration": {
                "id": "migration1",
                "name": "create_test_table",
                "status": "applied"
            }
        }
        mock_supabase_client.call_tool.return_value = mock_response
        
        # Create client instance with the mock
        client = SupabaseMCPClient()
        client.call_tool = mock_supabase_client.call_tool
        
        # Call method and check result
        result = await client.apply_migration(
            project_id="test-project",
            name="create_test_table",
            query="CREATE TABLE test (id SERIAL PRIMARY KEY);"
        )
        
        # Verify call to MCP tool
        mock_supabase_client.call_tool.assert_called_once_with(
            "apply_migration", 
            {
                "project_id": "test-project", 
                "name": "create_test_table", 
                "query": "CREATE TABLE test (id SERIAL PRIMARY KEY);"
            }
        )
        
        # Verify result
        assert result == mock_response
        assert result["migration"]["id"] == "migration1"
        assert result["migration"]["name"] == "create_test_table"
        assert result["migration"]["status"] == "applied"

    @pytest.mark.asyncio
    async def test_create_branch(self, mock_supabase_client):
        """Test create_branch method."""
        # Setup mock response
        mock_response = {
            "branch": {"id": "branch1", "name": "develop"}
        }
        mock_supabase_client.call_tool.return_value = mock_response
        
        # Create client instance with the mock
        client = SupabaseMCPClient()
        client.call_tool = mock_supabase_client.call_tool
        
        # Call method and check result
        result = await client.create_branch(
            project_id="test-project",
            confirm_cost_id="cost1",
            name="develop"
        )
        
        # Verify call to MCP tool
        mock_supabase_client.call_tool.assert_called_once_with(
            "create_branch", 
            {
                "project_id": "test-project", 
                "confirm_cost_id": "cost1",
                "name": "develop"
            }
        )
        
        # Verify result
        assert result == mock_response
        assert result["branch"]["id"] == "branch1"
        assert result["branch"]["name"] == "develop"


class TestSupabaseService:
    """Tests for the SupabaseService class."""

    @pytest.mark.asyncio
    async def test_get_default_project(self, supabase_service, mock_supabase_client):
        """Test get_default_project method with configured project ID."""
        # Setup mock response
        mock_project = {"id": "project1", "name": "Project 1"}
        mock_supabase_client.get_project.return_value = mock_project
        
        # Mock settings
        with patch("src.mcp.supabase.client.settings") as mock_settings:
            mock_settings.supabase_mcp.default_project_id = "project1"
            
            # Call method
            result = await supabase_service.get_default_project()
            
            # Verify call to client methods
            mock_supabase_client.get_project.assert_called_once_with("project1")
            
            # Verify result
            assert result == mock_project

    @pytest.mark.asyncio
    async def test_get_default_project_no_config(self, supabase_service, mock_supabase_client):
        """Test get_default_project method with no configured project ID."""
        # Setup mock responses
        mock_projects = {
            "projects": [{"id": "project1", "name": "Project 1"}]
        }
        mock_supabase_client.list_projects.return_value = mock_projects
        
        # Mock settings
        with patch("src.mcp.supabase.client.settings") as mock_settings:
            mock_settings.supabase_mcp.default_project_id = None
            
            # Call method
            result = await supabase_service.get_default_project()
            
            # Verify call to client methods
            mock_supabase_client.list_projects.assert_called_once()
            
            # Verify result
            assert result == mock_projects["projects"][0]

    @pytest.mark.asyncio
    async def test_apply_migrations(self, supabase_service, mock_supabase_client):
        """Test apply_migrations method."""
        # Setup mock responses
        mock_results = [
            {"migration": {"id": "mig1", "status": "applied"}},
            {"migration": {"id": "mig2", "status": "applied"}}
        ]
        
        # Setup return values for sequential calls
        mock_supabase_client.apply_migration.side_effect = mock_results
        
        # Call method
        migrations = [
            "CREATE TABLE test (id SERIAL PRIMARY KEY);",
            "CREATE INDEX idx_test_id ON test (id);"
        ]
        
        migration_names = ["create_test_table", "create_test_index"]
        
        result = await supabase_service.apply_migrations(
            project_id="project1",
            migrations=migrations,
            migration_names=migration_names
        )
        
        # Verify calls to client method
        assert mock_supabase_client.apply_migration.call_count == 2
        
        call_args_list = mock_supabase_client.apply_migration.call_args_list
        assert call_args_list[0][0] == ("project1", "create_test_table", migrations[0])
        assert call_args_list[1][0] == ("project1", "create_test_index", migrations[1])
        
        # Verify result
        assert result["project_id"] == "project1"
        assert result["migrations_applied"] == 2
        assert result["results"] == mock_results

    @pytest.mark.asyncio
    async def test_create_development_branch(self, supabase_service, mock_supabase_client):
        """Test create_development_branch method."""
        # Setup mock responses
        mock_supabase_client.list_organizations.return_value = {
            "organizations": [{"id": "org1", "name": "Org 1"}]
        }
        
        mock_supabase_client.get_cost.return_value = {
            "amount": 10.0,
            "recurrence": "hourly"
        }
        
        mock_supabase_client.confirm_cost.return_value = {"id": "cost1"}
        
        mock_supabase_client.create_branch.return_value = {
            "branch": {"id": "branch1", "name": "develop"}
        }
        
        # Mock settings
        with patch("src.mcp.supabase.client.settings") as mock_settings:
            mock_settings.supabase_mcp.default_project_id = "project1"
            
            # Call method
            result = await supabase_service.create_development_branch(
                project_id="project1",
                branch_name="develop"
            )
            
            # Verify calls to client methods
            mock_supabase_client.list_organizations.assert_called_once()
            
            mock_supabase_client.get_cost.assert_called_once_with(
                "branch", "org1"
            )
            
            mock_supabase_client.confirm_cost.assert_called_once_with(
                "branch", "hourly", 10.0
            )
            
            mock_supabase_client.create_branch.assert_called_once_with(
                "project1", "cost1", "develop"
            )
            
            # Verify result
            assert result == {"branch": {"id": "branch1", "name": "develop"}}


def test_get_client():
    """Test get_client function returns a SupabaseMCPClient instance."""
    client = get_client()
    assert isinstance(client, SupabaseMCPClient)