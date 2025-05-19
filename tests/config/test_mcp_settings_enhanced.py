"""Tests for enhanced MCP settings with runtime and transport options."""

import pytest
from pydantic import ValidationError

from tripsage.config.mcp_settings import (
    BaseMCPConfig,
    Crawl4AIMCPConfig,
    MCPSettings,
    RestMCPConfig,
    RuntimeType,
    TransportType,
)


class TestEnhancedMCPSettings:
    """Test suite for enhanced MCP settings"""

    def test_base_config_defaults(self):
        """Test BaseMCPConfig default values"""
        config = BaseMCPConfig()

        assert config.enabled is True
        assert config.runtime == RuntimeType.NODE
        assert config.transport == TransportType.STDIO
        assert config.command is None
        assert config.args == []
        assert config.env == {}
        assert config.auto_start is False
        assert config.health_check_endpoint is None

    def test_base_config_custom_values(self):
        """Test BaseMCPConfig with custom values"""
        config = BaseMCPConfig(
            runtime=RuntimeType.PYTHON,
            transport=TransportType.HTTP,
            command="python",
            args=["-m", "server"],
            env={"KEY": "value"},
            auto_start=True,
            health_check_endpoint="/health",
        )

        assert config.runtime == RuntimeType.PYTHON
        assert config.transport == TransportType.HTTP
        assert config.command == "python"
        assert config.args == ["-m", "server"]
        assert config.env == {"KEY": "value"}
        assert config.auto_start is True
        assert config.health_check_endpoint == "/health"

    def test_rest_config_defaults(self):
        """Test RestMCPConfig default transport override"""
        config = RestMCPConfig(
            url="http://localhost:8080",
            api_key="test-key",  # type: ignore
        )

        assert config.transport == TransportType.HTTP
        assert config.runtime == RuntimeType.NODE  # Inherited default

    def test_crawl4ai_config_overrides(self):
        """Test Crawl4AI config with runtime and transport overrides"""
        config = Crawl4AIMCPConfig(api_key="test-key")  # type: ignore

        assert config.runtime == RuntimeType.PYTHON
        assert config.transport == TransportType.WEBSOCKET
        assert str(config.url) == "ws://localhost:11235/mcp/ws/"

    def test_transport_type_enum(self):
        """Test TransportType enum values"""
        assert TransportType.STDIO == "stdio"
        assert TransportType.HTTP == "http"
        assert TransportType.HTTPSSE == "httpsse"
        assert TransportType.WEBSOCKET == "ws"

    def test_runtime_type_enum(self):
        """Test RuntimeType enum values"""
        assert RuntimeType.PYTHON == "python"
        assert RuntimeType.NODE == "node"
        assert RuntimeType.BINARY == "binary"

    def test_config_validation_invalid_runtime(self):
        """Test config validation with invalid runtime"""
        with pytest.raises(ValidationError):
            BaseMCPConfig(runtime="invalid")  # type: ignore

    def test_config_validation_invalid_transport(self):
        """Test config validation with invalid transport"""
        with pytest.raises(ValidationError):
            BaseMCPConfig(transport="invalid")  # type: ignore

    def test_settings_with_runtime_configs(self):
        """Test MCPSettings with runtime configurations"""
        settings = MCPSettings()

        # Check defaults are properly inherited
        assert settings.supabase.runtime == RuntimeType.NODE
        assert settings.supabase.transport == TransportType.STDIO

        assert settings.crawl4ai.runtime == RuntimeType.PYTHON
        assert settings.crawl4ai.transport == TransportType.WEBSOCKET

        assert settings.firecrawl.runtime == RuntimeType.NODE
        assert settings.firecrawl.transport == TransportType.HTTP

    def test_config_with_command_and_args(self):
        """Test config with command and args"""
        config = BaseMCPConfig(
            command="npx",
            args=["-y", "test-server", "--port", "8080"],
        )

        assert config.command == "npx"
        assert config.args == ["-y", "test-server", "--port", "8080"]

    def test_config_env_variables(self):
        """Test config with environment variables"""
        config = BaseMCPConfig(
            env={
                "API_KEY": "secret",
                "PORT": "8080",
                "DEBUG": "true",
            }
        )

        assert config.env["API_KEY"] == "secret"
        assert config.env["PORT"] == "8080"
        assert config.env["DEBUG"] == "true"

    def test_auto_start_configuration(self):
        """Test auto_start configuration"""
        config1 = BaseMCPConfig(auto_start=True)
        config2 = BaseMCPConfig(auto_start=False)

        assert config1.auto_start is True
        assert config2.auto_start is False

    def test_health_check_endpoint(self):
        """Test health check endpoint configuration"""
        config = RestMCPConfig(
            url="http://localhost:8080",
            api_key="test-key",  # type: ignore
            health_check_endpoint="/api/health",
        )

        assert config.health_check_endpoint == "/api/health"
