"""Database initialization for TripSage.

This module provides utilities to verify a Supabase/PostgreSQL connection,
optionally run SQL migrations, verify basic schema presence, and create simple
sample data for development. Memory functionality is handled externally by the
Mem0 SDK — no graph/neo4j code remains here (final implementation only).
"""

import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import Any


logger = logging.getLogger(__name__)


def get_supabase_client() -> Any:
    """Create and return a Supabase client.

    Returns:
        Client: Initialized Supabase client using configured URL and anon key.
    """
    # Local import to avoid hard dependency at module import time for linters.
    from supabase import create_client  # pylint: disable=import-error

    from tripsage_core.config import get_settings  # pylint: disable=import-error

    settings = get_settings()
    # type: ignore # pylint: disable=no-member
    return create_client(
        settings.database_url,
        settings.database_public_key.get_secret_value(),
    )


async def initialize_databases(
    run_migrations_on_startup: bool = False,
    verify_connections: bool = True,
) -> bool:
    """Initialize database connections and ensure databases are properly set up.

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

            # Perform a trivial RPC or table call to confirm connectivity.
            # The SDK response type is loosely typed; handle defensively.
            rpc_result: Any = supabase.rpc("version").execute()
            version_val = getattr(rpc_result, "data", None)
            if version_val is None:
                logger.exception("SQL connection verification failed: no data returned")
                return False
            logger.info("SQL database connection verified: %s", version_val)

        # Run migrations if requested
        if run_migrations_on_startup:
            logger.info("Running database migrations...")

            # Import lazily via importlib to avoid static import resolution issues.
            import importlib

            migrations_mod = importlib.import_module("tripsage.db.migrations")

            # Run SQL migrations
            sql_succeeded, sql_failed = await migrations_mod.run_migrations()
            logger.info(
                "SQL migrations: %s succeeded, %s failed", sql_succeeded, sql_failed
            )

            if sql_failed > 0:
                logger.warning("Some migrations failed")
                return False

        logger.info("Database initialization completed successfully")
        logger.info("Memory management is handled by Mem0 direct SDK integration")
        return True

    except Exception:
        logger.exception("Error initializing databases")
        return False


async def verify_database_schema() -> dict[str, Any]:
    """Verify that a minimal schema exists in the SQL database.

    Returns:
        dict[str, Any]: Verification results including discovered tables and
        any missing expected tables.
    """
    results: dict[str, Any] = {"sql": {}}

    try:
        supabase = get_supabase_client()

        table_query = (
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND tablename IN ('users','trips','migrations');"
        )

        rpc_result: Any = supabase.rpc("execute_sql", {"query": table_query}).execute()
        data = getattr(rpc_result, "data", None)

        existing_tables: list[str] = []
        if isinstance(data, Sequence):
            existing_tables = [
                str(row["tablename"])  # type: ignore[index]
                for row in data
                if isinstance(row, Mapping) and "tablename" in row
            ]

        results["sql"]["tables"] = existing_tables
        results["sql"]["missing_tables"] = [
            t for t in ["users", "trips", "migrations"] if t not in existing_tables
        ]
        results["sql"]["initialized"] = bool(existing_tables)

        logger.info("Database schema verification completed: %s", results)
        return results

    except Exception as exc:
        logger.exception("Error verifying database schema")
        return {"sql": {"error": str(exc)}}


async def create_sample_data() -> bool:
    """Create sample data for development and testing.

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
            res: Any = supabase.table("users").upsert(user).execute()
            if bool(getattr(res, "data", True)):
                logger.info("Created/updated sample user: %s", user["email"])

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
            res2: Any = supabase.table("trips").upsert(trip).execute()
            if bool(getattr(res2, "data", True)):
                logger.info("Created/updated sample trip: %s", trip["title"])

        logger.info("Sample data creation completed")
        logger.info("Note: Memory/graph data is now handled by Mem0 service")
        return True

    except Exception:
        logger.exception("Error creating sample data")
        return False


if __name__ == "__main__":
    import argparse

    async def main():
        """Initialize TripSage databases."""
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
                logger.exception("Database initialization failed")
                return

        if args.sample_data:
            await create_sample_data()

        # Verify schema
        await verify_database_schema()

    asyncio.run(main())
