"""
Tests for Supabase MCP Settings Configuration.

This module tests the SupabaseMCPConfig class and its integration
with the broader MCP settings system.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from tripsage.config.mcp_settings import (
    MCPSettings,
    RuntimeType,
    SupabaseMCPConfig,
    TransportType,
)


class TestSupabaseMCPConfig:
    """Tests for SupabaseMCPConfig."""

    def test_default_configuration(self):
        """Test SupabaseMCPConfig with default values."""
        config = SupabaseMCPConfig()

        # Check defaults
        assert config.enabled is True
        assert config.runtime == RuntimeType.NODE
        assert config.transport == TransportType.STDIO
        assert config.command == "npx"
        assert config.access_token.get_secret_value() == "test-access-token"
        assert config.project_ref is None
        assert config.read_only is False

        # Check default args
        expected_args = [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            "test-access-token",  # Should be replaced from secret
        ]
        assert config.args == expected_args

    def test_configuration_with_project_ref(self):
        """Test SupabaseMCPConfig with project_ref."""
        config = SupabaseMCPConfig(
            access_token=SecretStr("my-token"), project_ref="my-project-123"
        )

        # Check that project ref is added to args
        expected_args = [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            "my-token",
            "--project-ref",
            "my-project-123",
        ]
        assert config.args == expected_args

    def test_configuration_with_read_only(self):
        """Test SupabaseMCPConfig with read_only enabled."""
        config = SupabaseMCPConfig(access_token=SecretStr("my-token"), read_only=True)

        # Check that read-only flag is added to args
        expected_args = [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            "my-token",
            "--read-only",
        ]
        assert config.args == expected_args

    def test_configuration_with_all_options(self):
        """Test SupabaseMCPConfig with all options set."""
        config = SupabaseMCPConfig(
            access_token=SecretStr("my-token"),
            project_ref="my-project-123",
            read_only=True,
            timeout=60,
            retry_attempts=5,
        )

        # Check configuration
        assert config.access_token.get_secret_value() == "my-token"
        assert config.project_ref == "my-project-123"
        assert config.read_only is True
        assert config.timeout == 60
        assert config.retry_attempts == 5

        # Check args
        expected_args = [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            "my-token",
            "--project-ref",
            "my-project-123",
            "--read-only",
        ]
        assert config.args == expected_args

    def test_token_replacement_in_args(self):
        """Test that token placeholder is correctly replaced."""
        # Start with custom args that include the placeholder
        config = SupabaseMCPConfig(
            args=[
                "-y",
                "@supabase/mcp-server-supabase@latest",
                "--access-token",
                "${SUPABASE_ACCESS_TOKEN}",
                "--some-other-flag",
            ],
            access_token=SecretStr("secret-token-123"),
        )

        expected_args = [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            "secret-token-123",
            "--some-other-flag",
        ]
        assert config.args == expected_args

    def test_env_prefix(self):
        """Test that environment variable prefix is correct."""
        assert SupabaseMCPConfig.model_config["env_prefix"] == "TRIPSAGE_MCP_SUPABASE_"

    @patch.dict(
        os.environ,
        {
            "TRIPSAGE_MCP_SUPABASE_ACCESS_TOKEN": "env-token",
            "TRIPSAGE_MCP_SUPABASE_PROJECT_REF": "env-project",
            "TRIPSAGE_MCP_SUPABASE_READ_ONLY": "true",
            "TRIPSAGE_MCP_SUPABASE_ENABLED": "false",
        },
    )
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        config = SupabaseMCPConfig()

        assert config.access_token.get_secret_value() == "env-token"
        assert config.project_ref == "env-project"
        assert config.read_only is True
        assert config.enabled is False

    def test_disabled_configuration(self):
        """Test SupabaseMCPConfig when disabled."""
        config = SupabaseMCPConfig(enabled=False)

        assert config.enabled is False
        # Other settings should still be valid
        assert config.runtime == RuntimeType.NODE
        assert config.transport == TransportType.STDIO


class TestSupabaseMCPConfigValidation:
    """Tests for SupabaseMCPConfig validation."""

    def test_invalid_timeout(self):
        """Test that invalid timeout values are rejected."""
        with pytest.raises(ValidationError):
            SupabaseMCPConfig(timeout=-1)

        with pytest.raises(ValidationError):
            SupabaseMCPConfig(timeout=500)  # Too high

    def test_invalid_retry_attempts(self):
        """Test that invalid retry_attempts values are rejected."""
        with pytest.raises(ValidationError):
            SupabaseMCPConfig(retry_attempts=-1)

        with pytest.raises(ValidationError):
            SupabaseMCPConfig(retry_attempts=15)  # Too high

    def test_valid_timeout_range(self):
        """Test valid timeout values."""
        # Minimum
        config = SupabaseMCPConfig(timeout=1)
        assert config.timeout == 1

        # Maximum
        config = SupabaseMCPConfig(timeout=300)
        assert config.timeout == 300

        # Middle value
        config = SupabaseMCPConfig(timeout=60)
        assert config.timeout == 60

    def test_valid_retry_attempts_range(self):
        """Test valid retry_attempts values."""
        # Minimum
        config = SupabaseMCPConfig(retry_attempts=0)
        assert config.retry_attempts == 0

        # Maximum
        config = SupabaseMCPConfig(retry_attempts=10)
        assert config.retry_attempts == 10

        # Middle value
        config = SupabaseMCPConfig(retry_attempts=3)
        assert config.retry_attempts == 3


class TestMCPSettingsIntegration:
    """Tests for Supabase integration with MCPSettings."""

    def test_supabase_in_mcp_settings(self):
        """Test that Supabase is included in MCPSettings."""
        settings = MCPSettings()

        assert hasattr(settings, "supabase")
        assert isinstance(settings.supabase, SupabaseMCPConfig)

    def test_mcp_settings_with_custom_supabase(self):
        """Test MCPSettings with custom Supabase configuration."""
        custom_supabase = SupabaseMCPConfig(
            access_token=SecretStr("custom-token"),
            project_ref="custom-project",
            read_only=True,
        )

        settings = MCPSettings(supabase=custom_supabase)

        assert settings.supabase.access_token.get_secret_value() == "custom-token"
        assert settings.supabase.project_ref == "custom-project"
        assert settings.supabase.read_only is True

    def test_get_enabled_mcps_includes_supabase(self):
        """Test that get_enabled_mcps includes Supabase when enabled."""
        settings = MCPSettings()

        # By default, Supabase should be enabled
        enabled_mcps = settings.get_enabled_mcps()
        assert "supabase" in enabled_mcps
        assert enabled_mcps["supabase"]["enabled"] is True

    def test_get_enabled_mcps_excludes_disabled_supabase(self):
        """Test that get_enabled_mcps excludes Supabase when disabled."""
        disabled_supabase = SupabaseMCPConfig(enabled=False)
        settings = MCPSettings(supabase=disabled_supabase)

        enabled_mcps = settings.get_enabled_mcps()
        assert "supabase" not in enabled_mcps

    @patch.dict(
        os.environ,
        {
            "TRIPSAGE_MCP_SUPABASE_ACCESS_TOKEN": "test-env-token",
            "TRIPSAGE_MCP_SUPABASE_ENABLED": "true",
        },
    )
    def test_mcp_settings_from_environment(self):
        """Test loading MCPSettings from environment."""
        settings = MCPSettings()

        assert settings.supabase.access_token.get_secret_value() == "test-env-token"
        assert settings.supabase.enabled is True


class TestSupabaseMCPConfigEdgeCases:
    """Tests for edge cases in SupabaseMCPConfig."""

    def test_empty_access_token(self):
        """Test behavior with empty access token."""
        config = SupabaseMCPConfig(access_token=SecretStr(""))

        # Should still work, but args will have empty token
        assert "" in config.args

    def test_none_access_token(self):
        """Test behavior with None access token."""
        # This should use the default value
        config = SupabaseMCPConfig()
        config.access_token = None

        # The validator should handle None case gracefully
        # (in practice, Pydantic would use the default)

    def test_very_long_project_ref(self):
        """Test with a very long project reference."""
        long_ref = "a" * 1000
        config = SupabaseMCPConfig(
            access_token=SecretStr("token"), project_ref=long_ref
        )

        assert config.project_ref == long_ref
        assert long_ref in config.args

    def test_special_characters_in_token(self):
        """Test with special characters in access token."""
        special_token = "token-with-special-chars!@#$%^&*()_+"
        config = SupabaseMCPConfig(access_token=SecretStr(special_token))

        assert config.access_token.get_secret_value() == special_token
        assert special_token in config.args

    def test_multiple_placeholders_in_args(self):
        """Test args with multiple placeholders."""
        config = SupabaseMCPConfig(
            args=[
                "${SUPABASE_ACCESS_TOKEN}",
                "--flag",
                "${SUPABASE_ACCESS_TOKEN}",  # Duplicate
                "--another-flag",
            ],
            access_token=SecretStr("my-token"),
        )

        expected_args = ["my-token", "--flag", "my-token", "--another-flag"]
        assert config.args == expected_args


def test_import_and_basic_functionality():
    """Test that imports work and basic functionality is available."""
    from tripsage.config.mcp_settings import mcp_settings

    # Should be able to access supabase config
    supabase_config = mcp_settings.supabase
    assert isinstance(supabase_config, SupabaseMCPConfig)

    # Should have basic properties
    assert hasattr(supabase_config, "access_token")
    assert hasattr(supabase_config, "project_ref")
    assert hasattr(supabase_config, "read_only")
    assert hasattr(supabase_config, "enabled")
