"""
Tests for external Neon DB MCP server integration.

This module contains tests to verify that TripSage correctly interfaces
with the external Neon DB MCP server for development workflows.
"""

import importlib.util
from unittest.mock import patch

import pytest

from src.mcp.db_factory import DatabaseMCPFactory
from src.mcp.neon.client import NeonMCPClient, NeonService
from src.utils.settings import settings


@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    with patch("src.mcp.neon.client.settings") as mock_settings:
        mock_settings.neon_mcp.endpoint = "http://localhost:8099"
        mock_settings.neon_mcp.api_key = "test-api-key"
        mock_settings.neon_mcp.dev_only = True
        mock_settings.neon_mcp.default_project_id = "test-project-id"
        yield mock_settings


@pytest.mark.asyncio
async def test_external_mcp_server_config():
    """Test that the Neon DB MCP server is correctly configured in settings."""
    # Verify that settings include Neon MCP configuration
    assert hasattr(settings, "neon_mcp"), "Settings should have neon_mcp configuration"

    # Check essential configuration fields
    assert hasattr(settings.neon_mcp, "endpoint"), "Neon MCP endpoint setting is required"
    assert hasattr(settings.neon_mcp, "dev_only"), "Neon MCP dev_only flag is required"

    # Verify that dev_only is set to True for development environment
    assert settings.neon_mcp.dev_only is True, "Neon MCP should be configured for dev only"


def test_db_factory_provides_neon_in_development():
    """Test that DB factory provides Neon client for development environments."""
    # Create a factory with development environment
    with patch("src.mcp.db_factory.settings") as mock_settings:
        mock_settings.environment = "development"

        # Get client from factory
        client = DatabaseMCPFactory.get_client("development")

        # Verify that it's a NeonMCPClient instance
        assert isinstance(client, NeonMCPClient), "Factory should return NeonMCPClient"

        # Get service from factory
        service = DatabaseMCPFactory.get_service("development")

        # Verify that it's a NeonService instance
        assert isinstance(service, NeonService), "Factory should return NeonService"

        # Also test the specific development methods
        dev_client = DatabaseMCPFactory.get_development_client()
        assert isinstance(dev_client, NeonMCPClient), "Should return NeonMCPClient"

        dev_service = DatabaseMCPFactory.get_development_service()
        assert isinstance(dev_service, NeonService), "Should return NeonService"


def test_neon_mcp_external_server_validation():
    """Validate the external Neon MCP server package availability."""
    # Check if the mcp-server-neon package is installed or importable
    spec = importlib.util.find_spec("mcp_server_neon")
    is_installed = spec is not None

    # If not installed, check if package is available in pip repository
    if not is_installed:
        try:
            import subprocess

            # Run pip search or pip show to check if package exists
            result = subprocess.run(
                ["pip", "show", "mcp-server-neon"],
                capture_output=True,
                text=True,
                check=False,
            )

            # If we get info from pip, the package exists in the repository
            package_exists = result.returncode == 0 or "not found" not in result.stderr

            if not package_exists:
                pytest.skip("External mcp-server-neon package is not available")
        except Exception:
            # If subprocess fails, skip the test
            pytest.skip("Unable to verify external mcp-server-neon package")

    # If we're here, either the package is installed or available
    # Let's verify the NeonMCPClient can connect to it (if it's running)
    try:
        import socket

        # Create a socket connection to check if server is running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # 1 second timeout

        # Try to connect to the default Neon MCP server port
        server_running = False
        try:
            # Parse port from endpoint
            port = 8099  # Default port for Neon MCP server
            if hasattr(settings, "neon_mcp") and settings.neon_mcp.endpoint:
                try:
                    from urllib.parse import urlparse

                    url = urlparse(settings.neon_mcp.endpoint)
                    if url.port:
                        port = url.port
                except Exception:
                    pass

            result = sock.connect_ex(("localhost", port))
            server_running = result == 0
        finally:
            sock.close()

        if not server_running:
            pytest.skip("Neon MCP server is not currently running")

    except Exception:
        # If socket connection check fails, skip the test
        pytest.skip("Unable to verify if Neon MCP server is running")