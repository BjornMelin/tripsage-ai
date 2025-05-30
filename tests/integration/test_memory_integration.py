"""
Integration tests for memory service integration across the application.

This module tests the complete memory workflow including storage, retrieval,
search, and integration with chat and planning services.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.agents.chat import ChatAgent
from tripsage.api.main import app
from tripsage_core.models.db.chat import ChatMessageDB, ChatSessionDB
from tripsage_core.models.db.user import UserDB
from tripsage_core.services.business.chat_service import ChatService
from tripsage_core.services.business.memory_service import MemoryService


class TestMemoryServiceIntegration:
    """Test complete memory service integration workflow."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return UserDB(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            is_active=True,
            api_keys={"default": "test-api-key"},
        )

    @pytest.fixture
    def mock_chat_session(self):
        """Mock chat session for testing."""
        return ChatSessionDB(
            id=uuid4(),
            user_id=uuid4(),
            title="Paris Trip Planning",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            metadata={"destination": "Paris", "budget": 3000},
        )

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service with realistic responses."""
        service = AsyncMock(spec=MemoryService)

        # Mock memory storage
        service.store_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem_123",
            "memories_stored": 3,
        }

        # Mock memory retrieval
        service.get_user_context.return_value = {
            "preferences": {
                "accommodation_type": "luxury",
                "budget_range": "high",
                "preferred_destinations": ["Europe", "Japan"],
                "travel_style": "cultural",
            },
            "travel_history": [
                {
                    "destination": "Rome",
                    "dates": "2023-05-01 to 2023-05-10",
                    "budget": 2500,
                    "satisfaction": 9,
                },
                {
                    "destination": "Barcelona",
                    "dates": "2023-08-15 to 2023-08-22",
                    "budget": 1800,
                    "satisfaction": 8,
                },
            ],
            "memories": [
                {
                    "id": "mem_1",
                    "content": "User loves historic architecture and museums",
                    "category": "interests",
                    "confidence": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                },
                {
                    "id": "mem_2",
                    "content": "Prefers hotels near city center with good transport links",
                    "category": "accommodation",
                    "confidence": 0.88,
                    "created_at": "2024-01-01T11:00:00Z",
                },
            ],
        }

        # Mock memory search
        service.search_memories.return_value = [
            {
                "content": "User searched for flights to Paris in spring",
                "metadata": {"destination": "Paris", "season": "spring"},
                "score": 0.92,
                "created_at": "2024-01-15T14:30:00Z",
            },
            {
                "content": "Asked about luxury hotels with spa facilities",
                "metadata": {"accommodation": "luxury", "amenity": "spa"},
                "score": 0.87,
                "created_at": "2024-01-10T16:45:00Z",
            },
        ]

        # Mock memory updates
        service.update_user_preferences.return_value = {
            "status": "success",
            "updated_preferences": ["budget_range", "accommodation_type"],
        }

        return service

    @pytest.fixture
    def mock_chat_service(self, mock_chat_session):
        """Mock chat service."""
        service = AsyncMock(spec=ChatService)
        service.get_session.return_value = mock_chat_session
        service.save_message.return_value = ChatMessageDB(
            id=uuid4(),
            session_id=mock_chat_session.id,
            user_id=mock_chat_session.user_id,
            role="user",
            content="Test message",
            timestamp=datetime.utcnow(),
            metadata={},
        )
        return service

    @pytest.fixture
    def mock_chat_agent(self):
        """Mock chat agent with memory integration."""
        agent = AsyncMock(spec=ChatAgent)
        agent.process_message.return_value = {
            "response": "Based on your previous trips to Rome and Barcelona, I see you enjoy historic destinations. Paris would be perfect for you! Given your preference for luxury hotels near city centers, I recommend the Four Seasons Hotel George V.",
            "tool_calls": [],
            "session_id": "test-session-123",
            "memory_context_used": True,
        }
        return agent

    @pytest.mark.asyncio
    async def test_memory_storage_during_chat_flow(
        self, client, mock_user, mock_memory_service, mock_chat_service, mock_chat_agent
    ):
        """Test memory storage during chat conversation flow."""
        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage_core.services.business.memory_service.MemoryService"
            ) as mock_mem_class:
                mock_mem_class.return_value = mock_memory_service

                with patch(
                    "tripsage_core.services.business.chat_service.ChatService"
                ) as mock_chat_class:
                    mock_chat_class.return_value = mock_chat_service

                    with patch(
                        "tripsage.api.core.dependencies.verify_api_key"
                    ) as mock_verify:
                        mock_verify.return_value = mock_user

                        session_id = str(uuid4())

                        # Simulate a conversation that should create memories
                        response = client.post(
                            "/api/chat",
                            json={
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": "I'm planning a honeymoon trip to Paris. We love luxury hotels and historic sites. Our budget is around $3000.",
                                    }
                                ],
                                "session_id": session_id,
                                "stream": False,
                            },
                            headers={"Authorization": "Bearer test-api-key"},
                        )

                        # Verify chat response
                        assert response.status_code == 200
                        response_data = response.json()
                        assert "rome" in response_data["response"].lower()
                        assert "luxury" in response_data["response"].lower()

                        # Verify memory storage was triggered
                        mock_memory_service.store_conversation_memory.assert_called()

                        # Check that user preferences were extracted and stored
                        call_args = (
                            mock_memory_service.store_conversation_memory.call_args
                        )
                        assert "honeymoon" in str(call_args)
                        assert "luxury" in str(call_args)
                        assert "3000" in str(call_args)

    @pytest.mark.asyncio
    async def test_memory_retrieval_for_context_flow(
        self, client, mock_user, mock_memory_service, mock_chat_agent
    ):
        """Test memory retrieval and context injection in chat flow."""
        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage_core.services.business.memory_service.MemoryService"
            ) as mock_mem_class:
                mock_mem_class.return_value = mock_memory_service

                with patch(
                    "tripsage.api.core.dependencies.get_session_memory"
                ) as mock_get_memory:
                    # Configure memory retrieval
                    mock_get_memory.return_value = {
                        "preferences": {"accommodation": "luxury", "budget": "high"},
                        "travel_history": ["Rome", "Barcelona"],
                        "recent_searches": ["Paris hotels", "spring travel Europe"],
                    }

                    with patch(
                        "tripsage.api.core.dependencies.verify_api_key"
                    ) as mock_verify:
                        mock_verify.return_value = mock_user

                        session_id = str(uuid4())

                        # Send a request that should use memory context
                        response = client.post(
                            "/api/chat",
                            json={
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": "What destination would you recommend for my next trip?",
                                    }
                                ],
                                "session_id": session_id,
                                "stream": False,
                            },
                            headers={"Authorization": "Bearer test-api-key"},
                        )

                        # Verify response uses memory context
                        assert response.status_code == 200
                        response_data = response.json()
                        assert "previous trips" in response_data["response"].lower()
                        assert "rome" in response_data["response"].lower()

                        # Verify memory was retrieved
                        mock_get_memory.assert_called()
                        mock_memory_service.get_user_context.assert_called()

    @pytest.mark.asyncio
    async def test_memory_search_integration_flow(
        self, client, mock_user, mock_memory_service
    ):
        """Test memory search functionality integration."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService"
        ) as mock_mem_class:
            mock_mem_class.return_value = mock_memory_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Test memory search endpoint
                response = client.post(
                    "/api/memory/search",
                    json={
                        "query": "luxury hotels Paris",
                        "limit": 10,
                        "filters": {
                            "category": "accommodation",
                            "destination": "Paris",
                        },
                    },
                    headers={"Authorization": "Bearer test-api-key"},
                )

                # Verify search response
                assert response.status_code == 200
                response_data = response.json()
                assert "memories" in response_data
                assert len(response_data["memories"]) > 0

                # Check memory content
                memories = response_data["memories"]
                assert any("luxury" in mem["content"].lower() for mem in memories)

                # Verify service was called
                mock_memory_service.search_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_preference_update_flow(
        self, client, mock_user, mock_memory_service
    ):
        """Test memory preference update flow."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService"
        ) as mock_mem_class:
            mock_mem_class.return_value = mock_memory_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Test preference update
                response = client.put(
                    "/api/memory/preferences",
                    json={
                        "preferences": {
                            "accommodation_type": "boutique",
                            "budget_range": "medium-high",
                            "travel_style": "adventure",
                            "dietary_restrictions": ["vegetarian"],
                        }
                    },
                    headers={"Authorization": "Bearer test-api-key"},
                )

                # Verify update response
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "success"

                # Verify service was called with correct data
                mock_memory_service.update_user_preferences.assert_called_once()
                call_args = mock_memory_service.update_user_preferences.call_args[0]
                assert call_args[1]["accommodation_type"] == "boutique"
                assert "vegetarian" in call_args[1]["dietary_restrictions"]

    @pytest.mark.asyncio
    async def test_memory_cross_session_persistence_flow(
        self, client, mock_user, mock_memory_service, mock_chat_agent
    ):
        """Test memory persistence across different chat sessions."""
        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage_core.services.business.memory_service.MemoryService"
            ) as mock_mem_class:
                mock_mem_class.return_value = mock_memory_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    # First session - establish preferences
                    session_1 = str(uuid4())
                    response1 = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "I prefer luxury accommodations and have a high budget for travel",
                                }
                            ],
                            "session_id": session_1,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    assert response1.status_code == 200

                    # Second session - should remember preferences
                    session_2 = str(uuid4())
                    response2 = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {"role": "user", "content": "Plan a trip to Tokyo"}
                            ],
                            "session_id": session_2,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    assert response2.status_code == 200
                    response_data = response2.json()

                    # Should reference previous preferences
                    assert "luxury" in response_data["response"].lower()

                    # Verify memory was accessed for context in both sessions
                    assert mock_memory_service.get_user_context.call_count >= 2

    @pytest.mark.asyncio
    async def test_memory_error_handling_flow(
        self, client, mock_user, mock_memory_service, mock_chat_agent
    ):
        """Test memory service error handling and fallback."""
        # Configure memory service to fail
        mock_memory_service.get_user_context.side_effect = Exception(
            "Memory service unavailable"
        )
        mock_memory_service.store_conversation_memory.side_effect = Exception(
            "Storage failed"
        )

        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage_core.services.business.memory_service.MemoryService"
            ) as mock_mem_class:
                mock_mem_class.return_value = mock_memory_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    session_id = str(uuid4())

                    # Chat should still work without memory
                    response = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {"role": "user", "content": "Help me plan a trip"}
                            ],
                            "session_id": session_id,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Chat should succeed despite memory errors
                    assert response.status_code == 200

                    # Verify agent was still called
                    mock_chat_agent.process_message.assert_called()

    @pytest.mark.asyncio
    async def test_memory_concurrent_operations_flow(
        self, client, mock_user, mock_memory_service
    ):
        """Test concurrent memory operations."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService"
        ) as mock_mem_class:
            mock_mem_class.return_value = mock_memory_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Create multiple concurrent memory operations
                tasks = []

                # Concurrent memory searches
                for i in range(3):
                    task = asyncio.create_task(
                        asyncio.to_thread(
                            client.post,
                            "/api/memory/search",
                            json={"query": f"search query {i}", "limit": 5},
                            headers={"Authorization": "Bearer test-api-key"},
                        )
                    )
                    tasks.append(task)

                # Wait for all operations to complete
                responses = await asyncio.gather(*tasks)

                # Verify all operations succeeded
                for response in responses:
                    assert response.status_code == 200

                # Verify service was called for each operation
                assert mock_memory_service.search_memories.call_count == 3

    @pytest.mark.asyncio
    async def test_memory_integration_with_planning_flow(
        self, client, mock_user, mock_memory_service, mock_chat_agent
    ):
        """Test memory integration with trip planning workflow."""
        # Configure agent to use memory for planning
        mock_chat_agent.process_message.return_value = {
            "response": "Based on your travel history to Rome and Barcelona, and your preference for luxury hotels, I'll create a 7-day Paris itinerary focusing on historic sites and upscale accommodations.",
            "tool_calls": [
                {
                    "id": "tool_plan_123",
                    "function": {
                        "name": "create_itinerary",
                        "arguments": '{"destination": "Paris", "duration": 7, "style": "luxury_cultural", "budget": 3000}',
                    },
                }
            ],
            "session_id": "test-session-123",
            "memory_context_used": True,
        }

        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage_core.services.business.memory_service.MemoryService"
            ) as mock_mem_class:
                mock_mem_class.return_value = mock_memory_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    session_id = str(uuid4())

                    # Request trip planning using memory context
                    response = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Create a detailed itinerary for Paris based on my travel preferences",
                                }
                            ],
                            "session_id": session_id,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify planning response uses memory
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "travel history" in response_data["response"].lower()
                    assert "luxury" in response_data["response"].lower()
                    assert "tool_calls" in response_data

                    # Verify memory was used for context
                    mock_memory_service.get_user_context.assert_called()

                    # Verify planning tool was called with memory-informed parameters
                    tool_call = response_data["tool_calls"][0]
                    assert tool_call["function"]["name"] == "create_itinerary"
                    assert "luxury_cultural" in tool_call["function"]["arguments"]
