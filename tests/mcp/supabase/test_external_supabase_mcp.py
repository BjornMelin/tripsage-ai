"""
Tests for external Supabase MCP server integration.

This module contains tests that verify TripSage's integration with the external
Supabase MCP server for production environments.
"""

import os
import unittest
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from tripsage.mcp.db_factory import Environment, get_mcp_client, get_mcp_service
from tripsage.mcp.supabase.client import SupabaseMCPClient
from tripsage.mcp.supabase.models import ListOrganizationsResponse, ListProjectsResponse
from tripsage.mcp.supabase.service import SupabaseService
from tripsage.utils.settings import settings


class SupabaseMCPAvailableModel(BaseModel):
    """Simple model to check if Supabase MCP server is available."""

    available: bool
    message: str


@pytest.mark.asyncio
@pytest.mark.skipif(
    settings.environment.lower() != "production",
    reason="Only run in production environment",
)
class TestExternalSupabaseMCP:
    """Tests for the external Supabase MCP server integration."""

    def test_supabase_mcp_configured(self):
        """Test that Supabase MCP is configured in AppSettings."""
        assert hasattr(settings, "supabase_mcp"), (
            "Supabase MCP not configured in settings"
        )
        assert settings.supabase_mcp.endpoint, "Supabase MCP endpoint not configured"

        # Check that if Supabase MCP is configured to be production-only
        assert settings.supabase_mcp.prod_only, "Supabase MCP should be prod-only"

    def test_db_factory_production_client(self):
        """Test that db_factory provides SupabaseMCPClient for production."""
        # Test with explicit production environment
        client = get_mcp_client(Environment.PRODUCTION)
        assert isinstance(client, SupabaseMCPClient), (
            "Factory should return SupabaseMCPClient for production"
        )

        # Test with explicit staging environment (should also use Supabase)
        client = get_mcp_client(Environment.STAGING)
        assert isinstance(client, SupabaseMCPClient), (
            "Factory should return SupabaseMCPClient for staging"
        )

    def test_db_factory_production_service(self):
        """Test that db_factory provides SupabaseService for production."""
        # Test with explicit production environment
        service = get_mcp_service(Environment.PRODUCTION)
        assert isinstance(service, SupabaseService), (
            "Factory should return SupabaseService for production"
        )

        # Test with explicit staging environment (should also use Supabase)
        service = get_mcp_service(Environment.STAGING)
        assert isinstance(service, SupabaseService), (
            "Factory should return SupabaseService for staging"
        )


@pytest.mark.asyncio
class TestExternalSupabaseMCPMock:
    """Tests for the external Supabase MCP server integration with mocks."""

    @patch("src.mcp.supabase.client.settings")
    def test_client_initialization_from_settings(self, mock_settings):
        """Test that SupabaseMCPClient initializes correctly from settings."""
        # Setup mock
        mock_settings.supabase_mcp.endpoint = "https://test-endpoint"
        mock_settings.supabase_mcp.api_key.get_secret_value.return_value = (
            "test-api-key"
        )
        mock_settings.supabase_mcp.prod_only = True
        mock_settings.supabase_mcp.default_project_id = "test-project-id"

        # Create client
        client = SupabaseMCPClient()

        # Check that endpoint and API key are set correctly
        assert client.endpoint == "https://test-endpoint"
        assert client.api_key == "test-api-key"

    @patch("src.mcp.supabase.client.FastMCPClient.call_tool")
    async def test_list_organizations(self, mock_call_tool):
        """Test the list_organizations method."""
        # Setup mock response
        mock_response = {
            "organizations": [
                {"id": "org1", "name": "Organization 1", "created_at": "2025-05-11"},
                {"id": "org2", "name": "Organization 2", "created_at": "2025-05-11"},
            ]
        }
        mock_call_tool.return_value = mock_response

        # Create client
        client = SupabaseMCPClient(
            endpoint="https://test-endpoint", api_key="test-api-key"
        )

        # Call method
        result = await client.list_organizations()

        # Verify call to MCP tool
        mock_call_tool.assert_called_once()
        assert mock_call_tool.call_args[0][0] == "list_organizations"

        # Verify result
        assert isinstance(result, ListOrganizationsResponse)
        assert len(result.organizations) == 2
        assert result.organizations[0].id == "org1"
        assert result.organizations[0].name == "Organization 1"

    @patch("src.mcp.supabase.client.FastMCPClient.call_tool")
    async def test_list_projects(self, mock_call_tool):
        """Test the list_projects method."""
        # Setup mock response
        mock_response = {
            "projects": [
                {
                    "id": "project1",
                    "name": "Project 1",
                    "organization_id": "org1",
                    "created_at": "2025-05-11",
                    "status": "active",
                },
                {
                    "id": "project2",
                    "name": "Project 2",
                    "organization_id": "org1",
                    "created_at": "2025-05-11",
                    "status": "active",
                },
            ]
        }
        mock_call_tool.return_value = mock_response

        # Create client
        client = SupabaseMCPClient(
            endpoint="https://test-endpoint", api_key="test-api-key"
        )

        # Call method
        result = await client.list_projects()

        # Verify call to MCP tool
        mock_call_tool.assert_called_once()
        assert mock_call_tool.call_args[0][0] == "list_projects"

        # Verify result
        assert isinstance(result, ListProjectsResponse)
        assert len(result.projects) == 2
        assert result.projects[0].id == "project1"
        assert result.projects[0].name == "Project 1"
        assert result.projects[0].status == "active"


@pytest.mark.skipif(
    not os.environ.get("SUPABASE_MCP_TEST"),
    reason="Set SUPABASE_MCP_TEST=1 to run tests requiring Supabase MCP server",
)
@pytest.mark.asyncio
class TestExternalSupabaseMCPLive:
    """
    Integration tests for the external Supabase MCP server.

    These tests require a running Supabase MCP server and valid credentials.
    They are skipped by default and can be enabled by setting the
    SUPABASE_MCP_TEST environment variable.
    """

    async def test_list_organizations_live(self):
        """Test the list_organizations method with a live server."""
        client = SupabaseMCPClient()
        result = await client.list_organizations()

        # Basic validation that the response is correct
        assert isinstance(result, ListOrganizationsResponse)
        assert hasattr(result, "organizations")

    async def test_list_projects_live(self):
        """Test the list_projects method with a live server."""
        client = SupabaseMCPClient()
        result = await client.list_projects()

        # Basic validation that the response is correct
        assert isinstance(result, ListProjectsResponse)
        assert hasattr(result, "projects")

    async def test_default_project_live(self):
        """Test the get_default_project method with a live server."""
        service = SupabaseService()
        result = await service.get_default_project()

        # Basic validation that the response is correct
        assert "id" in result
        assert "name" in result


if __name__ == "__main__":
    unittest.main()
