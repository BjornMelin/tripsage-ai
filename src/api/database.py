"""
Database module for the TripSage API.

This module provides database connection and utilities for the TripSage API.
"""

import logging
import os
from typing import Any, Dict, Optional, Type

from fastapi import Depends
from supabase import Client

from src.db.client import get_supabase_client
from src.db.initialize import close_database_connection, initialize_database
from src.db.models.base import BaseDBModel
from src.db.repositories.base import BaseRepository
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


# Repository factories
def get_user_repository():
    """Get the user repository."""
    from src.db.repositories.user import UserRepository

    return UserRepository()


# Dependency for database access in API routes
async def get_db():
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
