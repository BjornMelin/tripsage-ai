"""
Tests for the database MCP factory.

This module contains tests for the database MCP factory which selects the appropriate
database MCP client based on the environment (development or production).
"""

from unittest.mock import MagicMock, patch

from tripsage.mcp.db_factory import (
    DatabaseMCPFactory,
    db_mcp_factory,
    get_mcp_client,
    get_mcp_service,
)
from tripsage.mcp.neon.client import NeonMCPClient, NeonService
from tripsage.mcp.supabase.client import SupabaseMCPClient, SupabaseService


class TestDatabaseMCPFactory:
    """Tests for the DatabaseMCPFactory class."""

    @patch("src.mcp.db_factory.get_neon_client")
    @patch("src.mcp.db_factory.get_supabase_client")
    def test_get_client_development(self, mock_get_supabase, mock_get_neon):
        """Test get_client method in development environment."""
        # Setup mocks
        mock_neon_client = MagicMock(spec=NeonMCPClient)
        mock_get_neon.return_value = mock_neon_client

        # Mock settings
        with patch("src.mcp.db_factory.settings") as mock_settings:
            mock_settings.environment = "development"

            # Call method
            client = DatabaseMCPFactory.get_client()

            # Verify correct client is returned
            assert client == mock_neon_client
            mock_get_neon.assert_called_once()
            mock_get_supabase.assert_not_called()

    @patch("src.mcp.db_factory.get_neon_client")
    @patch("src.mcp.db_factory.get_supabase_client")
    def test_get_client_production(self, mock_get_supabase, mock_get_neon):
        """Test get_client method in production environment."""
        # Setup mocks
        mock_supabase_client = MagicMock(spec=SupabaseMCPClient)
        mock_get_supabase.return_value = mock_supabase_client

        # Mock settings
        with patch("src.mcp.db_factory.settings") as mock_settings:
            mock_settings.environment = "production"

            # Call method
            client = DatabaseMCPFactory.get_client()

            # Verify correct client is returned
            assert client == mock_supabase_client
            mock_get_supabase.assert_called_once()
            mock_get_neon.assert_not_called()

    @patch("src.mcp.db_factory.NeonService")
    @patch("src.mcp.db_factory.SupabaseService")
    def test_get_service_development(self, mock_supabase_service, mock_neon_service):
        """Test get_service method in development environment."""
        # Setup mocks
        mock_neon = MagicMock(spec=NeonService)
        mock_neon_service.return_value = mock_neon

        # Mock settings
        with patch("src.mcp.db_factory.settings") as mock_settings:
            mock_settings.environment = "development"

            # Call method
            service = DatabaseMCPFactory.get_service()

            # Verify correct service is returned
            assert service == mock_neon
            mock_neon_service.assert_called_once()
            mock_supabase_service.assert_not_called()

    @patch("src.mcp.db_factory.NeonService")
    @patch("src.mcp.db_factory.SupabaseService")
    def test_get_service_production(self, mock_supabase_service, mock_neon_service):
        """Test get_service method in production environment."""
        # Setup mocks
        mock_supabase = MagicMock(spec=SupabaseService)
        mock_supabase_service.return_value = mock_supabase

        # Mock settings
        with patch("src.mcp.db_factory.settings") as mock_settings:
            mock_settings.environment = "production"

            # Call method
            service = DatabaseMCPFactory.get_service()

            # Verify correct service is returned
            assert service == mock_supabase
            mock_supabase_service.assert_called_once()
            mock_neon_service.assert_not_called()

    @patch("src.mcp.db_factory.get_neon_client")
    def test_get_development_client(self, mock_get_neon):
        """Test get_development_client method."""
        # Setup mocks
        mock_neon_client = MagicMock(spec=NeonMCPClient)
        mock_get_neon.return_value = mock_neon_client

        # Call method
        client = DatabaseMCPFactory.get_development_client()

        # Verify correct client is returned
        assert client == mock_neon_client
        mock_get_neon.assert_called_once()

    @patch("src.mcp.db_factory.get_supabase_client")
    def test_get_production_client(self, mock_get_supabase):
        """Test get_production_client method."""
        # Setup mocks
        mock_supabase_client = MagicMock(spec=SupabaseMCPClient)
        mock_get_supabase.return_value = mock_supabase_client

        # Call method
        client = DatabaseMCPFactory.get_production_client()

        # Verify correct client is returned
        assert client == mock_supabase_client
        mock_get_supabase.assert_called_once()

    @patch("src.mcp.db_factory.NeonService")
    def test_get_development_service(self, mock_neon_service):
        """Test get_development_service method."""
        # Setup mocks
        mock_neon = MagicMock(spec=NeonService)
        mock_neon_service.return_value = mock_neon

        # Call method
        service = DatabaseMCPFactory.get_development_service()

        # Verify correct service is returned
        assert service == mock_neon
        mock_neon_service.assert_called_once()

    @patch("src.mcp.db_factory.SupabaseService")
    def test_get_production_service(self, mock_supabase_service):
        """Test get_production_service method."""
        # Setup mocks
        mock_supabase = MagicMock(spec=SupabaseService)
        mock_supabase_service.return_value = mock_supabase

        # Call method
        service = DatabaseMCPFactory.get_production_service()

        # Verify correct service is returned
        assert service == mock_supabase
        mock_supabase_service.assert_called_once()


class TestFactoryFunctions:
    """Tests for standalone factory functions."""

    @patch("src.mcp.db_factory.get_neon_client")
    @patch("src.mcp.db_factory.get_supabase_client")
    def test_get_mcp_client_development(self, mock_get_supabase, mock_get_neon):
        """Test get_mcp_client function in development environment."""
        # Setup mocks
        mock_neon_client = MagicMock(spec=NeonMCPClient)
        mock_get_neon.return_value = mock_neon_client

        # Call function with explicit environment
        client = get_mcp_client("development")

        # Verify correct client is returned
        assert client == mock_neon_client
        mock_get_neon.assert_called_once()
        mock_get_supabase.assert_not_called()

    @patch("src.mcp.db_factory.get_neon_client")
    @patch("src.mcp.db_factory.get_supabase_client")
    def test_get_mcp_client_production(self, mock_get_supabase, mock_get_neon):
        """Test get_mcp_client function in production environment."""
        # Setup mocks
        mock_supabase_client = MagicMock(spec=SupabaseMCPClient)
        mock_get_supabase.return_value = mock_supabase_client

        # Call function with explicit environment
        client = get_mcp_client("production")

        # Verify correct client is returned
        assert client == mock_supabase_client
        mock_get_supabase.assert_called_once()
        mock_get_neon.assert_not_called()

    @patch("src.mcp.db_factory.NeonService")
    @patch("src.mcp.db_factory.SupabaseService")
    def test_get_mcp_service_development(
        self, mock_supabase_service, mock_neon_service
    ):
        """Test get_mcp_service function in development environment."""
        # Setup mocks
        mock_neon = MagicMock(spec=NeonService)
        mock_neon_service.return_value = mock_neon

        # Call function with explicit environment
        service = get_mcp_service("development")

        # Verify correct service is returned
        assert service == mock_neon
        mock_neon_service.assert_called_once()
        mock_supabase_service.assert_not_called()

    @patch("src.mcp.db_factory.NeonService")
    @patch("src.mcp.db_factory.SupabaseService")
    def test_get_mcp_service_production(self, mock_supabase_service, mock_neon_service):
        """Test get_mcp_service function in production environment."""
        # Setup mocks
        mock_supabase = MagicMock(spec=SupabaseService)
        mock_supabase_service.return_value = mock_supabase

        # Call function with explicit environment
        service = get_mcp_service("production")

        # Verify correct service is returned
        assert service == mock_supabase
        mock_supabase_service.assert_called_once()
        mock_neon_service.assert_not_called()


def test_db_mcp_factory_instance():
    """Test that db_mcp_factory is an instance of DatabaseMCPFactory."""
    assert isinstance(db_mcp_factory, DatabaseMCPFactory)
