#!/usr/bin/env python3
"""
Test the concept of CachedWebSearchTool without direct imports.

This test validates that the caching concept has been properly
implemented by checking the code structure.
"""


def test_cached_websearch_implementation():
    """Test that CachedWebSearchTool is properly implemented."""
    # Read the web_tools.py file
    with open("tripsage/tools/web_tools.py", "r") as f:
        content = f.read()

    # Check that CachedWebSearchTool is defined
    assert "class CachedWebSearchTool" in content
    assert "WebSearchTool" in content, "Should inherit from WebSearchTool"

    # Check initialization
    assert "def __init__" in content
    assert "cache" in content
    assert "WebOperationsCache" in content

    # Check caching logic
    assert "async def _run" in content
    assert "cache_key" in content
    assert "skip_cache" in content
    assert "await self.cache.get" in content
    assert "await self.cache.set" in content

    # Check proper parent call
    assert "super()._run" in content or "await super()._run" in content

    print("✓ CachedWebSearchTool implementation looks correct")


def test_travel_planning_agent_integration():
    """Test that TravelPlanningAgent uses CachedWebSearchTool."""
    # Read the travel_planning_agent.py file
    with open("src/agents/travel_planning_agent.py", "r") as f:
        content = f.read()

    # Check imports
    assert "from tripsage.tools.web_tools import CachedWebSearchTool" in content

    # Check usage
    assert "CachedWebSearchTool()" in content
    assert "self.web_search_tool" in content

    # Should not have domain restrictions anymore
    assert "allowed_domains" not in content
    assert "blocked_domains" not in content
    assert "AllowedDomains" not in content

    print("✓ TravelPlanningAgent integration looks correct")


def test_destination_research_agent_integration():
    """Test that DestinationResearchAgent uses CachedWebSearchTool."""
    # Read the destination_research_agent.py file
    with open("src/agents/destination_research_agent.py", "r") as f:
        content = f.read()

    # Check imports
    assert "from tripsage.tools.web_tools import CachedWebSearchTool" in content

    # Check usage
    assert "CachedWebSearchTool()" in content
    assert "self.web_search_tool" in content

    # Should not have domain restrictions anymore
    assert "allowed_domains = [" not in content
    assert "blocked_domains" not in content

    print("✓ DestinationResearchAgent integration looks correct")


def test_no_allowed_domains_in_agents():
    """Test that agents don't use AllowedDomains anymore."""
    # Check travel_agent.py
    with open("src/agents/travel_agent.py", "r") as f:
        content = f.read()

    # Should not import or use AllowedDomains
    assert "AllowedDomains" not in content
    assert "WebSearchTool()" in content  # Should use bare WebSearchTool

    print("✓ Travel Agent doesn't use AllowedDomains")


if __name__ == "__main__":
    test_cached_websearch_implementation()
    test_travel_planning_agent_integration()
    test_destination_research_agent_integration()
    test_no_allowed_domains_in_agents()
    print("\n✅ All tests passed!")
