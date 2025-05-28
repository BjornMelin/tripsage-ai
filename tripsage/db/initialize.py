"""
Database initialization module for TripSage.

This module provides functionality to initialize both SQL and Neo4j databases
using direct SDK connections for optimal performance.
"""

import asyncio
from typing import Any, Dict, Optional

from neo4j import GraphDatabase
from supabase import Client, create_client

from tripsage.config.app_settings import settings
from tripsage.db.migrations import run_migrations, run_neo4j_migrations
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)


def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    return create_client(
        settings.database.supabase_url,
        settings.database.supabase_anon_key.get_secret_value()
    )


def get_neo4j_driver():
    """Get a Neo4j driver instance."""
    return GraphDatabase.driver(
        settings.neo4j.uri,
        auth=(settings.neo4j.user, settings.neo4j.password.get_secret_value()),
        max_connection_lifetime=settings.neo4j.max_connection_lifetime,
        max_connection_pool_size=settings.neo4j.max_connection_pool_size,
        connection_acquisition_timeout=settings.neo4j.connection_acquisition_timeout,
    )


async def initialize_databases(
    run_migrations_on_startup: bool = False,
    verify_connections: bool = True,
    init_neo4j_schema: bool = False,
) -> bool:
    """
    Initialize database connections and ensure databases are properly set up.

    Args:
        run_migrations_on_startup: Whether to run migrations on startup.
        verify_connections: Whether to verify database connections.
        init_neo4j_schema: Whether to initialize Neo4j schema.

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
                logger.info(f"SQL database connection verified: PostgreSQL {result.data}")
            else:
                logger.error("SQL connection verification failed")
                return False

        # Verify Neo4j connection
        if verify_connections:
            logger.info("Verifying Neo4j database connection...")
            driver = get_neo4j_driver()
            
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                if result.single()["test"] == 1:
                    logger.info("Neo4j database connection verified")
                else:
                    logger.error("Neo4j connection verification failed")
                    return False
            
            driver.close()

        # Initialize Neo4j schema if requested
        if init_neo4j_schema:
            logger.info("Initializing Neo4j schema...")
            await initialize_neo4j_schema()

        # Run migrations if requested
        if run_migrations_on_startup:
            logger.info("Running database migrations...")

            # Run SQL migrations
            sql_succeeded, sql_failed = await run_migrations()
            logger.info(
                f"SQL migrations: {sql_succeeded} succeeded, {sql_failed} failed"
            )

            # Run Neo4j migrations
            neo4j_succeeded, neo4j_failed = await run_neo4j_migrations()
            logger.info(
                f"Neo4j migrations: {neo4j_succeeded} succeeded, {neo4j_failed} failed"
            )

            if sql_failed > 0 or neo4j_failed > 0:
                logger.warning("Some migrations failed")
                return False

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error initializing databases: {e}")
        return False


async def initialize_neo4j_schema() -> bool:
    """Initialize Neo4j schema with indexes and constraints."""
    driver = get_neo4j_driver()
    
    try:
        with driver.session() as session:
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entityType)",
                "CREATE INDEX entity_created IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
                "CREATE INDEX relation_type IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.relation)",
            ]
            
            for index_query in indexes:
                session.run(index_query)
                logger.info(f"Created index: {index_query}")
            
            # Create constraints if needed
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            ]
            
            for constraint_query in constraints:
                try:
                    session.run(constraint_query)
                    logger.info(f"Created constraint: {constraint_query}")
                except Exception as e:
                    # Constraint might already exist
                    logger.debug(f"Constraint creation skipped: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error initializing Neo4j schema: {e}")
        return False
    finally:
        driver.close()


async def verify_database_schema() -> Dict[str, Any]:
    """
    Verify that the database schema is correctly set up.

    Returns:
        Dictionary with verification results for each database.
    """
    results = {"sql": {}, "neo4j": {}}

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

        # Check Neo4j entities
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            # Count nodes and relationships
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Get node labels
            labels = session.run("CALL db.labels()").values()
            
            results["neo4j"]["node_count"] = node_count
            results["neo4j"]["relationship_count"] = rel_count
            results["neo4j"]["labels"] = [label[0] for label in labels]
            results["neo4j"]["initialized"] = node_count > 0 or len(labels) > 0
        
        driver.close()
        return results

    except Exception as e:
        logger.error(f"Error verifying database schema: {e}")
        return {"error": str(e)}


async def create_sample_data() -> bool:
    """
    Create sample data in both databases for testing.

    Returns:
        True if sample data was created successfully.
    """
    try:
        # Create sample user in SQL
        supabase = get_supabase_client()
        
        user_data = {
            "email": "test@example.com",
            "username": "test_user",
            "full_name": "Test User",
            "preferences": {"theme": "light"}
        }
        
        result = supabase.table("users").upsert(user_data).execute()
        
        if not result.data:
            logger.error("Failed to create sample user")
            return False

        # Create sample destinations in Neo4j
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            destinations = [
                {
                    "name": "London",
                    "entityType": "Destination",
                    "country": "UK",
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                    "timezone": "Europe/London",
                    "currency": "GBP",
                    "description": "Historic capital of the United Kingdom",
                },
                {
                    "name": "Sydney",
                    "entityType": "Destination",
                    "country": "Australia",
                    "latitude": -33.8688,
                    "longitude": 151.2093,
                    "timezone": "Australia/Sydney",
                    "currency": "AUD",
                    "description": "Australia's largest city and economic hub",
                },
            ]
            
            for dest in destinations:
                session.run(
                    """
                    MERGE (d:Entity:Destination {name: $name})
                    SET d += $properties
                    """,
                    name=dest["name"],
                    properties=dest
                )
            
            logger.info("Sample destinations created in Neo4j")
        
        driver.close()
        logger.info("Sample data created successfully")
        return True

    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        return False


if __name__ == "__main__":
    """
    Run database initialization when the script is executed directly.
    
    Example usage:
        python -m tripsage.db.initialize
    """
    import argparse

    parser = argparse.ArgumentParser(description="Initialize TripSage databases")
    parser.add_argument(
        "--run-migrations", action="store_true", help="Run migrations on startup"
    )
    parser.add_argument(
        "--init-neo4j", action="store_true", help="Initialize Neo4j schema"
    )
    parser.add_argument(
        "--verify-schema", action="store_true", help="Verify database schema"
    )
    parser.add_argument(
        "--create-sample-data", action="store_true", help="Create sample data"
    )
    args = parser.parse_args()

    async def main():
        if args.verify_schema:
            results = await verify_database_schema()
            print("Schema verification results:")
            print(results)
            return

        if args.create_sample_data:
            success = await create_sample_data()
            if success:
                print("Sample data created successfully")
            else:
                print("Failed to create sample data")
                exit(1)
            return

        result = await initialize_databases(
            run_migrations_on_startup=args.run_migrations,
            init_neo4j_schema=args.init_neo4j,
        )

        if result:
            print("Database initialization completed successfully")
        else:
            print("Database initialization failed")
            exit(1)

    asyncio.run(main())