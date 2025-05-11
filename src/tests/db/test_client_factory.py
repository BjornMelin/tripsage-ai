"""Tests for the database client and factory modules."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.client import (
    close_db_client,
    create_db_client,
    create_supabase_client,
    get_db_client,
    get_supabase_client,
    reset_client,
)
from src.db.config import DatabaseProvider, config
from src.db.factory import create_provider, get_provider, reset_provider
from src.db.providers import NeonProvider, SupabaseProvider


class TestFactory:
    """Tests for the factory module."""

    def test_create_provider_supabase(self, mock_supabase_config):
        """Test creating a Supabase provider."""
        # Arrange
        with patch("src.db.factory.config.provider", DatabaseProvider.SUPABASE):
            with patch("src.db.factory.config.supabase", mock_supabase_config):
                # Act
                provider = create_provider()

                # Assert
                assert isinstance(provider, SupabaseProvider)
                assert provider.url == mock_supabase_config.url

    def test_create_provider_neon(self, mock_neon_config):
        """Test creating a Neon provider."""
        # Arrange
        with patch("src.db.factory.config.provider", DatabaseProvider.NEON):
            with patch("src.db.factory.config.neon", mock_neon_config):
                # Act
                provider = create_provider()

                # Assert
                assert isinstance(provider, NeonProvider)
                assert provider.connection_string == mock_neon_config.connection_string

    def test_create_provider_missing_config(self):
        """Test creating a provider with missing configuration."""
        # Arrange
        with patch("src.db.factory.config.provider", DatabaseProvider.SUPABASE):
            with patch("src.db.factory.config.supabase", None):
                # Act and Assert
                with pytest.raises(ValueError) as excinfo:
                    create_provider()

                assert "Supabase configuration is missing" in str(excinfo.value)

    def test_create_provider_unsupported(self):
        """Test creating a provider with an unsupported type."""
        # Arrange
        with patch("src.db.factory.config.provider", "unsupported"):
            # Act and Assert
            with pytest.raises(ValueError) as excinfo:
                create_provider()

            assert "Unsupported database provider" in str(excinfo.value)

    def test_get_provider_new(self):
        """Test getting a new provider."""
        # Arrange
        mock_provider = MagicMock()

        with patch("src.db.factory._provider", None):
            with patch("src.db.factory.create_provider", return_value=mock_provider):
                # Act
                provider = get_provider()

                # Assert
                assert provider is mock_provider

    def test_get_provider_existing(self):
        """Test getting an existing provider."""
        # Arrange
        mock_provider = MagicMock()

        with patch("src.db.factory._provider", mock_provider):
            with patch("src.db.factory.create_provider") as mock_create:
                # Act
                provider = get_provider()

                # Assert
                assert provider is mock_provider
                mock_create.assert_not_called()

    def test_get_provider_force_new(self):
        """Test getting a new provider with force_new=True."""
        # Arrange
        existing_provider = MagicMock()
        new_provider = MagicMock()

        with patch("src.db.factory._provider", existing_provider):
            with patch("src.db.factory.create_provider", return_value=new_provider):
                # Act
                provider = get_provider(force_new=True)

                # Assert
                assert provider is new_provider

    def test_reset_provider(self):
        """Test resetting the provider."""
        # Arrange
        mock_provider = MagicMock()

        with patch("src.db.factory._provider", mock_provider):
            # Act
            reset_provider()

            # Assert
            with patch("src.db.factory._provider", None):
                assert True  # Provider was reset


class TestClient:
    """Tests for the client module."""

    async def test_create_db_client(self):
        """Test creating and connecting to a database client."""
        # Arrange
        mock_provider = MagicMock()
        mock_provider.connect = AsyncMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            # Act
            provider = await create_db_client()

            # Assert
            assert provider is mock_provider
            mock_provider.connect.assert_called_once()

    async def test_create_db_client_error(self):
        """Test error handling when creating a database client."""
        # Arrange
        mock_provider = MagicMock()
        mock_provider.connect = AsyncMock(side_effect=Exception("Connection failed"))

        with patch("src.db.client.get_provider", return_value=mock_provider):
            # Act and Assert
            with pytest.raises(Exception) as excinfo:
                await create_db_client()

            assert "Connection failed" in str(excinfo.value)

    async def test_get_db_client_connected(self):
        """Test getting a connected database client."""
        # Arrange
        mock_provider = MagicMock()
        mock_provider.is_connected = True
        mock_provider.connect = AsyncMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            # Act
            provider = await get_db_client()

            # Assert
            assert provider is mock_provider
            mock_provider.connect.assert_not_called()

    async def test_get_db_client_not_connected(self):
        """Test getting a database client that's not connected."""
        # Arrange
        mock_provider = MagicMock()
        mock_provider.is_connected = False
        mock_provider.connect = AsyncMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            # Act
            provider = await get_db_client()

            # Assert
            assert provider is mock_provider
            mock_provider.connect.assert_called_once()

    async def test_close_db_client(self):
        """Test closing a database client."""
        # Arrange
        mock_provider = MagicMock()
        mock_provider.is_connected = True
        mock_provider.disconnect = AsyncMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            with patch("src.db.client.reset_provider") as mock_reset:
                # Act
                await close_db_client()

                # Assert
                mock_provider.disconnect.assert_called_once()
                mock_reset.assert_called_once()

    async def test_close_db_client_not_connected(self):
        """Test closing a database client that's not connected."""
        # Arrange
        mock_provider = MagicMock()
        mock_provider.is_connected = False
        mock_provider.disconnect = AsyncMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            with patch("src.db.client.reset_provider") as mock_reset:
                # Act
                await close_db_client()

                # Assert
                mock_provider.disconnect.assert_not_called()
                mock_reset.assert_called_once()

    def test_create_supabase_client(self):
        """Test the deprecated create_supabase_client function."""
        # Arrange
        mock_provider = MagicMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            # Act
            client = create_supabase_client()

            # Assert
            assert client is mock_provider

    def test_get_supabase_client(self):
        """Test the deprecated get_supabase_client function."""
        # Arrange
        mock_provider = MagicMock()

        with patch("src.db.client.get_provider", return_value=mock_provider):
            # Act
            client = get_supabase_client()

            # Assert
            assert client is mock_provider

    def test_reset_client(self):
        """Test the deprecated reset_client function."""
        # Arrange
        with patch("src.db.client.reset_provider") as mock_reset:
            # Act
            reset_client()

            # Assert
            mock_reset.assert_called_once()
