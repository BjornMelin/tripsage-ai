"""Tests for the database configuration module."""

import os
from unittest.mock import patch

from src.db.config import (
    DatabaseConfig,
    DatabaseProvider,
    NeonConfig,
    SupabaseConfig,
    create_config,
)


class TestConfig:
    """Tests for the database configuration module."""

    def test_supabase_config(self):
        """Test SupabaseConfig model."""
        # Arrange
        url = "https://example.supabase.co"
        anon_key = "test-anon-key"
        service_role_key = "test-service-role-key"
        timeout = 30.0
        auto_refresh_token = True
        persist_session = True

        # Act
        config = SupabaseConfig(
            url=url,
            anon_key=anon_key,
            service_role_key=service_role_key,
            timeout=timeout,
            auto_refresh_token=auto_refresh_token,
            persist_session=persist_session,
        )

        # Assert
        assert config.url == url
        assert config.anon_key.get_secret_value() == anon_key
        assert config.service_role_key.get_secret_value() == service_role_key
        assert config.timeout == timeout
        assert config.auto_refresh_token == auto_refresh_token
        assert config.persist_session == persist_session

    def test_neon_config(self):
        """Test NeonConfig model."""
        # Arrange
        connection_string = "postgresql://user:password@test-host:5432/testdb"
        min_pool_size = 2
        max_pool_size = 20
        max_inactive_connection_lifetime = 120.0

        # Act
        config = NeonConfig(
            connection_string=connection_string,
            min_pool_size=min_pool_size,
            max_pool_size=max_pool_size,
            max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        )

        # Assert
        assert config.connection_string == connection_string
        assert config.min_pool_size == min_pool_size
        assert config.max_pool_size == max_pool_size
        assert (
            config.max_inactive_connection_lifetime == max_inactive_connection_lifetime
        )

    def test_database_config(self):
        """Test DatabaseConfig model."""
        # Arrange
        supabase_config = SupabaseConfig(
            url="https://example.supabase.co", anon_key="test-anon-key"
        )

        # Act
        config = DatabaseConfig(
            provider=DatabaseProvider.SUPABASE, supabase=supabase_config
        )

        # Assert
        assert config.provider == DatabaseProvider.SUPABASE
        assert config.supabase == supabase_config
        assert config.neon is None

    def test_create_config_supabase(self):
        """Test create_config function with Supabase provider."""
        # Arrange
        env_vars = {
            "DB_PROVIDER": "supabase",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
            "SUPABASE_TIMEOUT": "30.0",
            "SUPABASE_AUTO_REFRESH_TOKEN": "True",
            "SUPABASE_PERSIST_SESSION": "True",
        }

        with patch.dict(os.environ, env_vars):
            # Act
            config = create_config()

            # Assert
            assert config.provider == DatabaseProvider.SUPABASE
            assert config.supabase is not None
            assert config.supabase.url == "https://example.supabase.co"
            assert config.supabase.anon_key.get_secret_value() == "test-anon-key"
            assert (
                config.supabase.service_role_key.get_secret_value()
                == "test-service-role-key"
            )
            assert config.supabase.timeout == 30.0
            assert config.supabase.auto_refresh_token is True
            assert config.supabase.persist_session is True
            assert config.neon is None

    def test_create_config_neon(self):
        """Test create_config function with Neon provider."""
        # Arrange
        env_vars = {
            "DB_PROVIDER": "neon",
            "NEON_CONNECTION_STRING": "postgresql://user:password@test-host:5432/testdb",
            "NEON_MIN_POOL_SIZE": "2",
            "NEON_MAX_POOL_SIZE": "20",
            "NEON_MAX_INACTIVE_CONNECTION_LIFETIME": "120.0",
        }

        with patch.dict(os.environ, env_vars):
            # Act
            config = create_config()

            # Assert
            assert config.provider == DatabaseProvider.NEON
            assert config.neon is not None
            assert (
                config.neon.connection_string
                == "postgresql://user:password@test-host:5432/testdb"
            )
            assert config.neon.min_pool_size == 2
            assert config.neon.max_pool_size == 20
            assert config.neon.max_inactive_connection_lifetime == 120.0
            assert config.supabase is None

    def test_create_config_fallback_to_supabase(self):
        """Test create_config falls back to Supabase if Neon config is missing."""
        # Arrange
        env_vars = {
            "DB_PROVIDER": "neon",  # Specified Neon but no connection string
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
        }

        with patch.dict(os.environ, env_vars):
            # Act
            config = create_config()

            # Assert
            assert config.provider == DatabaseProvider.SUPABASE
            assert config.supabase is not None
            assert config.neon is None

    def test_create_config_default_provider(self):
        """Test create_config uses default provider when not specified."""
        # Arrange
        env_vars = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
        }

        with patch.dict(
            os.environ, {k: v for k, v in env_vars.items() if k != "DB_PROVIDER"}
        ):
            # Act
            config = create_config()

            # Assert
            assert config.provider == DatabaseProvider.SUPABASE
            assert config.supabase is not None
