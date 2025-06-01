"""
Tests for memory tools with dependency injection.

This module tests the refactored memory tools that use ServiceRegistry
for dependency injection instead of global state.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.tools.memory_tools import (
    add_conversation_memory,
    search_user_memories,
    get_user_context,
    memory_health_check
)
from tripsage.tools.models import (
    ConversationMessage,
    MemorySearchQuery
)


class TestMemoryTools:
    """Tests for memory tools with dependency injection."""

    @pytest.mark.asyncio
    async def test_add_conversation_memory_success(self):
        """Test adding conversation memory successfully."""
        mock_memory_service = MagicMock()
        mock_memory_service.add_conversation_memory = AsyncMock(return_value={
            "memory_id": "mem-123",
            "results": [{"content": "Test memory"}],
            "usage": {"total_tokens": 100}
        })
        
        registry = ServiceRegistry(memory_service=mock_memory_service)
        
        messages = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi there!")
        ]
        
        result = await add_conversation_memory(
            messages=messages,
            user_id="user123",
            service_registry=registry
        )
        
        assert result["status"] == "success"
        assert result["memory_id"] == "mem-123"

    @pytest.mark.asyncio
    async def test_memory_health_check_healthy(self):
        """Test memory service health check when healthy."""
        mock_memory_service = MagicMock()
        mock_memory_service.health_check = AsyncMock(return_value=True)
        
        registry = ServiceRegistry(memory_service=mock_memory_service)
        
        result = await memory_health_check(registry)
        
        assert result["status"] == "healthy"
        assert result["service"] == "Mem0 Memory Service"