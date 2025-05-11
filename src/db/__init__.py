"""
TripSage Database Module.

This module provides access to the Supabase database for the TripSage application.
"""

# Expose key components at the module level
from src.db.client import create_supabase_client, get_supabase_client, reset_client
from src.db.config import DatabaseConfig, config
from src.db.initialize import close_database_connection, initialize_database
from src.db.migrations import run_migrations

# Import models
from src.db.models import (
    BaseDBModel,
    BookingStatus,
    Flight,
    Trip,
    TripStatus,
    TripType,
    User,
)

# Import repositories
from src.db.repositories import (
    BaseRepository,
    FlightRepository,
    TripRepository,
    UserRepository,
)

__all__ = [
    # Client and configuration
    "get_supabase_client",
    "create_supabase_client",
    "reset_client",
    "DatabaseConfig",
    "config",
    # Initialization and management
    "initialize_database",
    "close_database_connection",
    "run_migrations",
    # Models
    "BaseDBModel",
    "User",
    "Trip",
    "TripStatus",
    "TripType",
    "Flight",
    "BookingStatus",
    # Repositories
    "BaseRepository",
    "UserRepository",
    "TripRepository",
    "FlightRepository",
]
