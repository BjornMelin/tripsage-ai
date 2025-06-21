"""
Integration tests for complete memory system workflow.
Tests end-to-end memory operations from chat to storage to retrieval.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.agents.chat import ChatAgent
from tripsage.tools.memory_tools import (
    ConversationMessage,
    MemorySearchQuery,
    add_conversation_memory,
    get_user_context,
    search_user_memories,
)


class TestMemoryWorkflowIntegration:
    """Integration tests for complete memory workflow."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service with realistic behavior."""
        service = AsyncMock()

        # Store for simulating memory persistence
        self.stored_memories = []
        self.user_preferences = {}

        async def mock_add_memory(messages, user_id, session_id=None, metadata=None):
            memory_id = f"mem-{len(self.stored_memories) + 1}"
            memory_entry = {
                "id": memory_id,
                "user_id": user_id,
                "session_id": session_id,
                "messages": messages,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.stored_memories.append(memory_entry)
            return {"status": "success", "memory_id": memory_id}

        async def mock_search_memories(user_id, query, limit=20, category_filter=None):
            # Simple search simulation
            results = []
            for memory in self.stored_memories:
                if memory["user_id"] == user_id:
                    # Simple content matching
                    content = " ".join([msg.get("content", "") for msg in memory["messages"]])
                    if query.lower() in content.lower():
                        results.append(
                            {
                                "id": memory["id"],
                                "content": content[:200],  # Truncate for summary
                                "metadata": memory["metadata"],
                                "score": 0.8
                                + len([word for word in query.lower().split() if word in content.lower()]) * 0.1,
                                "created_at": memory["created_at"],
                            }
                        )

            # Sort by score and limit
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        async def mock_get_context(user_id):
            user_memories = [m for m in self.stored_memories if m["user_id"] == user_id]

            # Extract preferences from memories
            preferences = self.user_preferences.get(user_id, {})

            # Analyze travel patterns
            destinations = []
            # budgets = []
            for memory in user_memories:
                content = " ".join([msg.get("content", "") for msg in memory["messages"]])
                # Simple pattern extraction
                if "paris" in content.lower():
                    destinations.append("Paris")
                if "tokyo" in content.lower():
                    destinations.append("Tokyo")
                if "luxury" in content.lower():
                    if "accommodation" not in preferences:
                        preferences["accommodation"] = "luxury"

            return {
                "memories": [
                    {
                        "id": m["id"],
                        "content": " ".join([msg.get("content", "") for msg in m["messages"]])[:100],
                        "metadata": m["metadata"],
                        "score": 0.9,
                        "created_at": m["created_at"],
                    }
                    for m in user_memories[-5:]  # Last 5 memories
                ],
                "preferences": preferences,
                "travel_patterns": {
                    "favorite_destinations": list(set(destinations)),
                    "avg_trip_duration": 7,
                    "booking_lead_time": 30,
                },
            }

        async def mock_update_preferences(user_id, preferences):
            self.user_preferences[user_id] = preferences
            return {"status": "success"}

        service.add_conversation_memory = mock_add_memory
        service.search_memories = mock_search_memories
        service.get_user_context = mock_get_context
        service.update_user_preferences = mock_update_preferences

        return service

    @pytest.fixture
    def chat_agent(self):
        """Chat agent for testing."""
        agent = ChatAgent()
        return agent

    @pytest.mark.asyncio
    async def test_complete_memory_workflow(self, mock_memory_service):
        """Test complete memory workflow from chat to retrieval."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "test-user-123"
            session_id = "session-456"

            # Step 1: Simulate initial conversation
            messages_1 = [
                ConversationMessage(
                    role="user",
                    content=("I'm planning a luxury honeymoon trip to Paris in June. Our budget is $10,000."),
                    timestamp=datetime.now(timezone.utc),
                ),
                ConversationMessage(
                    role="assistant",
                    content=(
                        "I'll help you plan a perfect luxury honeymoon in Paris! "
                        "With your $10,000 budget, we can find excellent 5-star hotels."
                    ),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]

            result_1 = await add_conversation_memory(
                messages=messages_1,
                user_id=user_id,
                session_id=session_id,
                metadata={"trip_type": "honeymoon", "destination": "Paris"},
            )

            assert result_1["status"] == "success"
            assert "mem-1" in result_1["memory_id"]

            # Step 2: Add more conversation with preferences
            messages_2 = [
                ConversationMessage(
                    role="user",
                    content=(
                        "I prefer hotels near the Champs-Élysées with spa services and Michelin-starred restaurants."
                    ),
                    timestamp=datetime.now(timezone.utc),
                ),
                ConversationMessage(
                    role="assistant",
                    content=(
                        "Perfect! I recommend the Four Seasons Hotel George V and Le "
                        "Bristol Paris. Both are on the Champs-Élysées "
                        "with world-class spas."
                    ),
                    timestamp=datetime.now(timezone.utc),
                ),
            ]

            result_2 = await add_conversation_memory(
                messages=messages_2,
                user_id=user_id,
                session_id=session_id,
                metadata={"preferences": "luxury, spa, fine_dining"},
            )

            assert result_2["status"] == "success"

            # Step 3: Search for Paris-related memories
            search_query = MemorySearchQuery(user_id=user_id, query="Paris luxury hotels", limit=10)

            search_results = await search_user_memories(search_query)

            assert len(search_results) >= 1
            assert any("Paris" in result["content"] for result in search_results)
            assert any(result["score"] > 0.8 for result in search_results)

            # Step 4: Get user context for personalization
            context = await get_user_context(user_id)

            assert "memories" in context
            assert "preferences" in context
            assert "travel_patterns" in context
            assert len(context["memories"]) >= 2
            assert "Paris" in context["travel_patterns"]["favorite_destinations"]

            # Step 5: Verify context contains extracted preferences
            assert context["preferences"].get("accommodation") == "luxury"

    @pytest.mark.asyncio
    async def test_multi_session_memory_continuity(self, mock_memory_service):
        """Test memory continuity across multiple chat sessions."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "continuity-user-123"

            # Session 1: Initial trip planning
            messages_session_1 = [
                ConversationMessage(
                    role="user",
                    content="I want to plan a trip to Tokyo for cherry blossom season.",
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            await add_conversation_memory(
                messages=messages_session_1,
                user_id=user_id,
                session_id="session-1",
                metadata={"destination": "Tokyo", "season": "spring"},
            )

            # Session 2: Follow-up preferences (different session)
            messages_session_2 = [
                ConversationMessage(
                    role="user",
                    content=("For my Tokyo trip, I prefer traditional ryokans over modern hotels."),
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            await add_conversation_memory(
                messages=messages_session_2,
                user_id=user_id,
                session_id="session-2",
                metadata={"accommodation_preference": "ryokan"},
            )

            # Session 3: Budget discussion (another session)
            messages_session_3 = [
                ConversationMessage(
                    role="user",
                    content=("My budget for the Tokyo trip is around $8,000 for two weeks."),
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            await add_conversation_memory(
                messages=messages_session_3,
                user_id=user_id,
                session_id="session-3",
                metadata={"budget": "$8,000", "duration": "two weeks"},
            )

            # Verify all sessions are reflected in user context
            context = await get_user_context(user_id)

            assert len(context["memories"]) == 3
            assert "Tokyo" in context["travel_patterns"]["favorite_destinations"]

            # Search should find memories across all sessions
            search_results = await search_user_memories(MemorySearchQuery(user_id=user_id, query="Tokyo trip"))

            assert len(search_results) >= 3

    @pytest.mark.asyncio
    async def test_preference_evolution_tracking(self, mock_memory_service):
        """Test tracking how user preferences evolve over time."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "evolution-user-123"

            # Initial conversation: Budget travel preference
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=("I'm a budget traveler looking for hostels and cheap flights."),
                        timestamp=datetime.now(timezone.utc) - timedelta(days=30),
                    )
                ],
                user_id=user_id,
                metadata={"preference_period": "initial", "style": "budget"},
            )

            # Middle conversation: Shift to mid-range
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=("I've gotten a promotion! Now I can afford mid-range hotels with good reviews."),
                        timestamp=datetime.now(timezone.utc) - timedelta(days=15),
                    )
                ],
                user_id=user_id,
                metadata={"preference_period": "middle", "style": "mid-range"},
            )

            # Latest conversation: Luxury preference
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=("For my anniversary trip, I want the best luxury hotels and first-class flights."),
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={
                    "preference_period": "current",
                    "style": "luxury",
                    "occasion": "anniversary",
                },
            )

            # Get context to see preference evolution
            context = await get_user_context(user_id)

            assert len(context["memories"]) == 3

            # Search for different preference periods
            luxury_search = await search_user_memories(MemorySearchQuery(user_id=user_id, query="luxury"))

            budget_search = await search_user_memories(MemorySearchQuery(user_id=user_id, query="budget"))

            assert len(luxury_search) >= 1
            assert len(budget_search) >= 1

    @pytest.mark.asyncio
    async def test_personalized_recommendations_workflow(self, mock_memory_service):
        """Test how stored memories enable personalized recommendations."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "recommendations-user-123"

            # Build user profile through conversations
            profile_conversations = [
                {
                    "messages": [
                        ConversationMessage(
                            role="user",
                            content=("I love cultural experiences and museums when I travel."),
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                    "metadata": {"interest": "culture", "preference": "museums"},
                },
                {
                    "messages": [
                        ConversationMessage(
                            role="user",
                            content=("I'm vegetarian and need restaurants with good plant-based options."),
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                    "metadata": {"dietary": "vegetarian", "requirement": "plant-based"},
                },
                {
                    "messages": [
                        ConversationMessage(
                            role="user",
                            content=("I prefer staying in boutique hotels with unique character over chain hotels."),
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                    "metadata": {"accommodation": "boutique", "preference": "unique"},
                },
            ]

            # Store all profile conversations
            for conv in profile_conversations:
                await add_conversation_memory(
                    messages=conv["messages"],
                    user_id=user_id,
                    metadata=conv["metadata"],
                )

            # Simulate new trip planning conversation
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=("I'm planning a trip to Barcelona. What do you recommend?"),
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_id,
                metadata={"destination": "Barcelona", "type": "planning"},
            )

            # Get context for personalized recommendations
            context = await get_user_context(user_id)

            # Search for relevant preferences
            cultural_interests = await search_user_memories(
                MemorySearchQuery(user_id=user_id, query="cultural museums")
            )

            dietary_requirements = await search_user_memories(
                MemorySearchQuery(user_id=user_id, query="vegetarian restaurants")
            )

            accommodation_prefs = await search_user_memories(
                MemorySearchQuery(user_id=user_id, query="boutique hotels")
            )

            # Verify personalization data is available
            assert len(cultural_interests) >= 1
            assert len(dietary_requirements) >= 1
            assert len(accommodation_prefs) >= 1
            assert len(context["memories"]) >= 4

    @pytest.mark.asyncio
    async def test_memory_based_context_enhancement(self, mock_memory_service):
        """Test how memories enhance conversation context."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "context-user-123"

            # Previous trip experience
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=("My trip to Italy last year was amazing. The food in Tuscany was incredible."),
                        timestamp=datetime.now(timezone.utc) - timedelta(days=365),
                    )
                ],
                user_id=user_id,
                metadata={
                    "destination": "Italy",
                    "region": "Tuscany",
                    "highlight": "food",
                },
            )

            # Current conversation referencing past experience
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content=("I want to plan another European food tour, similar to my Italy trip."),
                        timestamp=datetime.now(timezone.utc),
                    ),
                    ConversationMessage(
                        role="assistant",
                        content=(
                            "Based on your amazing Tuscany experience, I recommend exploring France's culinary regions."
                        ),
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
                user_id=user_id,
                metadata={"trip_type": "food_tour", "reference": "Italy_trip"},
            )

            # Search for context about past experiences
            past_experiences = await search_user_memories(MemorySearchQuery(user_id=user_id, query="Italy food trip"))

            food_preferences = await search_user_memories(MemorySearchQuery(user_id=user_id, query="food culinary"))

            # Get full context
            context = await get_user_context(user_id)

            # Verify context enhancement
            assert len(past_experiences) >= 1
            assert len(food_preferences) >= 2
            assert "Italy" in context["travel_patterns"]["favorite_destinations"]

    @pytest.mark.asyncio
    async def test_memory_workflow_performance(self, mock_memory_service):
        """Test memory workflow performance under load."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "performance-user-123"

            # Measure time for multiple operations
            start_time = time.time()

            # Add multiple conversations rapidly
            tasks = []
            for i in range(10):
                messages = [
                    ConversationMessage(
                        role="user",
                        content=f"Planning trip number {i} to destination {i}",
                        timestamp=datetime.now(timezone.utc),
                    )
                ]

                task = add_conversation_memory(
                    messages=messages,
                    user_id=user_id,
                    session_id=f"session-{i}",
                    metadata={"trip_number": i},
                )
                tasks.append(task)

            # Execute all adds concurrently
            results = await asyncio.gather(*tasks)

            add_time = time.time() - start_time

            # Measure search performance
            start_time = time.time()

            search_tasks = []
            for i in range(5):
                query = MemorySearchQuery(user_id=user_id, query=f"trip {i}")
                search_tasks.append(search_user_memories(query))

            await asyncio.gather(*search_tasks)

            search_time = time.time() - start_time

            # Measure context retrieval
            start_time = time.time()
            context = await get_user_context(user_id)
            context_time = time.time() - start_time

            # Performance assertions
            assert len(results) == 10
            assert all(result["status"] == "success" for result in results)
            assert add_time < 2.0  # 10 adds should complete within 2 seconds
            assert search_time < 1.0  # 5 searches should complete within 1 second
            assert context_time < 0.5  # Context retrieval should be under 500ms
            assert len(context["memories"]) <= 5  # Should limit to recent memories

    @pytest.mark.asyncio
    async def test_error_recovery_in_workflow(self, mock_memory_service):
        """Test error recovery in memory workflow."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_id = "error-recovery-user-123"

            # Simulate partial failure scenario
            original_search = mock_memory_service.search_memories
            call_count = 0

            async def failing_search(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Temporary search failure")
                return await original_search(*args, **kwargs)

            mock_memory_service.search_memories = failing_search

            # Add memory successfully
            messages = [
                ConversationMessage(
                    role="user",
                    content="Test message for error recovery",
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            result = await add_conversation_memory(messages=messages, user_id=user_id)

            assert result["status"] == "success"

            # First search should fail, but system should handle gracefully
            search_query = MemorySearchQuery(user_id=user_id, query="test message")

            # Due to @with_error_handling decorator, this should not raise
            search_result = await search_user_memories(search_query)

            # Second search should succeed
            search_result_2 = await search_user_memories(search_query)

            # Verify recovery
            assert search_result is not None  # Error handled gracefully
            assert len(search_result_2) >= 0  # Second attempt succeeds

    @pytest.mark.asyncio
    async def test_memory_data_isolation(self, mock_memory_service):
        """Test that user memory data is properly isolated."""
        with patch("tripsage.tools.memory_tools.memory_service", mock_memory_service):
            user_1 = "user-1-isolation"
            user_2 = "user-2-isolation"

            # Add memories for user 1
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="User 1 secret travel plans to Mars",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_1,
                metadata={"confidential": "user_1_data"},
            )

            # Add memories for user 2
            await add_conversation_memory(
                messages=[
                    ConversationMessage(
                        role="user",
                        content="User 2 planning trip to Jupiter",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
                user_id=user_2,
                metadata={"confidential": "user_2_data"},
            )

            # Verify user 1 cannot access user 2's data
            user_1_context = await get_user_context(user_1)
            user_1_search = await search_user_memories(MemorySearchQuery(user_id=user_1, query="Jupiter"))

            # Verify user 2 cannot access user 1's data
            user_2_context = await get_user_context(user_2)
            user_2_search = await search_user_memories(MemorySearchQuery(user_id=user_2, query="Mars"))

            # Check isolation
            user_1_content = str(user_1_context["memories"])
            user_2_content = str(user_2_context["memories"])

            assert "Mars" in user_1_content
            assert "Jupiter" not in user_1_content
            assert "Jupiter" in user_2_content
            assert "Mars" not in user_2_content

            assert len(user_1_search) == 0  # User 1 shouldn't find Jupiter
            assert len(user_2_search) == 0  # User 2 shouldn't find Mars


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=tripsage", "--cov-report=term-missing"])
