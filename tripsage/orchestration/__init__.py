"""
LangGraph orchestration package for TripSage AI.

This package contains the simplified LangGraph-based agent orchestration system
using modern @tool patterns and create_react_agent for maintainability.
"""

from .graph import SimpleTripSageOrchestrator, get_orchestrator
from .state import TravelPlanningState

# Keep backwards compatibility but prefer the simple orchestrator
TripSageOrchestrator = SimpleTripSageOrchestrator

__all__ = [
    "SimpleTripSageOrchestrator",
    "TripSageOrchestrator",  # Backwards compatibility
    "get_orchestrator",
    "TravelPlanningState",
]
