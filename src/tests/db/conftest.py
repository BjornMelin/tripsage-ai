"""Test fixtures for database tests."""

import asyncio
import os
from typing import AsyncGenerator, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.db.config import DatabaseConfig, DatabaseProvider, NeonConfig, SupabaseConfig
from src.db.providers import NeonProvider, SupabaseProvider


@pytest.fixture
def mock_supabase_config() -> SupabaseConfig:
    """Return a mock Supabase configuration."""
    return SupabaseConfig(
        url="https://example.supabase.co",
        anon_key="test-anon-key",
        service_role_key="test-service-role-key",
        timeout=5.0,
        auto_refresh_token=True,
        persist_session=True,
    )


@pytest.fixture
def mock_neon_config() -> NeonConfig:
    """Return a mock Neon configuration."""
    return NeonConfig(
        connection_string="postgresql://user:password@test-host:5432/testdb",
        min_pool_size=1,
        max_pool_size=5,
        max_inactive_connection_lifetime=60.0,
    )


@pytest.fixture
def mock_supabase_db_config(mock_supabase_config) -> DatabaseConfig:
    """Return a mock database configuration using Supabase."""
    return DatabaseConfig(
        provider=DatabaseProvider.SUPABASE, supabase=mock_supabase_config, neon=None
    )


@pytest.fixture
def mock_neon_db_config(mock_neon_config) -> DatabaseConfig:
    """Return a mock database configuration using Neon."""
    return DatabaseConfig(
        provider=DatabaseProvider.NEON, supabase=None, neon=mock_neon_config
    )


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Return a mock Supabase client."""
    mock_client = MagicMock()
    # Mock table method for fluent interface
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_limit = MagicMock()
    mock_execute = AsyncMock()
    mock_execute.return_value.data = [{"id": 1, "name": "test"}]

    mock_limit.execute = mock_execute
    mock_select.limit = MagicMock(return_value=mock_limit)
    mock_table.select = MagicMock(return_value=mock_select)
    mock_client.table = MagicMock(return_value=mock_table)

    # Mock RPC method
    mock_rpc = MagicMock()
    mock_rpc.execute = AsyncMock(return_value=MagicMock(data=[{"result": 1}]))
    mock_client.rpc = MagicMock(return_value=mock_rpc)

    return mock_client


@pytest_asyncio.fixture
async def mock_supabase_provider(
    mock_supabase_client,
) -> AsyncGenerator[SupabaseProvider, None]:
    """Return a mock Supabase provider."""
    with patch("src.db.providers.create_client", return_value=mock_supabase_client):
        provider = SupabaseProvider(
            url="https://example.supabase.co",
            key="test-key",
            options={
                "timeout": 5.0,
                "auto_refresh_token": True,
                "persist_session": True,
            },
        )
        await provider.connect()
        yield provider
        await provider.disconnect()


@pytest_asyncio.fixture
async def mock_asyncpg_pool() -> AsyncMock:
    """Return a mock asyncpg pool."""
    mock_pool = AsyncMock()

    # Mock connection context manager
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[{"id": 1, "name": "test"}])
    mock_conn.fetchrow = AsyncMock(return_value={"exists": True})
    mock_conn.execute = AsyncMock()

    # Mock the pool's acquire context manager
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    return mock_pool


@pytest_asyncio.fixture
async def mock_neon_provider(mock_asyncpg_pool) -> AsyncGenerator[NeonProvider, None]:
    """Return a mock Neon provider."""
    with patch("asyncpg.create_pool", return_value=mock_asyncpg_pool):
        provider = NeonProvider(
            connection_string="postgresql://user:password@test-host:5432/testdb",
            min_size=1,
            max_size=5,
            max_inactive_connection_lifetime=60.0,
        )
        await provider.connect()
        yield provider
        await provider.disconnect()
