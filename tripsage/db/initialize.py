"""
Database initialization module for TripSage.

This module provides functionality to initialize SQL databases using
direct SDK connections for optimal performance. Memory management is now
handled by Mem0 direct SDK integration.

Note: Neo4j has been replaced with Mem0 for memory management in the MVP
architecture.
"""

import asyncio
from typing import Any, Dict

from supabase import Client, create_client

from tripsage.config.app_settings import settings
from tripsage.db.migrations import run_migrations
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)


def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    return create_client(
        settings.database.supabase_url,
        settings.database.supabase_anon_key.get_secret_value(),
    )


async def initialize_databases(
    run_migrations_on_startup: bool = False,
    verify_connections: bool = True,
) -> bool:
    """
    Initialize database connections and ensure databases are properly set up.

    Args:
        run_migrations_on_startup: Whether to run migrations on startup.
        verify_connections: Whether to verify database connections.

    Returns:
        True if databases were successfully initialized, False otherwise.
    """
    logger.info("Initializing database connections")

    try:
        # Verify SQL connection
        if verify_connections:
            logger.info("Verifying SQL database connection...")
            supabase = get_supabase_client()

            # Test connection with a simple query
            result = supabase.rpc("version").execute()
            if result.data:
                logger.info(
                    f"SQL database connection verified: PostgreSQL {result.data}"
                )
            else:
                logger.error("SQL connection verification failed")
                return False

        # Run migrations if requested
        if run_migrations_on_startup:
            logger.info("Running database migrations...")

            # Run SQL migrations
            sql_succeeded, sql_failed = await run_migrations()
            logger.info(
                f"SQL migrations: {sql_succeeded} succeeded, {sql_failed} failed"
            )

            if sql_failed > 0:
                logger.warning("Some migrations failed")
                return False

        logger.info("Database initialization completed successfully")
        logger.info("Memory management is handled by Mem0 direct SDK integration")
        return True

    except Exception as e:
        logger.error(f"Error initializing databases: {e}")
        return False


async def verify_database_schema() -> Dict[str, Any]:
    """
    Verify that the database schema is correctly set up.

    Returns:
        Dictionary with verification results for SQL database.
    """
    results = {"sql": {}}

    try:
        # Check SQL tables
        supabase = get_supabase_client()

        # Get list of tables
        table_query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('users', 'trips', 'migrations');
        """

        result = supabase.rpc("execute_sql", {"query": table_query}).execute()

        if result.data:
            existing_tables = [row["tablename"] for row in result.data]
            results["sql"]["tables"] = existing_tables
            results["sql"]["missing_tables"] = [
                t for t in ["users", "trips", "migrations"] if t not in existing_tables
            ]
            results["sql"]["initialized"] = len(existing_tables) > 0

        logger.info(f"Database schema verification completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Error verifying database schema: {e}")
        return {"sql": {"error": str(e)}}


async def create_sample_data() -> bool:
    """
    Create sample data for development and testing.

    Returns:
        True if sample data was created successfully, False otherwise.
    """
    logger.info("Creating sample data...")

    try:
        supabase = get_supabase_client()

        # Create sample users
        sample_users = [
            {
                "id": "sample-user-1",
                "email": "user1@example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "metadata": {
                    "name": "Sample User 1",
                    "preferences": {"currency": "USD"},
                },
            },
            {
                "id": "sample-user-2",
                "email": "user2@example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "metadata": {
                    "name": "Sample User 2",
                    "preferences": {"currency": "EUR"},
                },
            },
        ]

        for user in sample_users:
            result = supabase.table("users").upsert(user).execute()
            if result.data:
                logger.info(f"Created sample user: {user['email']}")

        # Create sample trips
        sample_trips = [
            {
                "id": "sample-trip-1",
                "user_id": "sample-user-1",
                "title": "Trip to Paris",
                "description": "A wonderful trip to the City of Light",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "status": "planned",
                "metadata": {"destination": "Paris, France", "budget": 2000},
            },
            {
                "id": "sample-trip-2",
                "user_id": "sample-user-2",
                "title": "Adventure in Tokyo",
                "description": "Exploring the vibrant culture of Japan",
                "start_date": "2024-09-15",
                "end_date": "2024-09-25",
                "status": "planned",
                "metadata": {"destination": "Tokyo, Japan", "budget": 3000},
            },
        ]

        for trip in sample_trips:
            result = supabase.table("trips").upsert(trip).execute()
            if result.data:
                logger.info(f"Created sample trip: {trip['title']}")

        logger.info("Sample data creation completed")
        logger.info("Note: Memory/graph data is now handled by Mem0 service")
        return True

    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        return False


if __name__ == "__main__":
    import argparse

    async def main():
        parser = argparse.ArgumentParser(description="Initialize TripSage databases")
        parser.add_argument(
            "--verify", action="store_true", help="Verify database connections"
        )
        parser.add_argument(
            "--migrate", action="store_true", help="Run database migrations"
        )
        parser.add_argument(
            "--sample-data", action="store_true", help="Create sample data"
        )

        args = parser.parse_args()

        if args.verify or args.migrate:
            success = await initialize_databases(
                run_migrations_on_startup=args.migrate,
                verify_connections=args.verify,
            )
            if not success:
                logger.error("Database initialization failed")
                return

        if args.sample_data:
            await create_sample_data()

        # Verify schema
        await verify_database_schema()

    asyncio.run(main())
