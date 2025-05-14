"""
Tests for verifying the import statements in the TripSage tools.

These tests ensure that all tools are using the 'agents' module for importing
the OpenAI Agents SDK components consistently.
"""

import importlib.util
import os
import sys


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
accommodations_tools_path = os.path.join(
    base_dir, "tripsage/tools/accommodations_tools.py"
)
time_tools_path = os.path.join(base_dir, "tripsage/tools/time_tools.py")
memory_tools_path = os.path.join(base_dir, "tripsage/tools/memory_tools.py")
webcrawl_tools_path = os.path.join(base_dir, "tripsage/tools/webcrawl_tools.py")
base_path = os.path.join(base_dir, "tripsage/agents/base.py")

# Import the module source code as text for inspection
with open(calendar_tools_path, "r") as f:
    calendar_tools_source = f.read()

with open(googlemaps_tools_path, "r") as f:
    googlemaps_tools_source = f.read()

with open(weather_tools_path, "r") as f:
    weather_tools_source = f.read()

with open(accommodations_tools_path, "r") as f:
    accommodations_tools_source = f.read()

with open(base_path, "r") as f:
    base_source = f.read()

# Import tool modules that need to be tested for imports
for path in [time_tools_path, memory_tools_path, webcrawl_tools_path]:
    if os.path.exists(path):
        with open(path, "r") as f:
            globals()[os.path.basename(path).replace(".py", "_source")] = f.read()


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


def test_accommodations_tools_import():
    """Test that accommodations_tools is using the agents import."""
    assert "from agents import function_tool" in accommodations_tools_source
    assert (
        "from openai_agents_sdk import function_tool" not in accommodations_tools_source
    )


def test_time_tools_import():
    """Test that time_tools is using the agents import."""
    time_tools_var = "time_tools_source"
    if time_tools_var in globals():
        assert "from agents import function_tool" in globals()[time_tools_var]
        assert (
            "from openai_agents_sdk import function_tool"
            not in globals()[time_tools_var]
        )


def test_memory_tools_import():
    """Test that memory_tools is using the agents import."""
    memory_tools_var = "memory_tools_source"
    if memory_tools_var in globals():
        assert "from agents import function_tool" in globals()[memory_tools_var]
        assert (
            "from openai_agents_sdk import function_tool"
            not in globals()[memory_tools_var]
        )


def test_webcrawl_tools_import():
    """Test that webcrawl_tools is using the agents import."""
    webcrawl_tools_var = "webcrawl_tools_source"
    if webcrawl_tools_var in globals():
        assert "from agents import function_tool" in globals()[webcrawl_tools_var]
        assert (
            "from openai_agents_sdk import function_tool"
            not in globals()[webcrawl_tools_var]
        )


def test_base_agent_import():
    """Test that BaseAgent is correctly importing from agents module."""
    # Check that the base agent uses the right imports
    assert "from agents import Agent, function_tool" in base_source
    assert "from agents import Runner" in base_source

    # Echo method should be decorated in the source code
    assert "@function_tool" in base_source
