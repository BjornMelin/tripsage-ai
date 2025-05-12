"""
Database models for TripSage.

This module provides Pydantic models for the TripSage database schema.
"""

from src.db.models.base import BaseDBModel
from src.db.models.flight import BookingStatus, Flight
from src.db.models.trip import Trip, TripStatus, TripType
from src.db.models.user import User

__all__ = [
    "BaseDBModel",
    "User",
    "Trip",
    "TripStatus",
    "TripType",
    "Flight",
    "BookingStatus",
]
