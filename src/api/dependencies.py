"""
Dependencies module for the TripSage API.

This module provides common dependencies for the FastAPI routes.
"""

from fastapi import Depends

from src.api.auth import User, get_current_user
from src.api.database import (
    get_flight_repository,
    get_repository,
    get_trip_repository,
    get_user_repository,
)
from src.db.repositories.flight import FlightRepository
from src.db.repositories.trip import TripRepository
from src.db.repositories.user import UserRepository


# Create module-level dependencies
def get_current_active_user():
    """Get the current active user dependency."""
    from src.api.auth import get_current_active_user as get_user

    return get_user


# Repository dependencies
def get_user_repository_dependency():
    """Get the user repository dependency."""
    return get_repository(get_user_repository)


def get_trip_repository_dependency():
    """Get the trip repository dependency."""
    return get_repository(get_trip_repository)


def get_flight_repository_dependency():
    """Get the flight repository dependency."""
    return get_repository(get_flight_repository)


# Helpers for dependency injection in routes
current_active_user = Depends(get_current_active_user())
user_repository = Depends(get_user_repository_dependency())
trip_repository = Depends(get_trip_repository_dependency())
flight_repository = Depends(get_flight_repository_dependency())
