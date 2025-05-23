"""
Agent-specific test configuration.

This module provides fixtures specific to agent testing,
isolating them from the global conftest dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_all_dependencies():
    """Mock all problematic dependencies for agent tests."""
    # Create comprehensive mocks
    mock_settings = MagicMock()
    mock_settings.agent.model_name = "gpt-4"
    mock_settings.agent.temperature = 0.7
    
    mock_cache = MagicMock()
    mock_redis = MagicMock()
    mock_agents = MagicMock()
    
    # Apply all patches
    with (
        patch("tripsage.config.app_settings.settings", mock_settings),
        patch("tripsage.utils.settings.settings", mock_settings),
        patch("tripsage.utils.cache.redis", mock_redis),
        patch("tripsage.utils.cache.web_cache", mock_cache),
        patch("agents.Agent", mock_agents),
        patch("agents.Runner", mock_agents),
        patch("redis.asyncio.from_url", return_value=mock_redis),
        patch("redis.from_url", return_value=mock_redis),
    ):
        yield {
            "settings": mock_settings,
            "cache": mock_cache,
            "redis": mock_redis,
            "agents": mock_agents,
        }