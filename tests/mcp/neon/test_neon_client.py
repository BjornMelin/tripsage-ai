"""
Tests for Neon MCP client implementation.

This module contains tests for the Neon MCP client which is used
in development environments to interact with Neon PostgreSQL.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp.neon.client import NeonMCPClient, NeonService, get_client


@pytest.fixture
def mock_neon_client():
    """Create a mock Neon MCP client for testing."""
    client = MagicMock(spec=NeonMCPClient)
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def neon_service(mock_neon_client):
    """Create a NeonService instance with a mock client."""
    return NeonService(client=mock_neon_client)


class TestNeonMCPClient:
    """Tests for the NeonMCPClient class."""

    @patch("src.mcp.neon.client.FastMCPClient.__init__")
    def test_init(self, mock_init):
        """Test initialization of NeonMCPClient."""
        # Mock settings
        with patch("src.mcp.neon.client.settings") as mock_settings:
            mock_settings.neon_mcp.endpoint = "http://test-endpoint"
            mock_settings.neon_mcp.api_key = "test-api-key"

            # Initialize client
            _client = NeonMCPClient()

            # Check FastMCPClient initialization
            mock_init.assert_called_once()
            args, kwargs = mock_init.call_args

            assert kwargs["server_name"] == "Neon"
            assert kwargs["endpoint"] == "http://test-endpoint"
            assert kwargs["api_key"] == "test-api-key"
            assert kwargs["timeout"] == 60.0
            assert kwargs["use_cache"] is True
            assert kwargs["cache_ttl"] == 300  # 5 minutes

    @pytest.mark.asyncio
    async def test_list_projects(self, mock_neon_client):
        """Test list_projects method."""
        # Setup mock response
        mock_response = {
            "projects": [
                {"id": "project1", "name": "Project 1"},
                {"id": "project2", "name": "Project 2"},
            ]
        }
        mock_neon_client.call_tool.return_value = mock_response

        # Create client instance with the mock
        client = NeonMCPClient()
        client.call_tool = mock_neon_client.call_tool

        # Call method and check result
        result = await client.list_projects()

        # Verify call to MCP tool
        mock_neon_client.call_tool.assert_called_once_with(
            "list_projects", {"params": {}}, skip_cache=False
        )

        # Verify result
        assert result == mock_response
        assert len(result["projects"]) == 2
        assert result["projects"][0]["id"] == "project1"

    @pytest.mark.asyncio
    async def test_create_project(self, mock_neon_client):
        """Test create_project method."""
        # Setup mock response
        mock_response = {"project": {"id": "new-project", "name": "New Project"}}
        mock_neon_client.call_tool.return_value = mock_response

        # Create client instance with the mock
        client = NeonMCPClient()
        client.call_tool = mock_neon_client.call_tool

        # Call method and check result
        result = await client.create_project("New Project")

        # Verify call to MCP tool
        mock_neon_client.call_tool.assert_called_once_with(
            "create_project", {"params": {"name": "New Project"}}
        )

        # Verify result
        assert result == mock_response
        assert result["project"]["id"] == "new-project"
        assert result["project"]["name"] == "New Project"

    @pytest.mark.asyncio
    async def test_run_sql(self, mock_neon_client):
        """Test run_sql method."""
        # Setup mock response
        mock_response = {"results": [{"column1": "value1"}, {"column1": "value2"}]}
        mock_neon_client.call_tool.return_value = mock_response

        # Create client instance with the mock
        client = NeonMCPClient()
        client.call_tool = mock_neon_client.call_tool

        # Call method and check result
        result = await client.run_sql(
            project_id="test-project",
            sql="SELECT * FROM test_table",
            database_name="test_db",
            branch_id="test-branch",
        )

        # Verify call to MCP tool
        mock_neon_client.call_tool.assert_called_once_with(
            "run_sql",
            {
                "params": {
                    "projectId": "test-project",
                    "sql": "SELECT * FROM test_table",
                    "databaseName": "test_db",
                    "branchId": "test-branch",
                }
            },
        )

        # Verify result
        assert result == mock_response
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_create_branch(self, mock_neon_client):
        """Test create_branch method."""
        # Setup mock response
        mock_response = {"branch": {"id": "new-branch", "name": "feature-branch"}}
        mock_neon_client.call_tool.return_value = mock_response

        # Create client instance with the mock
        client = NeonMCPClient()
        client.call_tool = mock_neon_client.call_tool

        # Call method and check result
        result = await client.create_branch("test-project", "feature-branch")

        # Verify call to MCP tool
        mock_neon_client.call_tool.assert_called_once_with(
            "create_branch",
            {"params": {"projectId": "test-project", "branchName": "feature-branch"}},
        )

        # Verify result
        assert result == mock_response
        assert result["branch"]["id"] == "new-branch"
        assert result["branch"]["name"] == "feature-branch"


class TestNeonService:
    """Tests for the NeonService class."""

    @pytest.mark.asyncio
    async def test_create_development_branch(self, neon_service, mock_neon_client):
        """Test create_development_branch method."""
        # Setup mock responses
        mock_neon_client.list_projects.return_value = {
            "projects": [{"id": "project1", "name": "Project 1"}]
        }

        mock_neon_client.create_branch.return_value = {
            "branch": {"id": "branch1", "name": "dev-feature"}
        }

        mock_neon_client.get_connection_string.return_value = {
            "connectionString": "postgres://user:pass@host:port/db"
        }

        # Call method
        result = await neon_service.create_development_branch(
            project_id="project1", branch_name="dev-feature"
        )

        # Verify call to client methods
        mock_neon_client.create_branch.assert_called_once_with(
            "project1", "dev-feature"
        )

        mock_neon_client.get_connection_string.assert_called_once_with(
            "project1", mock_neon_client.create_branch.return_value["branch"]["id"]
        )

        # Verify result
        assert result["project_id"] == "project1"
        assert result["branch"] == {"id": "branch1", "name": "dev-feature"}
        assert result["connection_string"] == "postgres://user:pass@host:port/db"

    @pytest.mark.asyncio
    async def test_apply_migrations(self, neon_service, mock_neon_client):
        """Test apply_migrations method."""
        # Setup mock response
        mock_neon_client.run_sql_transaction.return_value = {
            "results": ["success", "success"]
        }

        # Call method
        migrations = [
            "CREATE TABLE test (id SERIAL PRIMARY KEY);",
            "CREATE INDEX idx_test_id ON test (id);",
        ]

        result = await neon_service.apply_migrations(
            project_id="project1",
            branch_id="branch1",
            migrations=migrations,
            database_name="test_db",
        )

        # Verify call to client method
        mock_neon_client.run_sql_transaction.assert_called_once_with(
            "project1", migrations, "test_db", "branch1"
        )

        # Verify result
        assert result["project_id"] == "project1"
        assert result["branch_id"] == "branch1"
        assert result["migrations_applied"] == 2
        assert result["result"] == {"results": ["success", "success"]}


def test_get_client():
    """Test get_client function returns a NeonMCPClient instance."""
    client = get_client()
    assert isinstance(client, NeonMCPClient)
