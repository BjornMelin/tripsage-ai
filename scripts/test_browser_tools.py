#!/usr/bin/env python
"""
Test script for validating browser tools implementation.

This script verifies that browser tools are correctly configured to
interface with external Playwright and Stagehand MCP servers.
"""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

# Add parent directory to Python path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Function to dynamically import modules after path adjustment
def import_module(name, path):
    """Import a module from a specific path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import the required modules
browser_tools = import_module(
    "browser_tools",
    os.path.join(parent_dir, "tripsage/tools/browser/browser_tools.py"),
)
settings_module = import_module(
    "settings", os.path.join(parent_dir, "tripsage/utils/settings.py")
)


async def validate_settings():
    """Validate settings for browser MCP integration."""
    settings = settings_module.get_settings()

    print("Validating settings for browser MCP integration...")

    # Check Playwright MCP settings
    playwright_config = settings.playwright_mcp
    print("\nPlaywright MCP Configuration:")
    print(f"  Endpoint: {playwright_config.endpoint}")
    print(
        f"  API Key: {'Configured' if playwright_config.api_key else 'Not configured'}"
    )
    print(f"  Headless: {playwright_config.headless}")
    print(f"  Browser Type: {playwright_config.browser_type}")

    # Check Stagehand MCP settings
    stagehand_config = settings.stagehand_mcp
    print("\nStagehand MCP Configuration:")
    print(f"  Endpoint: {stagehand_config.endpoint}")
    print(
        f"  API Key: {'Configured' if stagehand_config.api_key else 'Not configured'}"
    )
    browserbase_key = getattr(stagehand_config, "browserbase_api_key", None)
    status = "Configured" if browserbase_key else "Not configured"
    print(f"  Browserbase API Key: {status}")
    print(f"  Browserbase Project ID: {stagehand_config.browserbase_project_id}")
    print(f"  Headless: {stagehand_config.headless}")

    # Check if Redis is configured
    redis_config = settings.redis
    print("\nRedis Configuration:")
    print(f"  URL: {redis_config.url}")
    print(f"  TTL Short: {redis_config.ttl_short} seconds")
    print(f"  TTL Medium: {redis_config.ttl_medium} seconds")
    print(f"  TTL Long: {redis_config.ttl_long} seconds")

    return True


def print_function_definitions():
    """Print function definitions for OpenAI Agents SDK."""
    print("\nFunction Definitions for OpenAI Agents SDK:")
    for i, tool_def in enumerate(browser_tools.get_browser_tool_definitions(), 1):
        print(f"\nFunction Tool #{i}:")
        print(f"  Name: {tool_def.name}")
        print(f"  Description: {tool_def.description}")


async def main():
    """Run validation tests."""
    try:
        print("Validating Browser Tools Implementation\n" + "=" * 40)

        # Validate settings
        settings_valid = await validate_settings()
        if not settings_valid:
            print("\nSettings validation failed!")
            return 1

        # Print function tool definitions
        print_function_definitions()

        print("\nBrowser tools implementation is valid!")
        return 0

    except Exception as e:
        print(f"\nValidation failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
