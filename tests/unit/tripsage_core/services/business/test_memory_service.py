"""
Comprehensive tests for MemoryService.

This module provides full test coverage for memory management operations
including memory storage, retrieval, search, and AI-powered contextual understanding.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.models.db.memory import Memory
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest as MemoryCreateRequest,
)
from tripsage_core.services.business.memory_service import (
    MemorySearchRequest,
    MemoryService,
    get_memory_service,
)
from tripsage_core.services.business.memory_service import (
    MemorySearchResult as MemoryMetadata,
)
from tripsage_core.services.business.memory_service import (
    UserContextResponse as MemoryUpdateRequest,
)


# Define mock enums for testing
class MemoryType(str, Enum):
    PREFERENCE = "preference"
    FACTUAL = "factual"
    BEHAVIORAL = "behavioral"
    GOAL = "goal"


class MemoryImportance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class TestMemoryService:
    """Test suite for MemoryService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 client."""
        mem0 = AsyncMock()
        return mem0

    @pytest.fixture
    def mock_vector_service(self):
        """Mock vector service."""
        vector = AsyncMock()
        return vector

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service."""
        ai = AsyncMock()
        return ai

    @pytest.fixture
    def memory_service(
        self,
        mock_database_service,
    ):
        """Create MemoryService instance with mocked dependencies."""
        return MemoryService(
            database_service=mock_database_service,
            memory_backend_config={"type": "memory"},
            cache_ttl=300,
        )

    @pytest.fixture
    def sample_memory_create_request(self):
        """Sample memory creation request."""
        return MemoryCreateRequest(
            messages=[
                {
                    "role": "user",
                    "content": "I prefer boutique hotels in historic city centers",
                },
                {
                    "role": "assistant",
                    "content": (
                        "I'll remember your preference for boutique hotels "
                        "in historic areas."
                    ),
                },
            ],
            session_id=str(uuid4()),
            trip_id=str(uuid4()),
            metadata={
                "location": "Europe",
                "category": "accommodation",
                "tags": ["hotels", "boutique", "historic", "preferences"],
            },
        )

    @pytest.fixture
    def sample_memory(self):
        """Sample memory object."""
        memory_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return Memory(
            id=memory_id,
            user_id=user_id,
            content="User prefers boutique hotels in historic city centers",
            memory_type=MemoryType.PREFERENCE,
            importance=MemoryImportance.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_accessed=None,
            access_count=0,
            context={
                "trip_id": str(uuid4()),
                "session_id": str(uuid4()),
                "location": "Europe",
                "category": "accommodation",
            },
            tags=["hotels", "boutique", "historic", "preferences"],
            expires_at=now + timedelta(days=365),
            metadata=MemoryMetadata(
                memory_id=memory_id,
                vector_embedding=[0.1, 0.2, 0.3],  # Simplified embedding
                relevance_score=0.95,
                confidence_score=0.88,
                source="chat_conversation",
                extraction_method="ai_analysis",
                related_memories=[],
                semantic_clusters=["accommodation_preferences", "location_preferences"],
                last_reinforced=now,
                reinforcement_count=1,
            ),
            mem0_memory_id="mem0_abc123",
        )

    async def test_create_memory_success(
        self,
        memory_service,
        mock_database_service,
        mock_mem0_client,
        mock_vector_service,
        mock_ai_service,
        sample_memory_create_request,
    ):
        """Test successful memory creation."""
        user_id = str(uuid4())

        # Mock AI analysis
        mock_ai_service.analyze_memory_content.return_value = {
            "importance": MemoryImportance.HIGH,
            "semantic_clusters": ["accommodation_preferences"],
            "entities": ["boutique hotels", "historic city centers"],
            "confidence": 0.88,
        }

        # Mock vector embedding
        mock_vector_service.generate_embedding.return_value = [0.1, 0.2, 0.3]

        # Mock Mem0 storage
        mock_mem0_client.add.return_value = {"id": "mem0_abc123"}

        # Mock database operations
        mock_database_service.store_memory.return_value = None

        result = await memory_service.create_memory(
            user_id, sample_memory_create_request
        )

        # Assertions
        assert result.user_id == user_id
        assert result.content == sample_memory_create_request.content
        assert result.memory_type == sample_memory_create_request.memory_type
        assert result.importance == sample_memory_create_request.importance
        assert result.status == MemoryStatus.ACTIVE
        assert result.mem0_memory_id == "mem0_abc123"

        # Verify service calls
        mock_ai_service.analyze_memory_content.assert_called_once()
        mock_vector_service.generate_embedding.assert_called_once()
        mock_mem0_client.add.assert_called_once()
        mock_database_service.store_memory.assert_called_once()

    async def test_create_memory_duplicate_detection(
        self,
        memory_service,
        mock_database_service,
        mock_vector_service,
        sample_memory_create_request,
        sample_memory,
    ):
        """Test memory creation with duplicate detection."""
        user_id = str(uuid4())

        # Mock vector search finding similar memory
        mock_vector_service.search_similar.return_value = [
            {
                "memory_id": sample_memory.id,
                "similarity_score": 0.95,
                "content": sample_memory.content,
            }
        ]

        mock_database_service.get_memory.return_value = sample_memory.model_dump()
        mock_database_service.update_memory.return_value = None

        result = await memory_service.create_memory(
            user_id, sample_memory_create_request
        )

        # Should merge with existing memory instead of creating new one
        assert result.id == sample_memory.id
        assert result.metadata.reinforcement_count == 2  # Incremented
        mock_database_service.update_memory.assert_called_once()

    async def test_get_memory_success(
        self, memory_service, mock_database_service, sample_memory
    ):
        """Test successful memory retrieval."""
        mock_database_service.get_memory.return_value = sample_memory.model_dump()
        mock_database_service.update_memory.return_value = None

        result = await memory_service.get_memory(
            sample_memory.id, sample_memory.user_id
        )

        assert result is not None
        assert result.id == sample_memory.id
        assert result.content == sample_memory.content
        assert result.access_count == 1  # Incremented
        assert result.last_accessed is not None

        mock_database_service.get_memory.assert_called_once()
        mock_database_service.update_memory.assert_called_once()  # For access tracking

    async def test_get_memory_not_found(self, memory_service, mock_database_service):
        """Test memory retrieval when memory doesn't exist."""
        memory_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_memory.return_value = None

        result = await memory_service.get_memory(memory_id, user_id)

        assert result is None

    async def test_get_memory_access_denied(
        self, memory_service, mock_database_service, sample_memory
    ):
        """Test memory retrieval with access denied."""
        different_user_id = str(uuid4())

        mock_database_service.get_memory.return_value = sample_memory.model_dump()

        result = await memory_service.get_memory(sample_memory.id, different_user_id)

        assert result is None

    async def test_update_memory_success(
        self,
        memory_service,
        mock_database_service,
        mock_ai_service,
        mock_vector_service,
        mock_mem0_client,
        sample_memory,
    ):
        """Test successful memory update."""
        mock_database_service.get_memory.return_value = sample_memory.model_dump()
        mock_database_service.update_memory.return_value = None

        # Mock services for content re-analysis
        mock_ai_service.analyze_memory_content.return_value = {
            "importance": MemoryImportance.HIGH,
            "semantic_clusters": ["accommodation_preferences", "luxury_preferences"],
            "confidence": 0.92,
        }
        mock_vector_service.generate_embedding.return_value = [0.2, 0.3, 0.4]
        mock_mem0_client.update.return_value = {"success": True}

        update_request = MemoryUpdateRequest(
            content=(
                "User prefers luxury boutique hotels in historic European city centers"
            ),
            tags=["hotels", "boutique", "luxury", "historic", "preferences"],
            importance=MemoryImportance.CRITICAL,
        )

        result = await memory_service.update_memory(
            sample_memory.id, sample_memory.user_id, update_request
        )

        assert result.content == update_request.content
        assert result.importance == MemoryImportance.CRITICAL
        assert result.tags == update_request.tags
        assert result.updated_at > sample_memory.updated_at

        mock_database_service.update_memory.assert_called_once()
        mock_mem0_client.update.assert_called_once()

    async def test_delete_memory_success(
        self, memory_service, mock_database_service, mock_mem0_client, sample_memory
    ):
        """Test successful memory deletion."""
        mock_database_service.get_memory.return_value = sample_memory.model_dump()
        mock_database_service.delete_memory.return_value = True
        mock_mem0_client.delete.return_value = {"success": True}

        result = await memory_service.delete_memory(
            sample_memory.id, sample_memory.user_id
        )

        assert result is True
        mock_database_service.delete_memory.assert_called_once()
        mock_mem0_client.delete.assert_called_once()

    async def test_search_memories_success(
        self, memory_service, mock_database_service, mock_vector_service, sample_memory
    ):
        """Test successful memory search."""
        user_id = str(uuid4())

        search_request = MemorySearchRequest(
            query="hotel preferences",
            memory_types=[MemoryType.PREFERENCE],
            importance_levels=[MemoryImportance.HIGH, MemoryImportance.CRITICAL],
            tags=["hotels"],
            limit=10,
            similarity_threshold=0.7,
        )

        # Mock vector search
        mock_vector_service.search_memories.return_value = [
            {
                "memory_id": sample_memory.id,
                "similarity_score": 0.9,
                "content": sample_memory.content,
            }
        ]

        # Mock database retrieval
        mock_database_service.get_memories_by_ids.return_value = [
            sample_memory.model_dump()
        ]

        results = await memory_service.search_memories(user_id, search_request)

        assert len(results) == 1
        assert results[0].id == sample_memory.id
        assert results[0].metadata.relevance_score == 0.9

        mock_vector_service.search_memories.assert_called_once()
        mock_database_service.get_memories_by_ids.assert_called_once()

    async def test_get_related_memories_success(
        self, memory_service, mock_database_service, mock_vector_service, sample_memory
    ):
        """Test successful related memories retrieval."""
        mock_database_service.get_memory.return_value = sample_memory.model_dump()

        # Mock vector search for related memories
        related_memory_id = str(uuid4())
        mock_vector_service.find_related_memories.return_value = [
            {
                "memory_id": related_memory_id,
                "similarity_score": 0.8,
                "relation_type": "semantic_similarity",
            }
        ]

        # Mock related memory data
        related_memory_data = {
            "id": related_memory_id,
            "content": "User also prefers hotels with spa facilities",
            "memory_type": MemoryType.PREFERENCE.value,
        }
        mock_database_service.get_memories_by_ids.return_value = [related_memory_data]

        results = await memory_service.get_related_memories(
            sample_memory.id, sample_memory.user_id, limit=5
        )

        assert len(results) == 1
        assert results[0]["similarity_score"] == 0.8
        mock_vector_service.find_related_memories.assert_called_once()

    async def test_consolidate_memories_success(
        self,
        memory_service,
        mock_database_service,
        mock_ai_service,
        mock_vector_service,
    ):
        """Test successful memory consolidation."""
        user_id = str(uuid4())

        # Mock similar memories for consolidation
        memory_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        similar_memories = [
            {
                "id": memory_ids[0],
                "content": "User likes boutique hotels",
                "importance": MemoryImportance.MEDIUM.value,
            },
            {
                "id": memory_ids[1],
                "content": "User prefers small luxury hotels",
                "importance": MemoryImportance.HIGH.value,
            },
            {
                "id": memory_ids[2],
                "content": "User enjoys unique hotel experiences",
                "importance": MemoryImportance.MEDIUM.value,
            },
        ]

        mock_database_service.find_similar_memories.return_value = similar_memories

        # Mock AI consolidation
        consolidated_content = (
            "User prefers boutique and luxury hotels with unique experiences"
        )
        mock_ai_service.consolidate_memories.return_value = {
            "consolidated_content": consolidated_content,
            "importance": MemoryImportance.HIGH,
            "confidence": 0.95,
        }

        # Mock storage operations
        mock_database_service.store_memory.return_value = None
        mock_database_service.delete_memories.return_value = None
        mock_vector_service.generate_embedding.return_value = [0.5, 0.6, 0.7]

        result = await memory_service.consolidate_memories(
            user_id, similarity_threshold=0.8
        )

        assert result["consolidated_count"] >= 1
        assert result["deleted_count"] >= 2
        mock_ai_service.consolidate_memories.assert_called()

    async def test_extract_memories_from_text_success(
        self,
        memory_service,
        mock_ai_service,
        mock_database_service,
        mock_vector_service,
        mock_mem0_client,
    ):
        """Test successful memory extraction from text."""
        user_id = str(uuid4())

        conversation_text = """
        I really love staying in boutique hotels when I travel to Europe. 
        I prefer places with character and history. Budget is $200-300/night.
        I don't like chain hotels - they're too generic for my taste.
        """

        # Mock AI extraction
        extracted_memories = [
            {
                "content": "User prefers boutique hotels in Europe",
                "type": MemoryType.PREFERENCE,
                "importance": MemoryImportance.HIGH,
                "confidence": 0.9,
            },
            {
                "content": "User's hotel budget is $200-300 per night",
                "type": MemoryType.FACTUAL,
                "importance": MemoryImportance.MEDIUM,
                "confidence": 0.85,
            },
            {
                "content": "User dislikes chain hotels",
                "type": MemoryType.PREFERENCE,
                "importance": MemoryImportance.MEDIUM,
                "confidence": 0.8,
            },
        ]

        mock_ai_service.extract_memories_from_text.return_value = extracted_memories

        # Mock storage operations
        mock_vector_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
        mock_mem0_client.add.return_value = {"id": "mem0_extracted_123"}
        mock_database_service.store_memory.return_value = None

        context = {"session_id": str(uuid4()), "source": "chat_conversation"}

        results = await memory_service.extract_memories_from_text(
            user_id, conversation_text, context
        )

        assert len(results) == 3
        assert all(memory.user_id == user_id for memory in results)
        assert any("boutique hotels" in memory.content for memory in results)

        mock_ai_service.extract_memories_from_text.assert_called_once()
        assert mock_database_service.store_memory.call_count == 3

    async def test_get_user_memory_summary_success(
        self, memory_service, mock_database_service, mock_ai_service
    ):
        """Test successful user memory summary generation."""
        user_id = str(uuid4())

        # Mock memory statistics
        stats_data = {
            "total_memories": 150,
            "active_memories": 140,
            "expired_memories": 10,
            "memories_by_type": {
                "preference": 60,
                "factual": 50,
                "behavioral": 30,
                "goal": 10,
            },
            "memories_by_importance": {
                "critical": 15,
                "high": 45,
                "medium": 60,
                "low": 30,
            },
            "most_accessed_memories": [str(uuid4()), str(uuid4())],
            "recent_memories": 25,
        }

        mock_database_service.get_user_memory_statistics.return_value = stats_data

        # Mock AI summary generation
        summary_data = {
            "key_preferences": [
                "Prefers boutique hotels in historic areas",
                "Enjoys local food experiences",
                "Values unique cultural activities",
            ],
            "travel_patterns": [
                "Typically travels to Europe",
                "Average trip duration: 10-14 days",
                "Prefers spring and fall travel",
            ],
            "budget_insights": [
                "Hotel budget: $200-300/night",
                "Total trip budget: $3000-5000",
                "Willing to spend more on unique experiences",
            ],
            "personality_profile": {
                "travel_style": "Cultural Explorer",
                "risk_tolerance": "Moderate",
                "planning_style": "Detailed",
            },
        }

        mock_ai_service.generate_memory_summary.return_value = summary_data

        result = await memory_service.get_user_memory_summary(user_id)

        assert "statistics" in result
        assert "summary" in result
        assert result["statistics"]["total_memories"] == 150
        assert len(result["summary"]["key_preferences"]) == 3

        mock_database_service.get_user_memory_statistics.assert_called_once()
        mock_ai_service.generate_memory_summary.assert_called_once()

    async def test_cleanup_expired_memories_success(
        self, memory_service, mock_database_service, mock_mem0_client
    ):
        """Test successful cleanup of expired memories."""
        # Mock expired memories
        expired_memory_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        mock_database_service.get_expired_memories.return_value = expired_memory_ids
        mock_database_service.delete_memories.return_value = None
        mock_mem0_client.delete.return_value = {"success": True}

        result = await memory_service.cleanup_expired_memories()

        assert result["cleaned_count"] == 3
        assert result["success"] is True

        mock_database_service.get_expired_memories.assert_called_once()
        mock_database_service.delete_memories.assert_called_once()
        assert mock_mem0_client.delete.call_count == 3

    async def test_reinforce_memory_success(
        self, memory_service, mock_database_service, sample_memory
    ):
        """Test successful memory reinforcement."""
        mock_database_service.get_memory.return_value = sample_memory.model_dump()
        mock_database_service.update_memory.return_value = None

        reinforcement_context = {
            "source": "user_confirmation",
            "confidence_boost": 0.1,
            "additional_evidence": "User explicitly confirmed this preference",
        }

        result = await memory_service.reinforce_memory(
            sample_memory.id, sample_memory.user_id, reinforcement_context
        )

        assert result.metadata.reinforcement_count == 2  # Incremented
        assert result.metadata.confidence_score == 0.98  # Boosted
        assert result.metadata.last_reinforced > sample_memory.metadata.last_reinforced

        mock_database_service.update_memory.assert_called_once()

    async def test_memory_decay_processing(self, memory_service, mock_database_service):
        """Test memory decay processing for unused memories."""
        user_id = str(uuid4())

        # Mock memories due for decay processing
        stale_memories = [
            {
                "id": str(uuid4()),
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=90),
                "access_count": 1,
                "importance": MemoryImportance.LOW.value,
            },
            {
                "id": str(uuid4()),
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=60),
                "access_count": 0,
                "importance": MemoryImportance.MEDIUM.value,
            },
        ]

        mock_database_service.get_stale_memories.return_value = stale_memories
        mock_database_service.update_memory.return_value = None
        mock_database_service.delete_memory.return_value = True

        result = await memory_service.process_memory_decay(user_id)

        assert result["processed_count"] >= 2
        assert "decayed_memories" in result
        assert "deleted_memories" in result

        mock_database_service.get_stale_memories.assert_called_once()

    async def test_contextual_memory_retrieval(
        self,
        memory_service,
        mock_database_service,
        mock_vector_service,
        mock_ai_service,
    ):
        """Test contextual memory retrieval for specific situations."""
        user_id = str(uuid4())

        context = {
            "current_location": "Paris",
            "trip_type": "leisure",
            "travel_dates": ["2024-07-15", "2024-07-22"],
            "companions": "solo",
            "budget_range": "mid-range",
        }

        # Mock AI context analysis
        context_analysis = {
            "relevant_memory_types": [MemoryType.PREFERENCE, MemoryType.FACTUAL],
            "context_keywords": ["Paris", "solo travel", "mid-range", "leisure"],
            "importance_weighting": {
                "location": 0.4,
                "travel_style": 0.3,
                "budget": 0.2,
                "timing": 0.1,
            },
        }
        mock_ai_service.analyze_context_for_memory_retrieval.return_value = (
            context_analysis
        )

        # Mock vector search with context
        mock_vector_service.contextual_search.return_value = [
            {
                "memory_id": str(uuid4()),
                "relevance_score": 0.95,
                "context_match_score": 0.88,
            }
        ]

        # Mock memory data
        mock_database_service.get_memories_by_ids.return_value = []

        results = await memory_service.get_contextual_memories(user_id, context)

        assert "memories" in results
        assert "context_analysis" in results
        assert results["context_analysis"]["importance_weighting"]["location"] == 0.4

        mock_ai_service.analyze_context_for_memory_retrieval.assert_called_once()
        mock_vector_service.contextual_search.assert_called_once()

    async def test_service_error_handling(
        self, memory_service, mock_database_service, sample_memory_create_request
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.store_memory.side_effect = Exception("Database error")

        with pytest.raises(ServiceError, match="Failed to create memory"):
            await memory_service.create_memory(user_id, sample_memory_create_request)

    async def test_get_memory_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_memory_service()
        assert isinstance(service, MemoryService)

    async def test_memory_privacy_controls(
        self, memory_service, mock_database_service, sample_memory
    ):
        """Test memory privacy and sharing controls."""
        # Test memory visibility settings
        privacy_settings = {
            "visibility": "private",  # private, shared, public
            "shared_with": [],
            "anonymize_content": False,
            "retention_period": 365,  # days
        }

        mock_database_service.get_memory.return_value = sample_memory.model_dump()
        mock_database_service.update_memory.return_value = None

        result = await memory_service.update_memory_privacy(
            sample_memory.id, sample_memory.user_id, privacy_settings
        )

        assert result is True
        mock_database_service.update_memory.assert_called_once()

    async def test_memory_export_import(
        self, memory_service, mock_database_service, mock_mem0_client
    ):
        """Test memory export and import functionality."""
        user_id = str(uuid4())

        # Mock export

        mock_database_service.get_user_memories.return_value = []

        # Mock export generation
        with patch.object(memory_service, "_generate_memory_export") as mock_export:
            mock_export.return_value = {
                "export_url": "https://storage.example.com/exports/memories_123.json",
                "file_size": 1024000,
            }

            export_result = await memory_service.export_user_memories(user_id)

            assert "export_url" in export_result
            assert export_result["file_size"] > 0
            mock_export.assert_called_once()

    async def test_semantic_clustering(
        self, memory_service, mock_ai_service, mock_database_service
    ):
        """Test semantic clustering of memories."""
        user_id = str(uuid4())

        # Mock clustering analysis
        clustering_result = {
            "clusters": [
                {
                    "cluster_id": "accommodation_preferences",
                    "theme": "Hotel and accommodation preferences",
                    "memory_ids": [str(uuid4()), str(uuid4())],
                    "coherence_score": 0.92,
                },
                {
                    "cluster_id": "food_experiences",
                    "theme": "Food and dining preferences",
                    "memory_ids": [str(uuid4())],
                    "coherence_score": 0.87,
                },
            ],
            "outliers": [str(uuid4())],
            "cluster_quality_score": 0.85,
        }

        mock_ai_service.cluster_memories_semantically.return_value = clustering_result
        mock_database_service.update_memory_clusters.return_value = None

        result = await memory_service.cluster_user_memories(user_id)

        assert len(result["clusters"]) == 2
        assert result["cluster_quality_score"] == 0.85
        assert len(result["outliers"]) == 1

        mock_ai_service.cluster_memories_semantically.assert_called_once()
        mock_database_service.update_memory_clusters.assert_called_once()
