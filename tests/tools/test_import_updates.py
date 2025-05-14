"""
Tests for verifying the import statements in the TripSage tools.

These tests ensure that all tools are using the 'agents' module for importing
the OpenAI Agents SDK components consistently.
"""

import importlib.util
import inspect
import os
import sys

import pytest
from agents import function_tool


# Import the modules directly using importlib to avoid dependency issues
def import_module_from_path(module_name, file_path):
    """Import a module from a file path without running the full module"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    return module


# Define paths to the modules
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
calendar_tools_path = os.path.join(base_dir, "tripsage/tools/calendar_tools.py")
googlemaps_tools_path = os.path.join(base_dir, "tripsage/tools/googlemaps_tools.py")
weather_tools_path = os.path.join(base_dir, "tripsage/tools/weather_tools.py")
base_path = os.path.join(base_dir, "tripsage/agents/base.py")

# Import the module source code as text for inspection
with open(calendar_tools_path, "r") as f:
    calendar_tools_source = f.read()

with open(googlemaps_tools_path, "r") as f:
    googlemaps_tools_source = f.read()

with open(weather_tools_path, "r") as f:
    weather_tools_source = f.read()

with open(base_path, "r") as f:
    base_source = f.read()


def test_calendar_tools_import():
    """Test that calendar_tools is using the agents import."""
    assert "from agents import function_tool" in calendar_tools_source
    assert "from openai_agents_sdk import function_tool" not in calendar_tools_source


def test_googlemaps_tools_import():
    """Test that googlemaps_tools is using the agents import."""
    assert "from agents import function_tool" in googlemaps_tools_source
    assert "from openai_agents_sdk import function_tool" not in googlemaps_tools_source


def test_weather_tools_import():
    """Test that weather_tools is using the agents import."""
    assert "from agents import function_tool" in weather_tools_source
    assert "from openai_agents_sdk import function_tool" not in weather_tools_source


def test_base_agent_import():
    """Test that BaseAgent is correctly importing from agents module."""
    # Check that the base agent uses the right imports
    assert "from agents import Agent, function_tool" in base_source
    assert "from agents import Runner" in base_source

    # Echo method should be decorated in the source code
    assert "@function_tool" in base_source
