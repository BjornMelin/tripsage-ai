"""Tests for the MCP Configuration Management System."""

import os
from unittest import mock

import pytest
from pydantic import ValidationError

from tripsage.config.mcp_settings import (
    BaseMCPConfig,
    MCPSettings,
    PlaywrightMCPConfig,
    RestMCPConfig,
    get_mcp_settings,
)


class TestBaseMCPConfig:
    """Test base MCP configuration functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BaseMCPConfig()
        assert config.enabled is True
        assert config.timeout == 30
        assert config.retry_attempts == 3
        assert config.retry_backoff == 1.0
        assert config.log_level == "INFO"

    def test_validation(self):
        """Test configuration validation."""
        # Test timeout validation
        with pytest.raises(ValidationError):
            BaseMCPConfig(timeout=0)  # Too small

        with pytest.raises(ValidationError):
            BaseMCPConfig(timeout=301)  # Too large

        # Test retry_attempts validation
        with pytest.raises(ValidationError):
            BaseMCPConfig(retry_attempts=-1)  # Negative value

        with pytest.raises(ValidationError):
            BaseMCPConfig(retry_attempts=11)  # Too many

        # Test log_level validation
        with pytest.raises(ValidationError):
            BaseMCPConfig(log_level="INVALID")  # Invalid log level

    def test_custom_values(self):
        """Test setting custom configuration values."""
        config = BaseMCPConfig(
            enabled=False,
            timeout=60,
            retry_attempts=5,
            retry_backoff=2.0,
            log_level="DEBUG",
        )
        assert config.enabled is False
        assert config.timeout == 60
        assert config.retry_attempts == 5
        assert config.retry_backoff == 2.0
        assert config.log_level == "DEBUG"


class TestRestMCPConfig:
    """Test REST MCP configuration functionality."""

    def test_required_fields(self):
        """Test required fields validation."""
        with pytest.raises(ValidationError):
            RestMCPConfig()  # Missing url and api_key

    def test_valid_config(self):
        """Test valid configuration."""
        config = RestMCPConfig(url="https://example.com/api", api_key="test_key")
        assert (
            str(config.url) == "https://example.com/api/"
        )  # Note trailing slash added
        assert config.api_key.get_secret_value() == "test_key"
        assert config.headers == {}
        assert config.max_connections == 10

    def test_url_validation(self):
        """Test URL validation and normalization."""
        # Test URL without trailing slash gets one added
        config = RestMCPConfig(url="https://example.com/api", api_key="test_key")
        assert str(config.url) == "https://example.com/api/"

        # Test URL with trailing slash remains the same
        config = RestMCPConfig(url="https://example.com/api/", api_key="test_key")
        assert str(config.url) == "https://example.com/api/"

        # Test invalid URL
        with pytest.raises(ValidationError):
            RestMCPConfig(url="not-a-url", api_key="test_key")


class TestPlaywrightMCPConfig:
    """Test Playwright MCP configuration functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        # We need to provide required values from parent class
        config = PlaywrightMCPConfig(url="https://example.com/api", api_key="test_key")
        assert config.headless is True
        assert config.browser_type == "chromium"
        assert config.screenshot_dir is None
        assert config.timeout_page == 60
        assert config.timeout_navigation == 30
        assert config.session_persistence is True

    def test_env_prefix(self):
        """Test environment variable prefix."""
        assert (
            PlaywrightMCPConfig.model_config["env_prefix"] == "TRIPSAGE_MCP_PLAYWRIGHT_"
        )


class TestMCPSettings:
    """Test MCPSettings functionality."""

    def test_get_enabled_mcps(self):
        """Test get_enabled_mcps method."""
        # Create settings with some MCPs disabled
        settings = MCPSettings()
        settings.playwright.enabled = False
        settings.crawl4ai.enabled = True
        settings.firecrawl.enabled = True
        settings.supabase.enabled = False

        enabled_mcps = settings.get_enabled_mcps()

        # Check that only enabled MCPs are in the result
        assert "playwright" not in enabled_mcps
        assert "crawl4ai" in enabled_mcps
        assert "firecrawl" in enabled_mcps
        assert "supabase" not in enabled_mcps

    def test_model_validator_warnings(self, caplog):
        """Test model validator warning logging."""
        # Create settings with all web crawling MCPs disabled
        settings = MCPSettings()
        settings.crawl4ai.enabled = False
        settings.firecrawl.enabled = False

        # Create settings with all database MCPs disabled
        settings.supabase.enabled = False
        settings.neo4j_memory.enabled = False

        # Run validation to trigger warnings
        settings.validate_settings()

        # Check warning logs
        assert "No web crawling MCP is enabled" in caplog.text
        assert "No database MCP is enabled" in caplog.text


@mock.patch.dict(
    os.environ,
    {
        "TRIPSAGE_MCP_PLAYWRIGHT_ENABLED": "false",
        "TRIPSAGE_MCP_PLAYWRIGHT_URL": "https://playwright.example.com",
        "TRIPSAGE_MCP_PLAYWRIGHT_API_KEY": "playwright_test_key",
        "TRIPSAGE_MCP_PLAYWRIGHT_BROWSER_TYPE": "firefox",
        "TRIPSAGE_MCP_CRAWLER4AI_ENABLED": "true",
        "TRIPSAGE_MCP_CRAWLER4AI_URL": "https://crawl4ai.example.com",
        "TRIPSAGE_MCP_CRAWLER4AI_API_KEY": "crawl4ai_test_key",
    },
)
def test_load_from_environment_variables():
    """Test loading settings from environment variables."""
    # Clear the LRU cache to ensure we load from environment variables
    get_mcp_settings.cache_clear()

    # Get settings (should load from environment variables)
    settings = get_mcp_settings()

    # Check that environment variables were applied
    assert settings.playwright.enabled is False
    assert str(settings.playwright.url) == "https://playwright.example.com/"
    assert settings.playwright.api_key.get_secret_value() == "playwright_test_key"
    assert settings.playwright.browser_type == "firefox"

    # Check other settings have default values
    assert settings.time.enabled is True
    assert settings.weather.enabled is True


def test_settings_singleton():
    """Test that get_mcp_settings returns a singleton instance."""
    # Get settings twice
    settings1 = get_mcp_settings()
    settings2 = get_mcp_settings()

    # They should be the same object
    assert settings1 is settings2
