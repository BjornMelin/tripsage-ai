"""
Integration tests for MemoryService with PGVectorService.

This module tests the integration between the memory service and the new
PGVectorService for optimal vector operations and memory table optimization.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemorySearchRequest,
    MemoryService,
)


class TestMemoryPGVectorIntegration:
    """Test memory service integration with PGVectorService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        db.execute_sql = AsyncMock()
        return db

    @pytest.fixture
    def mock_pgvector_service(self):
        """Mock PGVectorService."""
        pgvector_service = AsyncMock()
        pgvector_service.optimize_memory_tables = AsyncMock()
        pgvector_service.check_index_health = AsyncMock()
        pgvector_service.list_vector_tables = AsyncMock()
        return pgvector_service

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 client."""
        mem0 = MagicMock()
        mem0.add = MagicMock()
        mem0.search = MagicMock()
        mem0.get_all = MagicMock()
        return mem0

    @pytest.fixture
    async def memory_service_with_pgvector(
        self, mock_database_service, mock_pgvector_service, mock_mem0_client
    ):
        """Create memory service with mocked PGVector integration."""
        with patch(
            "tripsage_core.services.infrastructure.PGVectorService"
        ) as MockPGVectorService:
            MockPGVectorService.return_value = mock_pgvector_service

            service = MemoryService(database_service=mock_database_service)
            service.memory = mock_mem0_client
            service._connected = True

            return service

    @pytest.mark.asyncio
    async def test_memory_service_initialization_with_pgvector(
        self, mock_database_service
    ):
        """Test that memory service properly initializes PGVectorService."""
        with patch(
            "tripsage_core.services.infrastructure.PGVectorService"
        ) as MockPGVectorService:
            mock_pgvector_instance = AsyncMock()
            MockPGVectorService.return_value = mock_pgvector_instance

            service = MemoryService(database_service=mock_database_service)

            # Verify PGVectorService was initialized
            MockPGVectorService.assert_called_once_with(mock_database_service)
            assert service.pgvector_service == mock_pgvector_instance

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_success(
        self, memory_service_with_pgvector, mock_pgvector_service
    ):
        """Test successful memory table optimization."""
        # Mock optimization results
        mock_pgvector_service.optimize_memory_tables.return_value = {
            "memory_optimization": [
                {
                    "table": "memories",
                    "column": "embedding",
                    "actions": [
                        {
                            "action": "created_index",
                            "index_name": "idx_memories_embedding_cosine_hnsw",
                            "profile": "balanced",
                        }
                    ],
                }
            ],
            "errors": [],
        }

        result = await memory_service_with_pgvector.optimize_memory_tables()

        # Assertions
        assert result["success"] is True
        assert result["total_optimized"] == 1
        assert len(result["optimizations"]) == 1
        assert len(result["errors"]) == 0
        assert "timestamp" in result

        # Verify PGVectorService was called
        mock_pgvector_service.optimize_memory_tables.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_with_errors(
        self, memory_service_with_pgvector, mock_pgvector_service
    ):
        """Test memory table optimization with some errors."""
        # Mock optimization results with errors
        mock_pgvector_service.optimize_memory_tables.return_value = {
            "memory_optimization": [
                {
                    "table": "memories",
                    "column": "embedding",
                    "actions": [{"action": "index_exists"}],
                }
            ],
            "errors": [
                {
                    "table": "invalid_table",
                    "column": "embedding",
                    "error": "Table does not exist",
                }
            ],
        }

        result = await memory_service_with_pgvector.optimize_memory_tables()

        # Assertions
        assert result["success"] is True
        assert result["total_optimized"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["table"] == "invalid_table"

    @pytest.mark.asyncio
    async def test_check_memory_vector_health(
        self, memory_service_with_pgvector, mock_pgvector_service
    ):
        """Test memory vector health checking."""
        # Mock vector tables list
        mock_pgvector_service.list_vector_tables.return_value = [
            {
                "table_name": "memories",
                "column_name": "embedding",
                "index_status": "indexed",
            },
            {
                "table_name": "conversations",
                "column_name": "embedding",
                "index_status": "no_index",
            },
            {
                "table_name": "other_table",
                "column_name": "data",
                "index_status": "indexed",
            },
        ]

        # Mock health check results
        mock_pgvector_service.check_index_health.side_effect = [
            {
                "status": "healthy",
                "index_name": "idx_memories_embedding_cosine_hnsw",
                "size": "245 MB",
                "rows": 150000,
                "usage_count": 1250,
                "recommendations": [],
            },
            {
                "status": "missing",
                "message": "No HNSW index found on conversations.embedding",
                "recommendations": ["Create HNSW index for better query performance"],
            },
        ]

        result = await memory_service_with_pgvector.check_memory_vector_health()

        # Assertions
        assert result["total_tables"] == 2  # Only memory-related tables
        assert result["healthy_tables"] == 1
        assert result["needs_attention"] == 1
        assert result["overall_status"] == "needs_attention"
        assert len(result["health_reports"]) == 2

        # Verify health checks were called for memory tables only
        assert mock_pgvector_service.check_index_health.call_count == 2

    @pytest.mark.asyncio
    async def test_connect_with_memory_optimization(
        self, mock_database_service, mock_pgvector_service, mock_mem0_client
    ):
        """Test that connect() automatically optimizes memory tables."""
        # Mock successful connection validation
        with patch(
            "tripsage_core.services.infrastructure.PGVectorService"
        ) as MockPGVectorService:
            MockPGVectorService.return_value = mock_pgvector_service

            # Mock optimization results
            mock_pgvector_service.optimize_memory_tables.return_value = {
                "success": True,
                "total_optimized": 2,
                "memory_optimization": [],
                "errors": [],
            }

            service = MemoryService(database_service=mock_database_service)
            service.memory = mock_mem0_client

            # Mock connection manager and successful Mem0 test
            service.connection_manager = AsyncMock()
            service.connection_manager.parse_and_validate_url = AsyncMock()
            service.connection_manager.circuit_breaker = AsyncMock()
            service.connection_manager.circuit_breaker.call = AsyncMock()

            await service.connect()

            # Verify optimization was called during connect
            mock_pgvector_service.optimize_memory_tables.assert_called_once()
            assert service._connected is True

    @pytest.mark.asyncio
    async def test_memory_operations_with_optimized_tables(
        self, memory_service_with_pgvector, mock_mem0_client
    ):
        """Test that memory operations work correctly with optimized tables."""
        user_id = str(uuid4())

        # Test conversation memory addition
        conversation_request = ConversationMemoryRequest(
            messages=[
                {"role": "user", "content": "I love staying in boutique hotels"},
                {"role": "assistant", "content": "I'll remember your preference"},
            ],
            session_id=str(uuid4()),
        )

        mock_mem0_client.add.return_value = {
            "results": [
                {
                    "id": "mem0_123",
                    "memory": "User prefers boutique hotels",
                    "metadata": {"domain": "travel_planning"},
                }
            ],
            "usage": {"total_tokens": 150},
        }

        result = await memory_service_with_pgvector.add_conversation_memory(
            user_id, conversation_request
        )

        assert "results" in result
        assert len(result["results"]) == 1

        # Test memory search
        search_request = MemorySearchRequest(query="hotel preferences", limit=5)

        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_123",
                    "memory": "User prefers boutique hotels",
                    "metadata": {"categories": ["accommodation"]},
                    "score": 0.92,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

        search_results = await memory_service_with_pgvector.search_memories(
            user_id, search_request
        )

        assert len(search_results) == 1
        assert search_results[0].similarity == 0.92

    @pytest.mark.asyncio
    async def test_optimization_failure_handling(
        self, memory_service_with_pgvector, mock_pgvector_service
    ):
        """Test handling of optimization failures."""
        # Mock optimization failure
        mock_pgvector_service.optimize_memory_tables.side_effect = Exception(
            "Database connection error"
        )

        result = await memory_service_with_pgvector.optimize_memory_tables()

        assert result["success"] is False
        assert "Database connection error" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_failure_handling(
        self, memory_service_with_pgvector, mock_pgvector_service
    ):
        """Test handling of health check failures."""
        # Mock health check failure
        mock_pgvector_service.list_vector_tables.side_effect = Exception(
            "Permission denied"
        )

        result = await memory_service_with_pgvector.check_memory_vector_health()

        assert "error" in result
        assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_service_not_connected_handling(self, mock_database_service):
        """Test optimization methods when service is not connected."""
        service = MemoryService(database_service=mock_database_service)
        service._connected = False
        service.memory = None

        # Test optimization
        result = await service.optimize_memory_tables()
        assert result["error"] == "Memory service not available"

        # Test health check
        result = await service.check_memory_vector_health()
        assert result["error"] == "Memory service not available"

    @pytest.mark.asyncio
    async def test_concurrent_optimization_operations(
        self, memory_service_with_pgvector, mock_pgvector_service
    ):
        """Test concurrent optimization operations."""
        # Mock successful optimization
        mock_pgvector_service.optimize_memory_tables.return_value = {
            "memory_optimization": [],
            "errors": [],
        }

        # Run multiple optimization operations concurrently
        tasks = [
            memory_service_with_pgvector.optimize_memory_tables() for _ in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result.get("success") for result in results)

        # Verify optimization was called for each request
        assert mock_pgvector_service.optimize_memory_tables.call_count == 3

    @pytest.mark.asyncio
    async def test_memory_service_pgvector_integration_end_to_end(
        self, mock_database_service
    ):
        """Test complete end-to-end integration between memory service and pgvector."""
        with patch(
            "tripsage_core.services.infrastructure.PGVectorService"
        ) as MockPGVectorService:
            mock_pgvector_service = AsyncMock()
            MockPGVectorService.return_value = mock_pgvector_service

            # Mock Mem0
            mock_mem0 = MagicMock()
            mock_mem0.add.return_value = {"results": [], "usage": {"total_tokens": 100}}
            mock_mem0.search.return_value = {"results": []}

            # Mock optimization results
            mock_pgvector_service.optimize_memory_tables.return_value = {
                "memory_optimization": [
                    {
                        "table": "memories",
                        "column": "embedding",
                        "actions": [{"action": "created_index"}],
                    }
                ],
                "errors": [],
            }

            service = MemoryService(database_service=mock_database_service)
            service.memory = mock_mem0
            service._connected = True

            # Test full workflow
            user_id = str(uuid4())

            # 1. Optimize tables
            opt_result = await service.optimize_memory_tables()
            assert opt_result["success"] is True

            # 2. Add memory
            conversation_request = ConversationMemoryRequest(
                messages=[{"role": "user", "content": "Test memory"}]
            )
            add_result = await service.add_conversation_memory(
                user_id, conversation_request
            )
            assert "results" in add_result

            # 3. Search memory
            search_request = MemorySearchRequest(query="test")
            search_result = await service.search_memories(user_id, search_request)
            assert isinstance(search_result, list)

            # Verify all services were called
            mock_pgvector_service.optimize_memory_tables.assert_called()
            mock_mem0.add.assert_called()
            mock_mem0.search.assert_called()
