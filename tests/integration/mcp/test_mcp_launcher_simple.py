"""Simple isolated tests for the MCP launcher script."""

from unittest.mock import MagicMock, patch

import pytest

# Mock settings directly to avoid dependencies
mock_settings = MagicMock()
mock_settings.supabase = MagicMock(enabled=True, command="supabase", runtime="python")
mock_settings.neo4j_memory = MagicMock(enabled=True, command="neo4j", runtime="python")

with patch("scripts.mcp.mcp_launcher.MCPSettings", return_value=mock_settings):
    from scripts.mcp.mcp_launcher import MCPLauncher


class TestMCPLauncher:
    """Test suite for MCPLauncher"""

    @pytest.fixture
    def launcher(self):
        """Create launcher instance with mocked settings"""
        launcher = MCPLauncher(mock_settings)
        return launcher

    @pytest.mark.asyncio
    async def test_start_server_success(self, launcher):
        """Test successful server start"""
        with patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.poll.return_value = None
            mock_popen.return_value = proc

            result = await launcher.start_server("supabase")

            assert result is True
            assert "supabase" in launcher.servers
            mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_server_success(self, launcher):
        """Test successful server stop"""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        launcher.servers["supabase"] = mock_proc

        result = await launcher.stop_server("supabase")

        assert result is True
        assert "supabase" not in launcher.servers
        mock_proc.terminate.assert_called_once()

    def test_list_servers(self, launcher):
        """Test listing servers"""
        launcher.servers["supabase"] = MagicMock()

        servers = launcher.list_servers()

        assert "supabase" in servers
        assert "running" in servers["supabase"]["status"]
