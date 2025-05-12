"""
Database module for the TripSage API.

This module provides database connection and repository instances for the TripSage API.
"""

from fastapi import Depends
from supabase import Client

from src.db.client import get_supabase_client
from src.db.initialize import close_database_connection, initialize_database
from src.db.repositories.flight import FlightRepository
from src.db.repositories.trip import TripRepository
from src.db.repositories.user import UserRepository
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


# Repository factories
def get_user_repository() -> UserRepository:
    """Get the user repository."""
    return UserRepository()


def get_trip_repository() -> TripRepository:
    """Get the trip repository."""
    return TripRepository()


def get_flight_repository() -> FlightRepository:
    """Get the flight repository."""
    return FlightRepository()


# Dependency for database access in API routes
async def get_db() -> Client:
    """
    Get the database client as a FastAPI dependency.

    Returns:
        The Supabase client.
    """
    client = get_supabase_client()
    return client


# Dependency for repositories in API routes
def get_repository(repo_factory):
    """
    Create a dependency for a specific repository.

    Args:
        repo_factory: Factory function that creates the repository.

    Returns:
        A dependency function that returns the repository.
    """

    def _get_repo():
        return repo_factory()

    return Depends(_get_repo)


# Initialize database connection
async def startup_db_client():
    """Initialize the database client on application startup."""
    logger.info("Initializing database client")
    # Run database initialization without migrations (migrations should be run manually)
    success = await initialize_database(run_migrations_on_startup=False)
    if not success:
        logger.error("Failed to initialize database client")
        raise RuntimeError("Failed to initialize database client")
    logger.info("Database client initialized successfully")


# Close database connection
async def shutdown_db_client():
    """Close the database client on application shutdown."""
    logger.info("Closing database client")
    await close_database_connection()
    logger.info("Database client closed")
