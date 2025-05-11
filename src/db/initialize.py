"""
Database initialization module for TripSage.

This module provides functionality to initialize the database connection
and ensure the database is properly set up.
"""

import asyncio
import logging
from typing import Optional

from src.db.client import get_supabase_client, reset_client
from src.db.migrations import run_migrations
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


async def initialize_database(
    run_migrations_on_startup: bool = False,
    verify_connection: bool = True,
) -> bool:
    """
    Initialize the database connection and ensure the database is properly set up.

    Args:
        run_migrations_on_startup: Whether to run migrations on startup.
        verify_connection: Whether to verify the database connection.

    Returns:
        True if the database was successfully initialized, False otherwise.
    """
    logger.info("Initializing database connection")

    try:
        # Initialize and test the Supabase client
        if verify_connection:
            client = get_supabase_client()
            response = client.table("users").select("id").limit(1).execute()
            logger.info("Database connection verified")

        # Run migrations if requested
        if run_migrations_on_startup:
            logger.info("Running database migrations")
            succeeded, failed = run_migrations()
            if failed > 0:
                logger.warning(
                    f"Some migrations failed: {failed} failed, {succeeded} succeeded"
                )
            else:
                logger.info(
                    f"Database migrations completed successfully: {succeeded} applied"
                )

        logger.info("Database initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False


async def close_database_connection() -> None:
    """
    Close the database connection.
    """
    logger.info("Closing database connection")
    # Reset the client to ensure it's closed
    reset_client()


def get_model_mapping() -> dict:
    """
    Get a mapping of table names to model classes.

    Returns:
        A dictionary mapping table names to model classes.
    """
    from src.db.models.flight import Flight
    from src.db.models.trip import Trip
    from src.db.models.user import User

    # Import other models here

    return {
        "users": User,
        "trips": Trip,
        "flights": Flight,
        # Add other models here
    }


def get_repository_mapping() -> dict:
    """
    Get a mapping of model classes to repository classes.

    Returns:
        A dictionary mapping model classes to repository classes.
    """
    from src.db.models.flight import Flight
    from src.db.models.trip import Trip
    from src.db.models.user import User
    from src.db.repositories.flight import FlightRepository
    from src.db.repositories.trip import TripRepository
    from src.db.repositories.user import UserRepository

    # Import other repositories here

    return {
        User: UserRepository,
        Trip: TripRepository,
        Flight: FlightRepository,
        # Add other repositories here
    }


if __name__ == "__main__":
    """
    Run database initialization when the script is executed directly.

    Example usage:
        python -m src.db.initialize
    """
    import argparse

    parser = argparse.ArgumentParser(description="Initialize the database")
    parser.add_argument(
        "--run-migrations", action="store_true", help="Run migrations on startup"
    )
    args = parser.parse_args()

    result = asyncio.run(
        initialize_database(run_migrations_on_startup=args.run_migrations)
    )

    if result:
        print("Database initialization completed successfully")
    else:
        print("Database initialization failed")
        exit(1)
