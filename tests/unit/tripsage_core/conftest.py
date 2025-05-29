"""Pytest configuration for TripSage Core tests."""

import sys
from pathlib import Path

# Add the project root to sys.path to ensure imports work
project_root = Path(__file__).parents[3]  # Go up to project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the core module to ensure it's available
import tripsage_core  # noqa: E402, F401
