"""Tests for the unified MCP launcher script."""

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.mcp.mcp_launcher import MCPLauncher, ServerRuntime


class TestMCPLauncher:
    """Test suite for MCPLauncher"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock MCP settings"""
        with patch("scripts.mcp.mcp_launcher.MCPSettings") as mock:
            settings = MagicMock()
            settings.supabase.server_url = "http://localhost:54321"
            settings.supabase.supabase_key = "test-key"
            settings.neo4j_memory.server_url = "neo4j://localhost:7687"
            settings.neo4j_memory.neo4j_username = "neo4j"
            settings.neo4j_memory.neo4j_password = "password"
            mock.return_value = settings
            yield settings

    @pytest.fixture
    def launcher(self, mock_settings):
        """Create launcher instance with mocked settings"""
        return MCPLauncher(mock_settings)

    def test_load_server_configs(self, launcher):
        """Test server configuration loading"""
        configs = launcher.configs

        assert "supabase" in configs
        assert configs["supabase"].runtime == ServerRuntime.NODE
        assert configs["supabase"].command == "npx"
        assert configs["supabase"].args == ["-y", "supabase-mcp"]

        assert "neo4j_memory" in configs
        assert configs["neo4j_memory"].runtime == ServerRuntime.NODE

        assert "crawl4ai" in configs
        assert configs["crawl4ai"].runtime == ServerRuntime.PYTHON
        assert configs["crawl4ai"].command == "python"

    @pytest.mark.asyncio
    async def test_start_server_success(self, launcher):
        """Test successful server start"""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = await launcher.start_server("supabase")

            assert result is True
            assert "supabase" in launcher.servers
            assert launcher.servers["supabase"] == mock_process
            mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_server_already_running(self, launcher):
        """Test starting an already running server"""
        launcher.servers["supabase"] = MagicMock()

        result = await launcher.start_server("supabase")

        assert result is True  # Still returns True but doesn't start new process

    @pytest.mark.asyncio
    async def test_start_server_unknown(self, launcher):
        """Test starting an unknown server"""
        result = await launcher.start_server("unknown")

        assert result is False

    @pytest.mark.asyncio
    async def test_start_server_error(self, launcher):
        """Test server start failure"""
        with patch("subprocess.Popen", side_effect=Exception("Failed to start")):
            result = await launcher.start_server("supabase")

            assert result is False
            assert "supabase" not in launcher.servers

    @pytest.mark.asyncio
    async def test_stop_server_success(self, launcher):
        """Test successful server stop"""
        mock_process = MagicMock()
        launcher.servers["supabase"] = mock_process

        result = await launcher.stop_server("supabase")

        assert result is True
        assert "supabase" not in launcher.servers
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    @pytest.mark.asyncio
    async def test_stop_server_force_kill(self, launcher):
        """Test force killing a server that won't terminate"""
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        launcher.servers["supabase"] = mock_process

        result = await launcher.stop_server("supabase")

        assert result is True
        assert "supabase" not in launcher.servers
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_server_not_running(self, launcher):
        """Test stopping a server that's not running"""
        result = await launcher.stop_server("supabase")

        assert result is True  # Returns True even if not running

    @pytest.mark.asyncio
    async def test_start_all(self, launcher):
        """Test starting all servers"""
        launcher.configs["supabase"].auto_start = True
        launcher.configs["neo4j_memory"].auto_start = False

        with patch.object(
            launcher, "start_server", new_callable=AsyncMock
        ) as mock_start:
            mock_start.return_value = True

            results = await launcher.start_all(auto_only=True)

            assert results == {"supabase": True}
            mock_start.assert_called_once_with("supabase")

    @pytest.mark.asyncio
    async def test_start_all_no_filter(self, launcher):
        """Test starting all servers without filtering"""
        with patch.object(
            launcher, "start_server", new_callable=AsyncMock
        ) as mock_start:
            mock_start.return_value = True

            results = await launcher.start_all(auto_only=False)

            assert len(results) == len(launcher.configs)
            assert all(results.values())

    @pytest.mark.asyncio
    async def test_stop_all(self, launcher):
        """Test stopping all servers"""
        launcher.servers = {"supabase": MagicMock(), "neo4j_memory": MagicMock()}

        with patch.object(launcher, "stop_server", new_callable=AsyncMock) as mock_stop:
            mock_stop.return_value = True

            results = await launcher.stop_all()

            assert results == {"supabase": True, "neo4j_memory": True}
            assert mock_stop.call_count == 2

    def test_list_servers(self, launcher):
        """Test listing servers and their status"""
        launcher.servers = {"supabase": MagicMock()}

        status = launcher.list_servers()

        assert status["supabase"] == "running"
        assert status["neo4j_memory"] == "stopped"

    @pytest.mark.asyncio
    async def test_health_check_running(self, launcher):
        """Test health check for running server"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        launcher.servers["supabase"] = mock_process

        result = await launcher.health_check("supabase")

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_stopped(self, launcher):
        """Test health check for stopped server"""
        result = await launcher.health_check("supabase")

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_crashed(self, launcher):
        """Test health check for crashed server"""
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Exited with error
        launcher.servers["supabase"] = mock_process

        result = await launcher.health_check("supabase")

        assert result is False
