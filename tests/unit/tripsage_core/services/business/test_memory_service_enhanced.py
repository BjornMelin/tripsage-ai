"""Enhanced comprehensive tests for MemoryService.

This module provides full test coverage for memory management operations
including memory storage, retrieval, search, and AI-powered contextual understanding.
Tests use modern Python 3.13 patterns with proper mocking and async patterns.
Includes property-based testing with Hypothesis for robust coverage.
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryService,
    PreferencesUpdateRequest,
    UserContextResponse,
    get_memory_service,
)


class TestMemoryServiceModels:
    """Test Pydantic models for memory service."""

    def test_memory_search_result_creation(self):
        """Test MemorySearchResult model creation."""
        now = datetime.now(UTC)
        result = MemorySearchResult(
            id="test-id",
            memory="Test memory content",
            metadata={"test": "value"},
            categories=["test_category"],
            similarity=0.95,
            created_at=now,
            user_id="user-123",
        )

        assert result.id == "test-id"
        assert result.memory == "Test memory content"
        assert result.metadata == {"test": "value"}
        assert result.categories == ["test_category"]
        assert result.similarity == 0.95
        assert result.user_id == "user-123"

    def test_conversation_memory_request_validation(self):
        """Test ConversationMemoryRequest validation."""
        # Valid request
        request = ConversationMemoryRequest(
            messages=[{"role": "user", "content": "Hello"}],
            session_id="session-123",
            trip_id="trip-456",
        )
        assert len(request.messages) == 1
        assert request.session_id == "session-123"

        # Invalid - empty messages should still be allowed for flexibility
        request_empty = ConversationMemoryRequest(messages=[])
        assert request_empty.messages == []

    def test_memory_search_request_validation(self):
        """Test MemorySearchRequest validation."""
        # Valid request
        request = MemorySearchRequest(
            query="test query", limit=10, similarity_threshold=0.8
        )
        assert request.query == "test query"
        assert request.limit == 10
        assert request.similarity_threshold == 0.8

        # Test bounds validation
        with pytest.raises(ValidationError):
            MemorySearchRequest(query="", limit=0)  # Empty query, invalid limit

        with pytest.raises(ValidationError):
            MemorySearchRequest(query="test", limit=100)  # Limit too high

        with pytest.raises(ValidationError):
            MemorySearchRequest(
                query="test", similarity_threshold=1.5
            )  # Invalid threshold

    def test_preferences_update_request_validation(self):
        """Test PreferencesUpdateRequest validation."""
        # Valid request
        request = PreferencesUpdateRequest(
            preferences={"hotel_type": "boutique"}, category="accommodation"
        )
        assert request.preferences == {"hotel_type": "boutique"}
        assert request.category == "accommodation"

        # Empty preferences should raise error
        with pytest.raises(ValidationError) as exc_info:
            PreferencesUpdateRequest(preferences={})
        assert "Preferences cannot be empty" in str(exc_info.value)

    @given(
        st.text(min_size=1, max_size=1000),
        st.integers(min_value=1, max_value=50),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_memory_search_request_property_based(self, query, limit, threshold):
        """Property-based test for MemorySearchRequest."""
        request = MemorySearchRequest(
            query=query, limit=limit, similarity_threshold=threshold
        )
        assert len(request.query) >= 1
        assert 1 <= request.limit <= 50
        assert 0.0 <= request.similarity_threshold <= 1.0


class TestMemoryService:
    """Test suite for MemoryService with comprehensive coverage."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service with comprehensive memory operations."""
        db = AsyncMock()
        db.create_memory = AsyncMock()
        db.get_memory_by_id = AsyncMock()
        db.get_memories_by_filters = AsyncMock(return_value=[])
        db.update_memory = AsyncMock()
        db.delete_memory = AsyncMock(return_value=True)
        db.get_user_memory_stats = AsyncMock(
            return_value={
                "total_memories": 0,
                "memory_types": {},
            }
        )
        return db

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 client with comprehensive operations."""
        mem0 = MagicMock()
        mem0.add = MagicMock()
        mem0.search = MagicMock(return_value={"results": []})
        mem0.get_all = MagicMock(return_value={"results": []})
        mem0.update = MagicMock()
        mem0.delete = MagicMock()
        mem0.history = MagicMock(return_value=[])
        return mem0

    @pytest.fixture
    def memory_service(self, mock_mem0_client, mock_settings):
        """Create MemoryService instance with fully mocked dependencies."""
        with (
            patch("tripsage_core.config.get_settings", return_value=mock_settings),
            patch(
                "tripsage_core.services.infrastructure.get_database_service",
                return_value=AsyncMock(),
            ),
            patch(
                "tripsage_core.utils.connection_utils.DatabaseURLParser"
            ) as mock_parser,
            patch(
                "tripsage_core.utils.connection_utils.SecureDatabaseConnectionManager"
            ) as mock_conn_mgr,
            patch("mem0.Memory") as mock_memory_class,
        ):
            # Mock URL parser
            mock_credentials = MagicMock()
            mock_credentials.hostname = "localhost"
            mock_credentials.port = 5432
            mock_credentials.database = "test_db"
            mock_credentials.username = "test_user"
            mock_credentials.password = "test_pass"
            mock_credentials.query_params = {}
            mock_parser.return_value.parse_url.return_value = mock_credentials

            # Mock connection manager
            mock_conn_mgr.return_value.parse_and_validate_url = AsyncMock()
            mock_conn_mgr.return_value.circuit_breaker.call = AsyncMock()
            mock_conn_mgr.return_value.retry_handler.execute_with_retry = AsyncMock()

            # Mock Mem0 Memory class
            mock_memory_class.from_config.return_value = mock_mem0_client

            service = MemoryService()
            service._connected = True
            return service

    @pytest.fixture
    def sample_conversation_request(self):
        """Sample conversation memory request."""
        return ConversationMemoryRequest(
            messages=[
                {
                    "role": "user",
                    "content": "I prefer boutique hotels in historic city centers",
                },
                {
                    "role": "assistant",
                    "content": (
                        "I'll remember your preference for boutique hotels in "
                        "historic areas."
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

    @pytest.mark.asyncio
    async def test_service_initialization_success(self, mock_settings):
        """Test successful service initialization."""
        with (
            patch("tripsage_core.config.get_settings", return_value=mock_settings),
            patch(
                "tripsage_core.services.infrastructure.get_database_service",
                return_value=AsyncMock(),
            ),
            patch(
                "tripsage_core.utils.connection_utils.DatabaseURLParser"
            ) as mock_parser,
            patch(
                "tripsage_core.utils.connection_utils.SecureDatabaseConnectionManager"
            ),
            patch("mem0.Memory") as mock_memory_class,
        ):
            # Mock successful URL parsing
            mock_credentials = MagicMock()
            mock_credentials.hostname = "localhost"
            mock_credentials.port = 5432
            mock_credentials.database = "test_db"
            mock_credentials.username = "test_user"
            mock_credentials.password = "test_pass"
            mock_credentials.query_params = {}
            mock_parser.return_value.parse_url.return_value = mock_credentials

            mock_memory_instance = MagicMock()
            mock_memory_class.from_config.return_value = mock_memory_instance

            service = MemoryService()

            assert service.memory == mock_memory_instance
            assert service.cache_ttl == 300
            assert not service._connected

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self, mock_settings):
        """Test service initialization with Mem0 import failure."""
        with (
            patch("tripsage_core.config.get_settings", return_value=mock_settings),
            patch(
                "tripsage_core.services.infrastructure.get_database_service",
                return_value=AsyncMock(),
            ),
            patch(
                "tripsage_core.utils.connection_utils.DatabaseURLParser"
            ) as mock_parser,
            patch(
                "tripsage_core.utils.connection_utils.SecureDatabaseConnectionManager"
            ),
            patch("mem0.Memory", side_effect=ImportError("Mem0 not available")),
        ):
            # Mock URL parsing
            mock_credentials = MagicMock()
            mock_credentials.hostname = "localhost"
            mock_credentials.port = 5432
            mock_credentials.database = "test_db"
            mock_credentials.username = "test_user"
            mock_credentials.password = "test_pass"
            mock_credentials.query_params = {}
            mock_parser.return_value.parse_url.return_value = mock_credentials

            service = MemoryService()

            assert service.memory is None

    @pytest.mark.asyncio
    async def test_connect_success(self, memory_service, mock_mem0_client):
        """Test successful connection."""
        memory_service._connected = False

        await memory_service.connect()
        assert memory_service._connected

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, memory_service):
        """Test connect when already connected."""
        memory_service._connected = True

        await memory_service.connect()
        assert memory_service._connected

    @pytest.mark.asyncio
    async def test_connect_no_memory_backend(self, memory_service):
        """Test connect when no memory backend available."""
        memory_service.memory = None
        memory_service._connected = False

        await memory_service.connect()
        assert not memory_service._connected

    @pytest.mark.asyncio
    async def test_close(self, memory_service):
        """Test service close."""
        memory_service._connected = True
        memory_service._cache = {"test": ([], time.time())}

        await memory_service.close()
        assert not memory_service._connected
        assert len(memory_service._cache) == 0

    @pytest.mark.asyncio
    async def test_add_conversation_memory_success(
        self,
        memory_service,
        mock_mem0_client,
        sample_conversation_request,
    ):
        """Test successful conversation memory addition."""
        user_id = str(uuid4())

        # Mock Mem0 response
        mock_mem0_client.add.return_value = {
            "results": [
                {
                    "id": "mem0_abc123",
                    "memory": "User prefers boutique hotels in historic city centers",
                    "metadata": {
                        "domain": "travel_planning",
                        "session_id": sample_conversation_request.session_id,
                    },
                }
            ],
            "usage": {"total_tokens": 150},
        }

        result = await memory_service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        # Assertions
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "mem0_abc123"
        assert "boutique hotels" in result["results"][0]["memory"]

        # Verify service calls
        mock_mem0_client.add.assert_called_once()
        call_args = mock_mem0_client.add.call_args
        assert call_args[1]["user_id"] == user_id
        assert call_args[1]["messages"] == sample_conversation_request.messages

    @pytest.mark.asyncio
    async def test_add_conversation_memory_service_unavailable(
        self, sample_conversation_request
    ):
        """Test memory addition when service is unavailable."""
        # Create service without Mem0 backend
        service = MemoryService()
        service.memory = None

        user_id = str(uuid4())
        result = await service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        assert result["error"] == "Memory service not available"
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_memories_success(self, memory_service, mock_mem0_client):
        """Test successful memory search."""
        user_id = str(uuid4())

        search_request = MemorySearchRequest(
            query="hotel preferences",
            limit=10,
        )

        # Mock Mem0 search response
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_123",
                    "memory": "User prefers boutique hotels",
                    "metadata": {},
                    "categories": ["accommodation", "preferences"],
                    "score": 0.92,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        results = await memory_service.search_memories(user_id, search_request)

        assert len(results) == 1
        assert results[0].id == "mem0_123"
        assert results[0].similarity == 0.92
        assert "boutique hotels" in results[0].memory
        assert results[0].categories == ["accommodation", "preferences"]

        mock_mem0_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories_with_similarity_threshold(
        self, memory_service, mock_mem0_client
    ):
        """Test memory search with similarity threshold filtering."""
        user_id = str(uuid4())

        search_request = MemorySearchRequest(
            query="hotel preferences",
            limit=10,
            similarity_threshold=0.8,
        )

        # Mock Mem0 search response with mixed similarity scores
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_high",
                    "memory": "High similarity memory",
                    "metadata": {},
                    "categories": [],
                    "score": 0.95,
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": "mem0_low",
                    "memory": "Low similarity memory",
                    "metadata": {},
                    "categories": [],
                    "score": 0.5,  # Below threshold
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
        }

        results = await memory_service.search_memories(user_id, search_request)

        # Only high similarity result should be returned
        assert len(results) == 1
        assert results[0].id == "mem0_high"
        assert results[0].similarity == 0.95

    @pytest.mark.asyncio
    async def test_search_memories_caching(self, memory_service, mock_mem0_client):
        """Test memory search caching behavior."""
        user_id = str(uuid4())
        search_request = MemorySearchRequest(query="test query", limit=5)

        # Mock response
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_cached",
                    "memory": "Cached memory",
                    "metadata": {},
                    "categories": [],
                    "score": 0.8,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        # First search - should call Mem0
        results1 = await memory_service.search_memories(user_id, search_request)
        assert len(results1) == 1
        assert mock_mem0_client.search.call_count == 1

        # Second search - should use cache
        results2 = await memory_service.search_memories(user_id, search_request)
        assert len(results2) == 1
        assert mock_mem0_client.search.call_count == 1  # No additional call

        # Results should be identical
        assert results1[0].id == results2[0].id

    @pytest.mark.asyncio
    async def test_get_user_context_success(self, memory_service, mock_mem0_client):
        """Test successful user context retrieval."""
        user_id = str(uuid4())

        # Mock get_all for user context
        mock_mem0_client.get_all.return_value = {
            "results": [
                {
                    "memory": "Prefers boutique hotels",
                    "metadata": {},
                    "categories": ["preferences"],
                },
                {
                    "memory": "Visited Tokyo in 2023",
                    "metadata": {},
                    "categories": ["past_trips"],
                },
                {
                    "memory": "Budget around $3000 for week-long trips",
                    "metadata": {},
                    "categories": ["budget_patterns"],
                },
            ]
        }

        result = await memory_service.get_user_context(user_id)

        assert isinstance(result, UserContextResponse)
        assert len(result.preferences) == 1
        assert len(result.past_trips) == 1
        assert len(result.budget_patterns) == 1
        assert isinstance(result.summary, str)
        assert isinstance(result.insights, dict)

        # Verify get_all was called
        mock_mem0_client.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_context_empty(self, memory_service, mock_mem0_client):
        """Test user context with no memories."""
        user_id = str(uuid4())

        mock_mem0_client.get_all.return_value = {"results": []}

        result = await memory_service.get_user_context(user_id)

        assert isinstance(result, UserContextResponse)
        assert len(result.preferences) == 0
        assert len(result.past_trips) == 0
        assert "New user with limited travel history" in result.summary

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(
        self, memory_service, mock_mem0_client
    ):
        """Test successful preferences update."""
        user_id = str(uuid4())

        update_request = PreferencesUpdateRequest(
            preferences={
                "accommodation_type": "boutique_hotel",
                "budget_range": "medium",
                "travel_style": "cultural",
            },
            category="travel_preferences",
        )

        # Mock add for preference update (uses conversation-style update)
        mock_mem0_client.add.return_value = {
            "results": [{"id": "mem0_new_pref", "memory": "Updated preferences"}],
            "usage": {"total_tokens": 50},
        }

        result = await memory_service.update_user_preferences(user_id, update_request)

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "mem0_new_pref"

        # Verify add was called with formatted messages
        mock_mem0_client.add.assert_called_once()
        call_args = mock_mem0_client.add.call_args
        assert call_args[1]["user_id"] == user_id
        assert len(call_args[1]["messages"]) == 2

    @pytest.mark.asyncio
    async def test_delete_user_memories_specific(
        self, memory_service, mock_mem0_client
    ):
        """Test deletion of specific user memories."""
        user_id = str(uuid4())
        memory_ids = ["mem0_1", "mem0_2"]

        # Mock successful deletions
        mock_mem0_client.delete.return_value = True

        result = await memory_service.delete_user_memories(user_id, memory_ids)

        assert result["success"] is True
        assert result["deleted_count"] == 2

        # Verify delete was called for each memory
        assert mock_mem0_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_user_memories_all(self, memory_service, mock_mem0_client):
        """Test deletion of all user memories."""
        user_id = str(uuid4())

        # Mock get_all to return some memories
        mock_mem0_client.get_all.return_value = {
            "results": [
                {"id": "mem0_1", "memory": "Memory 1"},
                {"id": "mem0_2", "memory": "Memory 2"},
            ]
        }
        mock_mem0_client.delete.return_value = True

        result = await memory_service.delete_user_memories(user_id)

        assert result["success"] is True
        assert result["deleted_count"] == 2

        # Verify get_all and delete calls
        mock_mem0_client.get_all.assert_called_once()
        assert mock_mem0_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_extraction_error_handling(
        self, memory_service, mock_mem0_client, sample_conversation_request
    ):
        """Test error handling in memory extraction."""
        user_id = str(uuid4())

        # Mock extraction failure
        mock_mem0_client.add.side_effect = Exception("Extraction failed")

        result = await memory_service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        assert "error" in result
        assert result["results"] == []
        assert "Extraction failed" in result["error"]

    @pytest.mark.asyncio
    async def test_search_error_handling(self, memory_service, mock_mem0_client):
        """Test error handling in memory search."""
        user_id = str(uuid4())
        search_request = MemorySearchRequest(query="test query")

        # Mock search failure
        mock_mem0_client.search.side_effect = Exception("Search failed")

        results = await memory_service.search_memories(user_id, search_request)

        assert results == []

    @pytest.mark.asyncio
    async def test_cache_invalidation(
        self, memory_service, mock_mem0_client, sample_conversation_request
    ):
        """Test cache invalidation after memory updates."""
        user_id = str(uuid4())

        # First search (should cache)
        search_request = MemorySearchRequest(query="hotels", limit=5)
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_1",
                    "memory": "Old hotel preference",
                    "score": 0.8,
                    "metadata": {},
                    "categories": [],
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        results1 = await memory_service.search_memories(user_id, search_request)
        assert len(results1) == 1

        # Add new memory (should invalidate cache)
        mock_mem0_client.add.return_value = {"results": [{"id": "mem0_2"}]}
        await memory_service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        # Second search (should not use cache)
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_1",
                    "memory": "Old hotel preference",
                    "score": 0.8,
                    "metadata": {},
                    "categories": [],
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": "mem0_2",
                    "memory": "New hotel preference",
                    "score": 0.9,
                    "metadata": {},
                    "categories": [],
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
        }

        results2 = await memory_service.search_memories(user_id, search_request)
        assert len(results2) == 2

        # Verify search was called twice (not cached second time)
        assert mock_mem0_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_get_memory_service_dependency(self):
        """Test the dependency injection function."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService"
        ) as MockMemoryService:
            mock_instance = MagicMock()
            MockMemoryService.return_value = mock_instance

            service = await get_memory_service()
            assert service == mock_instance

    @pytest.mark.asyncio
    async def test_search_with_filters(self, memory_service, mock_mem0_client):
        """Test memory search with various filters."""
        user_id = str(uuid4())

        search_request = MemorySearchRequest(
            query="travel preferences",
            limit=20,
            filters={
                "categories": ["preferences", "travel"],
                "date_range": {
                    "start": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                    "end": datetime.now(UTC).isoformat(),
                },
            },
            similarity_threshold=0.8,
        )

        mock_mem0_client.search.return_value = {"results": []}

        results = await memory_service.search_memories(user_id, search_request)

        assert results == []

        # Verify filters were passed
        call_args = mock_mem0_client.search.call_args
        assert call_args[1]["query"] == "travel preferences"
        assert call_args[1]["limit"] == 20
        assert call_args[1]["filters"] == search_request.filters

    @pytest.mark.asyncio
    async def test_memory_service_not_connected(self):
        """Test operations when memory service is not connected."""
        service = MemoryService()
        service.memory = MagicMock()
        service._connected = False

        user_id = str(uuid4())
        search_request = MemorySearchRequest(query="test")

        # Should return empty results when not connected
        results = await service.search_memories(user_id, search_request)
        assert results == []

        # Should return error in conversation memory
        conversation_request = ConversationMemoryRequest(messages=[])
        result = await service.add_conversation_memory(user_id, conversation_request)
        assert result["error"] == "Memory service not available"

    @pytest.mark.asyncio
    async def test_travel_context_enrichment(self, memory_service, mock_mem0_client):
        """Test travel-specific context enrichment."""
        user_id = str(uuid4())

        # Search with travel context
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem0_travel_1",
                    "memory": (
                        "Loves exploring destinations and local markets "
                        "with good budget"
                    ),
                    "metadata": {},
                    "categories": ["preferences"],
                    "score": 0.85,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        results = await memory_service.search_memories(
            user_id, MemorySearchRequest(query="market experiences")
        )

        assert len(results) == 1
        # Check that enrichment added travel context flags
        result = results[0]
        assert (
            result.metadata.get("has_location") is True
        )  # "destinations" keyword found
        assert result.metadata.get("has_budget") is True  # "budget" keyword found
        assert result.categories == ["preferences"]

    def test_cache_management(self, memory_service):
        """Test cache size management."""
        # Fill cache beyond limit
        for i in range(1100):  # More than 1000 limit
            cache_key = f"test_key_{i}"
            memory_service._cache[cache_key] = ([], time.time())

        # Add one more to trigger cleanup
        memory_service._cache_result("trigger_cleanup", [])

        # Should be reduced to ~800 entries (1000 - 200)
        assert len(memory_service._cache) <= 1000

    def test_cache_key_generation(self, memory_service):
        """Test cache key generation."""
        user_id = "test_user"
        search_request = MemorySearchRequest(
            query="test query", limit=10, filters={"category": "test"}
        )

        key1 = memory_service._generate_cache_key(user_id, search_request)
        key2 = memory_service._generate_cache_key(user_id, search_request)

        # Same input should generate same key
        assert key1 == key2

        # Different input should generate different key
        search_request2 = MemorySearchRequest(query="different query", limit=10)
        key3 = memory_service._generate_cache_key(user_id, search_request2)
        assert key1 != key3

    def test_datetime_parsing(self, memory_service):
        """Test datetime parsing utility."""
        # Valid ISO format
        dt_str = "2023-12-25T15:30:00Z"
        parsed = memory_service._parse_datetime(dt_str)
        assert isinstance(parsed, datetime)

        # Invalid format should return current time
        invalid_str = "invalid-date"
        parsed_invalid = memory_service._parse_datetime(invalid_str)
        assert isinstance(parsed_invalid, datetime)

    def test_insights_analysis(self, memory_service):
        """Test travel insights analysis methods."""
        # Test destination analysis
        context = {
            "past_trips": [
                {"memory": "Visited Japan last year"},
                {"memory": "Loved traveling to France"},
            ],
            "saved_destinations": [
                {"memory": "Want to visit Italy next"},
            ],
        }

        insights = memory_service._analyze_destinations(context)
        assert "most_visited" in insights
        assert "destination_count" in insights

        # Test budget analysis
        budget_context = {
            "budget_patterns": [
                {"memory": "Spent $2000 on last trip"},
                {"memory": "Budget of $3000 for Europe"},
            ]
        }

        budget_insights = memory_service._analyze_budgets(budget_context)
        assert "average_budget" in budget_insights

        # Test with no budget data
        empty_budget_context = {"budget_patterns": []}
        empty_budget_insights = memory_service._analyze_budgets(empty_budget_context)
        assert "budget_info" in empty_budget_insights

    def test_activity_analysis(self, memory_service):
        """Test activity preferences analysis."""
        context = {
            "activity_preferences": [
                {"memory": "Love visiting museums and cultural sites"},
                {"memory": "Enjoy hiking and beach activities"},
            ],
            "preferences": [
                {"memory": "Prefer cultural experiences and dining"},
            ],
        }

        insights = memory_service._analyze_activities(context)
        assert "preferred_activities" in insights
        assert "activity_style" in insights

    def test_travel_style_analysis(self, memory_service):
        """Test travel style analysis."""
        context = {
            "preferences": [
                {"memory": "Love luxury hotels and premium experiences"},
                {"memory": "Travel with family and kids"},
            ],
            "travel_style": [
                {"memory": "Prefer solo adventures"},
            ],
        }

        insights = memory_service._analyze_travel_style(context)
        assert "travel_styles" in insights
        assert "primary_style" in insights

        # Should detect luxury and family styles
        detected_styles = insights["travel_styles"]
        assert "luxury" in detected_styles
        assert "family" in detected_styles

    def test_context_summary_generation(self, memory_service):
        """Test context summary generation."""
        context = {
            "preferences": [],
            "past_trips": [],
        }
        insights = {
            "preferred_destinations": {"most_visited": ["Japan", "France"]},
            "travel_style": {"primary_style": "luxury"},
            "budget_range": {"average_budget": 2500},
            "preferred_activities": {"preferred_activities": ["museum", "dining"]},
        }

        summary = memory_service._generate_context_summary(context, insights)
        assert isinstance(summary, str)
        assert "Japan" in summary or "France" in summary
        assert "luxury" in summary
        assert "2500" in summary

        # Test with empty insights
        empty_insights = {
            "preferred_destinations": {"most_visited": []},
            "travel_style": {"primary_style": "general"},
            "budget_range": {},
            "preferred_activities": {"preferred_activities": []},
        }

        empty_summary = memory_service._generate_context_summary(
            context, empty_insights
        )
        assert "New user with limited travel history" in empty_summary


class TestMemoryServicePropertyBased:
    """Property-based tests for MemoryService using Hypothesis."""

    @pytest.fixture
    def memory_service_for_property_tests(self, mock_settings):
        """Create memory service for property-based testing."""
        with (
            patch("tripsage_core.config.get_settings", return_value=mock_settings),
            patch(
                "tripsage_core.services.infrastructure.get_database_service",
                return_value=AsyncMock(),
            ),
            patch(
                "tripsage_core.utils.connection_utils.DatabaseURLParser"
            ) as mock_parser,
            patch(
                "tripsage_core.utils.connection_utils.SecureDatabaseConnectionManager"
            ),
            patch("mem0.Memory") as mock_memory_class,
        ):
            mock_credentials = MagicMock()
            mock_credentials.hostname = "localhost"
            mock_credentials.port = 5432
            mock_credentials.database = "test_db"
            mock_credentials.username = "test_user"
            mock_credentials.password = "test_pass"
            mock_credentials.query_params = {}
            mock_parser.return_value.parse_url.return_value = mock_credentials

            mock_mem0_client = MagicMock()
            mock_mem0_client.search.return_value = {"results": []}
            mock_memory_class.from_config.return_value = mock_mem0_client

            service = MemoryService()
            service._connected = True
            return service

    @given(
        st.text(min_size=1, max_size=100),
        st.integers(min_value=1, max_value=50),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @pytest.mark.asyncio
    async def test_search_with_random_inputs(
        self, memory_service_for_property_tests, query, limit, threshold
    ):
        """Property-based test for memory search with random valid inputs."""
        user_id = str(uuid4())
        search_request = MemorySearchRequest(
            query=query, limit=limit, similarity_threshold=threshold
        )

        results = await memory_service_for_property_tests.search_memories(
            user_id, search_request
        )

        # Results should always be a list
        assert isinstance(results, list)
        # Results length should not exceed the limit
        assert len(results) <= limit

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
            min_size=1,
            max_size=10,
        )
    )
    @pytest.mark.asyncio
    async def test_preferences_update_with_random_data(
        self, memory_service_for_property_tests, preferences_data
    ):
        """Property-based test for preferences update with random data."""
        user_id = str(uuid4())

        try:
            update_request = PreferencesUpdateRequest(
                preferences=preferences_data, category="test_category"
            )

            # Mock successful add
            memory_service_for_property_tests.memory.add.return_value = {
                "results": [{"id": "test_id", "memory": "test memory"}],
                "usage": {"total_tokens": 10},
            }

            result = await memory_service_for_property_tests.update_user_preferences(
                user_id, update_request
            )

            # Should always return a dict with results
            assert isinstance(result, dict)
            assert "results" in result

        except ValidationError:
            # Some random data might not pass validation, which is acceptable
            pass

    @given(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10))
    @pytest.mark.asyncio
    async def test_delete_memories_with_random_ids(
        self, memory_service_for_property_tests, memory_ids
    ):
        """Property-based test for memory deletion with random IDs."""
        user_id = str(uuid4())

        # Mock successful deletions
        memory_service_for_property_tests.memory.delete.return_value = True

        result = await memory_service_for_property_tests.delete_user_memories(
            user_id, memory_ids if memory_ids else None
        )

        # Should always return a dict with success and deleted_count
        assert isinstance(result, dict)
        assert "success" in result
        assert "deleted_count" in result
        assert isinstance(result["deleted_count"], int)
        assert result["deleted_count"] >= 0


class TestMemoryServiceIntegration:
    """Integration-style tests for MemoryService (still using mocks but
    testing workflows).
    """

    @pytest.fixture
    def integration_memory_service(self, mock_settings):
        """Create memory service for integration testing."""
        with (
            patch("tripsage_core.config.get_settings", return_value=mock_settings),
            patch(
                "tripsage_core.services.infrastructure.get_database_service",
                return_value=AsyncMock(),
            ),
            patch(
                "tripsage_core.utils.connection_utils.DatabaseURLParser"
            ) as mock_parser,
            patch(
                "tripsage_core.utils.connection_utils.SecureDatabaseConnectionManager"
            ) as mock_conn_mgr,
            patch("mem0.Memory") as mock_memory_class,
        ):
            # Set up comprehensive mocking
            mock_credentials = MagicMock()
            mock_credentials.hostname = "localhost"
            mock_credentials.port = 5432
            mock_credentials.database = "test_db"
            mock_credentials.username = "test_user"
            mock_credentials.password = "test_pass"
            mock_credentials.query_params = {}
            mock_parser.return_value.parse_url.return_value = mock_credentials

            mock_conn_mgr.return_value.parse_and_validate_url = AsyncMock()
            mock_conn_mgr.return_value.circuit_breaker.call = AsyncMock()
            mock_conn_mgr.return_value.retry_handler.execute_with_retry = AsyncMock()

            mock_mem0_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_mem0_client

            service = MemoryService()
            return service, mock_mem0_client

    @pytest.mark.asyncio
    async def test_full_memory_workflow(self, integration_memory_service):
        """Test complete memory workflow: connect -> add -> search ->
        update -> delete.
        """
        service, mock_mem0_client = integration_memory_service
        user_id = str(uuid4())

        # 1. Connect
        await service.connect()
        assert service._connected

        # 2. Add conversation memory
        conversation_request = ConversationMemoryRequest(
            messages=[
                {"role": "user", "content": "I love beach resorts"},
                {
                    "role": "assistant",
                    "content": "I'll remember your preference for beach resorts",
                },
            ],
            session_id=str(uuid4()),
            metadata={"type": "accommodation_preference"},
        )

        mock_mem0_client.add.return_value = {
            "results": [{"id": "mem_beach", "memory": "User loves beach resorts"}],
            "usage": {"total_tokens": 50},
        }

        add_result = await service.add_conversation_memory(
            user_id, conversation_request
        )
        assert add_result["results"][0]["id"] == "mem_beach"

        # 3. Search for the memory
        search_request = MemorySearchRequest(query="beach preferences", limit=10)
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "mem_beach",
                    "memory": "User loves beach resorts",
                    "metadata": {},
                    "categories": ["preferences"],
                    "score": 0.95,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        search_results = await service.search_memories(user_id, search_request)
        assert len(search_results) == 1
        assert search_results[0].id == "mem_beach"

        # 4. Update preferences
        preferences_request = PreferencesUpdateRequest(
            preferences={"resort_type": "luxury_beach_resort"}, category="accommodation"
        )

        mock_mem0_client.add.return_value = {
            "results": [
                {"id": "mem_updated", "memory": "Updated beach resort preferences"}
            ],
            "usage": {"total_tokens": 30},
        }

        update_result = await service.update_user_preferences(
            user_id, preferences_request
        )
        assert "results" in update_result

        # 5. Get user context
        mock_mem0_client.get_all.return_value = {
            "results": [
                {
                    "memory": "User loves beach resorts",
                    "metadata": {},
                    "categories": ["preferences"],
                },
                {
                    "memory": "Updated beach resort preferences",
                    "metadata": {},
                    "categories": ["preferences"],
                },
            ]
        }

        context = await service.get_user_context(user_id)
        assert len(context.preferences) == 2

        # 6. Delete memories
        mock_mem0_client.delete.return_value = True
        delete_result = await service.delete_user_memories(
            user_id, ["mem_beach", "mem_updated"]
        )
        assert delete_result["success"] is True
        assert delete_result["deleted_count"] == 2

        # 7. Close service
        await service.close()
        assert not service._connected

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, integration_memory_service):
        """Test error recovery in memory operations."""
        service, mock_mem0_client = integration_memory_service
        user_id = str(uuid4())

        await service.connect()

        # Test search with error and recovery
        search_request = MemorySearchRequest(query="test query")

        # First call fails
        mock_mem0_client.search.side_effect = Exception("Network error")
        results = await service.search_memories(user_id, search_request)
        assert results == []

        # Recovery - subsequent call succeeds
        mock_mem0_client.search.side_effect = None
        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "recovered_mem",
                    "memory": "Recovered memory",
                    "metadata": {},
                    "categories": [],
                    "score": 0.8,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        recovered_results = await service.search_memories(user_id, search_request)
        assert len(recovered_results) == 1
        assert recovered_results[0].id == "recovered_mem"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, integration_memory_service):
        """Test concurrent memory operations."""
        import asyncio

        service, mock_mem0_client = integration_memory_service
        user_id = str(uuid4())

        await service.connect()

        # Set up mocks for concurrent operations
        mock_mem0_client.add.return_value = {
            "results": [{"id": "concurrent_mem", "memory": "Concurrent memory"}],
            "usage": {"total_tokens": 25},
        }

        mock_mem0_client.search.return_value = {
            "results": [
                {
                    "id": "search_mem",
                    "memory": "Search result",
                    "metadata": {},
                    "categories": [],
                    "score": 0.8,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ]
        }

        # Run multiple operations concurrently
        tasks = [
            service.add_conversation_memory(
                user_id,
                ConversationMemoryRequest(
                    messages=[{"role": "user", "content": f"Message {i}"}]
                ),
            )
            for i in range(3)
        ] + [
            service.search_memories(user_id, MemorySearchRequest(query=f"query {i}"))
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete without errors
        for result in results:
            assert not isinstance(result, Exception)

        # Should have 3 add results and 3 search results
        add_results = results[:3]
        search_results = results[3:]

        for add_result in add_results:
            assert isinstance(add_result, dict)
            assert "results" in add_result

        for search_result in search_results:
            assert isinstance(search_result, list)
