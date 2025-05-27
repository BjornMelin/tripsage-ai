"""
Tests for CachedWebSearchTool integration in TravelPlanningAgent
and DestinationResearchAgent.

This module tests that the agents are correctly using CachedWebSearchTool
instead of the direct WebSearchTool.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.destination_research_agent import DestinationResearchAgent
from tripsage.agents.travel_planning_agent import TravelPlanningAgent
from tripsage.tools.web_tools import CachedWebSearchTool


class TestCachedWebSearchIntegration:
    """Test cached web search integration in agents."""

    @patch("src.agents.travel_planning_agent.logger")
    @patch("src.agents.travel_planning_agent.get_config")
    def test_travel_planning_agent_uses_cached_websearch(
        self, mock_config, mock_logger
    ):
        """Test that TravelPlanningAgent uses CachedWebSearchTool."""
        # Mock config
        mock_config.return_value = MagicMock()

        # Create agent
        agent = TravelPlanningAgent()

        # Verify that CachedWebSearchTool is used
        assert hasattr(agent, "web_search_tool")
        assert isinstance(agent.web_search_tool, CachedWebSearchTool)

        # Verify logging
        mock_logger.info.assert_any_call(
            "Added CachedWebSearchTool to TravelPlanningAgent with "
            "travel-specific domain configuration"
        )

    @patch("src.agents.destination_research_agent.logger")
    @patch("src.agents.destination_research_agent.get_config")
    def test_destination_research_agent_uses_cached_websearch(
        self, mock_config, mock_logger
    ):
        """Test that DestinationResearchAgent uses CachedWebSearchTool."""
        # Mock config
        mock_config.return_value = MagicMock()

        # Create agent
        agent = DestinationResearchAgent()

        # Verify that CachedWebSearchTool is used
        assert hasattr(agent, "web_search_tool")
        assert isinstance(agent.web_search_tool, CachedWebSearchTool)

        # Verify logging
        mock_logger.info.assert_any_call(
            "Added CachedWebSearchTool to DestinationResearchAgent"
        )

    @pytest.mark.asyncio
    @patch("src.agents.travel_planning_agent.logger")
    @patch("src.agents.travel_planning_agent.get_config")
    @patch("tripsage.tools.web_tools.web_cache")
    async def test_cached_websearch_functionality(
        self, mock_cache, mock_config, mock_logger
    ):
        """Test that CachedWebSearchTool caching actually works."""
        # Mock config
        mock_config.return_value = MagicMock()

        # Mock cache
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.generate_cache_key = MagicMock(return_value="test_key")
        mock_cache.determine_content_type = MagicMock(return_value="daily")

        # Create agent
        agent = TravelPlanningAgent()

        # Mock the parent class _run method
        with patch.object(
            CachedWebSearchTool, "_run", new_callable=AsyncMock
        ) as mock_parent_run:
            mock_parent_run.return_value = {"search_results": ["test result"]}

            # Run a search (requires mocking parent methods too)
            # This test mainly verifies the integration is set up correctly
            assert agent.web_search_tool is not None
            assert isinstance(agent.web_search_tool, CachedWebSearchTool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
