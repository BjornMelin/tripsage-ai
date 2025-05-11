"""
Pytest configuration for TripSage tests.
"""

import os
import sys

import pytest

# Add the src directory to the path so tests can import modules directly from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment variables
os.environ.setdefault("AIRBNB_MCP_ENDPOINT", "http://localhost:3000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
