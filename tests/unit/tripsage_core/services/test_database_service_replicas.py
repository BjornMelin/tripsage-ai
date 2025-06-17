"""
Tests for database service integration with read replicas.

Tests cover the integration between DatabaseService and ReplicaManager,
including query routing, health monitoring, and configuration management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.replica_manager import (
    QueryType,
    ReplicaManager,
)


@pytest.fixture
def mock_settings_with_replicas():
    """Create mock settings with read replicas enabled."""
    settings = MagicMock(spec=Settings)
    settings.database_url = "https://primary.supabase.co"

    # Mock SecretStr attributes properly with longer keys
    # (Supabase requires longer keys)
    mock_public_key = MagicMock()
    mock_public_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.primary-key-test-value-for-testing-only"
    )
    settings.database_public_key = mock_public_key

    mock_service_key = MagicMock()
    mock_service_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.service-key-test-value-for-testing-only"
    )
    settings.database_service_key = mock_service_key

    mock_jwt_secret = MagicMock()
    mock_jwt_secret.get_secret_value.return_value = (
        "test-jwt-secret-super-secret-for-testing-only-very-long-secret-key"
    )
    settings.database_jwt_secret = mock_jwt_secret

    settings.enable_read_replicas = True
    settings.database_region = "us-east-1"
    settings.read_replica_strategy = "round_robin"

    # Mock read_replicas property
    settings.read_replicas = {
        "west": {
            "url": "https://west.supabase.co",
            "api_key": "west-key",
            "name": "West Replica",
            "region": "us-west-1",
            "priority": 1,
            "weight": 1.0,
            "max_connections": 100,
            "read_only": True,
            "enabled": True,
        }
    }

    return settings


@pytest.fixture
def mock_settings_without_replicas():
    """Create mock settings with read replicas disabled."""
    settings = MagicMock(spec=Settings)
    settings.database_url = "https://primary.supabase.co"

    # Mock SecretStr attributes properly with longer keys
    # (Supabase requires longer keys)
    mock_public_key = MagicMock()
    mock_public_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.primary-key-test-value-without-replicas"
    )
    settings.database_public_key = mock_public_key

    mock_service_key = MagicMock()
    mock_service_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.service-key-test-value-without-replicas"
    )
    settings.database_service_key = mock_service_key

    mock_jwt_secret = MagicMock()
    mock_jwt_secret.get_secret_value.return_value = (
        "test-jwt-secret-super-secret-without-replicas-very-long-secret-key"
    )
    settings.database_jwt_secret = mock_jwt_secret

    settings.enable_read_replicas = False
    settings.read_replicas = {}

    return settings


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    table_mock = MagicMock()
    query_mock = MagicMock()

    # Chain method calls for table operations
    client.table.return_value = table_mock
    table_mock.select.return_value = query_mock
    table_mock.insert.return_value = query_mock
    table_mock.update.return_value = query_mock
    table_mock.delete.return_value = query_mock
    table_mock.upsert.return_value = query_mock

    # Chain method calls for query building
    query_mock.eq.return_value = query_mock
    query_mock.gte.return_value = query_mock
    query_mock.lte.return_value = query_mock
    query_mock.order.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.execute.return_value = MagicMock(
        data=[{"id": "test", "name": "Test"}], count=1
    )

    return client


class TestDatabaseServiceReplicaIntegration:
    """Test cases for DatabaseService with replica integration."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_settings_with_replicas):
        """Set up test fixtures."""
        self.settings = mock_settings_with_replicas
        self.db_service = DatabaseService(self.settings)

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_initialization_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test database service initialization with replicas enabled."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        assert self.db_service.is_connected
        assert self.db_service._replica_manager is not None
        assert isinstance(self.db_service._replica_manager, ReplicaManager)

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    async def test_initialization_without_replicas(
        self, mock_create_client, mock_supabase_client, mock_settings_without_replicas
    ):
        """Test database service initialization with replicas disabled."""
        mock_create_client.return_value = mock_supabase_client

        db_service = DatabaseService(mock_settings_without_replicas)
        await db_service.connect()

        assert db_service.is_connected
        assert db_service._replica_manager is None

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_initialization_failure_fallback(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test fallback when replica initialization fails."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.side_effect = Exception("Replica init failed")

        # Should not raise exception, should fall back to primary only
        await self.db_service.connect()

        assert self.db_service.is_connected
        # Replica manager should be None or not properly initialized
        # but service should still work

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_select_with_replica_routing(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test SELECT queries use replica routing."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        # Mock the replica manager to return a specific replica
        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "acquire_connection"
            ) as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(
                    return_value=("west", mock_supabase_client)
                )
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await self.db_service.select("users", "*", {"active": True})

                assert result == [{"id": "test", "name": "Test"}]
                mock_acquire.assert_called_once()

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_insert_uses_primary(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test INSERT queries always use primary database."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        # Mock the replica manager - it should not be called for write operations
        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "acquire_connection"
            ) as mock_acquire:
                result = await self.db_service.insert("users", {"name": "Test User"})

                assert result == [{"id": "test", "name": "Test"}]
                # Replica manager should not be used for writes
                mock_acquire.assert_not_called()

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_vector_search_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test vector search queries use replica routing."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "acquire_connection"
            ) as mock_acquire:
                mock_acquire.return_value.__aenter__ = AsyncMock(
                    return_value=("west", mock_supabase_client)
                )
                mock_acquire.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await self.db_service.vector_search(
                    "destinations",
                    "embedding",
                    [0.1, 0.2, 0.3],
                    limit=5,
                    user_region="us-west-1",
                )

                assert result == [{"id": "test", "name": "Test"}]
                # Should have called acquire_connection with VECTOR_SEARCH query type
                mock_acquire.assert_called_once()
                call_args = mock_acquire.call_args
                assert call_args[1]["query_type"] == QueryType.VECTOR_SEARCH
                assert call_args[1]["user_region"] == "us-west-1"

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_fallback_on_failure(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test fallback to primary when replica connection fails."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "acquire_connection"
            ) as mock_acquire:
                # Mock replica connection failure
                mock_acquire.side_effect = Exception("Replica connection failed")

                # Should fall back to primary and still work
                result = await self.db_service.select("users", "*", {"active": True})

                assert result == [{"id": "test", "name": "Test"}]
                # Primary client should have been used directly

    async def test_replica_health_methods(self):
        """Test replica health monitoring methods."""
        # Test when replicas are disabled
        db_service = DatabaseService(MagicMock(enable_read_replicas=False))

        health = await db_service.get_replica_health()
        assert health["enabled"] is False

        metrics = await db_service.get_replica_metrics()
        assert metrics["enabled"] is False

        recommendations = await db_service.get_scaling_recommendations()
        assert recommendations["enabled"] is False

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_health_methods_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test replica health monitoring methods when replicas are enabled."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            # Mock health and metrics data
            with patch.object(
                self.db_service._replica_manager, "get_replica_health"
            ) as mock_health:
                with patch.object(
                    self.db_service._replica_manager, "get_replica_metrics"
                ) as mock_metrics:
                    with patch.object(
                        self.db_service._replica_manager, "get_load_balancer_stats"
                    ) as mock_stats:
                        from datetime import datetime, timezone  # noqa: E501

                        from tripsage_core.services.infrastructure.replica_manager import (  # noqa: E501
                            LoadBalancerStats,
                            ReplicaHealth,
                            ReplicaMetrics,
                            ReplicaStatus,
                        )

                        # Mock return values
                        mock_health.return_value = {
                            "west": ReplicaHealth(
                                replica_id="west",
                                status=ReplicaStatus.HEALTHY,
                                last_check=datetime.now(timezone.utc),
                                latency_ms=10.0,
                                uptime_percentage=99.5,
                            )
                        }

                        mock_metrics.return_value = {
                            "west": ReplicaMetrics(
                                replica_id="west",
                                total_queries=1000,
                                avg_response_time_ms=15.0,
                            )
                        }

                        mock_stats.return_value = LoadBalancerStats(
                            total_requests=1000, successful_requests=990
                        )

                        # Test health retrieval
                        health = await self.db_service.get_replica_health()
                        assert health["enabled"] is True
                        assert health["replica_count"] == 1
                        assert "west" in health["replicas"]

                        # Test metrics retrieval
                        metrics = await self.db_service.get_replica_metrics()
                        assert metrics["enabled"] is True
                        assert "load_balancer" in metrics
                        assert "replicas" in metrics

    async def test_load_balancing_strategy_methods(self):
        """Test load balancing strategy management."""
        # Test when replicas are disabled
        db_service = DatabaseService(MagicMock(enable_read_replicas=False))

        result = db_service.set_load_balancing_strategy("latency_based")
        assert result is False

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_load_balancing_strategy_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test load balancing strategy management when replicas are enabled."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            # Test valid strategy
            result = self.db_service.set_load_balancing_strategy("latency_based")
            assert result is True

            # Test invalid strategy
            result = self.db_service.set_load_balancing_strategy("invalid_strategy")
            assert result is False

    async def test_replica_management_methods(self):
        """Test replica add/remove methods when replicas are disabled."""
        db_service = DatabaseService(MagicMock(enable_read_replicas=False))

        result = await db_service.add_read_replica(
            "test", "https://test.supabase.co", "test-key"
        )
        assert result is False

        result = await db_service.remove_read_replica("test")
        assert result is False

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_management_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test replica add/remove methods when replicas are enabled."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "register_replica", return_value=True
            ) as mock_register:
                with patch.object(
                    self.db_service._replica_manager,
                    "remove_replica",
                    return_value=True,
                ) as mock_remove:
                    # Test adding replica
                    result = await self.db_service.add_read_replica(
                        "test",
                        "https://test.supabase.co",
                        "test-key",
                        region="us-west-2",
                        priority=2,
                    )
                    assert result is True
                    mock_register.assert_called_once()

                    # Test removing replica
                    result = await self.db_service.remove_read_replica("test")
                    assert result is True
                    mock_remove.assert_called_once_with("test")

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_management_error_handling(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test error handling in replica management methods."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "register_replica"
            ) as mock_register:
                with patch.object(
                    self.db_service._replica_manager, "remove_replica"
                ) as mock_remove:
                    # Test adding replica with error
                    mock_register.side_effect = Exception("Registration failed")
                    result = await self.db_service.add_read_replica(
                        "test", "https://test.supabase.co", "test-key"
                    )
                    assert result is False

                    # Test removing replica with error
                    mock_remove.side_effect = Exception("Removal failed")
                    result = await self.db_service.remove_read_replica("test")
                    assert result is False

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_close_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test proper cleanup when closing database service with replicas."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        # Verify replica manager was created
        assert self.db_service._replica_manager is not None

        # Mock the replica manager close method
        if self.db_service._replica_manager:
            with patch.object(self.db_service._replica_manager, "close") as mock_close:
                await self.db_service.close()

                # Verify replica manager was closed
                mock_close.assert_called_once()
                assert self.db_service._replica_manager is None

    def test_replica_status_methods(self):
        """Test replica status checking methods."""
        # Test when replicas are disabled
        db_service = DatabaseService(MagicMock(enable_read_replicas=False))

        assert db_service.get_replica_manager() is None
        assert db_service.is_replica_enabled() is False

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_status_methods_with_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test replica status checking methods when replicas are enabled."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        assert self.db_service.get_replica_manager() is not None
        assert self.db_service.is_replica_enabled() is True


class TestQueryTypeRouting:
    """Test query type routing behavior."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_settings_with_replicas):
        """Set up test fixtures."""
        self.settings = mock_settings_with_replicas
        self.db_service = DatabaseService(self.settings)

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_read_operations_use_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test that read operations are routed to replicas."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            with patch.object(
                self.db_service, "_get_client_for_query"
            ) as mock_get_client:
                mock_get_client.return_value.__aenter__ = AsyncMock(
                    return_value=("west", mock_supabase_client)
                )
                mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

                # Test SELECT query
                await self.db_service.select("users")

                # Verify _get_client_for_query was called with READ query type
                mock_get_client.assert_called_with(
                    query_type=QueryType.READ, user_region=None
                )

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    async def test_write_operations_use_primary(
        self, mock_create_client, mock_supabase_client
    ):
        """Test that write operations always use primary database."""
        mock_create_client.return_value = mock_supabase_client

        await self.db_service.connect()

        # Mock replica manager to ensure it's not called for writes
        if self.db_service._replica_manager:
            with patch.object(
                self.db_service._replica_manager, "acquire_connection"
            ) as mock_acquire:
                # Test write operations
                await self.db_service.insert("users", {"name": "Test"})
                await self.db_service.update("users", {"name": "Updated"}, {"id": "1"})
                await self.db_service.upsert("users", {"id": "1", "name": "Upserted"})
                await self.db_service.delete("users", {"id": "1"})

                # Replica manager should not be used for any write operations
                mock_acquire.assert_not_called()

    @patch("tripsage_core.services.infrastructure.database_service.create_client")
    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_vector_search_uses_replicas(
        self, mock_replica_create, mock_primary_create, mock_supabase_client
    ):
        """Test that vector search operations are routed to replicas."""
        mock_primary_create.return_value = mock_supabase_client
        mock_replica_create.return_value = mock_supabase_client

        await self.db_service.connect()

        if self.db_service._replica_manager:
            with patch.object(
                self.db_service, "_get_client_for_query"
            ) as mock_get_client:
                mock_get_client.return_value.__aenter__ = AsyncMock(
                    return_value=("west", mock_supabase_client)
                )
                mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

                # Test vector search
                await self.db_service.vector_search(
                    "destinations", "embedding", [0.1, 0.2]
                )

                # Verify _get_client_for_query was called with VECTOR_SEARCH query type
                mock_get_client.assert_called_with(
                    query_type=QueryType.VECTOR_SEARCH, user_region=None
                )
