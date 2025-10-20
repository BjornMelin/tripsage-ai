#!/usr/bin/env python3
"""Database initialization script for TripSage.

Initializes a fresh database with base schema, required extensions,
RLS policies, and optional seed data.

Usage:
    python scripts/database/init_database.py [--with-seed-data] [--env development]
"""

import asyncio
import logging
from pathlib import Path

import click
from supabase import Client, create_client

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.database_service import DatabaseService


logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization with schema and seed data."""

    def __init__(self, db_service: DatabaseService, supabase_client: Client):
        """Initialize database initializer."""
        self.db_service = db_service
        self.supabase_client = supabase_client
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent.parent
        self.schema_dir = self.project_root / "supabase" / "schemas"

    async def initialize_database(self, with_seed_data: bool = False) -> bool:
        """Initialize database with schema and optional seed data."""
        try:
            logger.info("Starting database initialization...")

            # 1. Install required extensions
            success = await self._install_extensions()
            if not success:
                logger.error("Failed to install extensions")
                return False

            # 2. Create base tables
            success = await self._create_base_tables()
            if not success:
                logger.error("Failed to create base tables")
                return False

            # 3. Setup RLS policies
            success = await self._setup_rls_policies()
            if not success:
                logger.error("Failed to setup RLS policies")
                return False

            # 4. Create indexes
            success = await self._create_indexes()
            if not success:
                logger.error("Failed to create indexes")
                return False

            # 5. Seed data if requested
            if with_seed_data:
                success = await self._seed_initial_data()
                if not success:
                    logger.error("Failed to seed initial data")
                    return False

            # 6. Run post-initialization validation
            success = await self._validate_initialization()
            if not success:
                logger.error("Post-initialization validation failed")
                return False

            logger.info("Database initialization completed successfully")
            return True

        except Exception:
            logger.exception("Database initialization failed")
            return False

    async def _install_extensions(self) -> bool:
        """Install required PostgreSQL extensions."""
        extensions = [
            "uuid-ossp",  # UUID generation
            "pg_cron",  # Scheduled jobs
            "pg_net",  # HTTP requests
            "pg_stat_statements",  # Query statistics
        ]

        try:
            logger.info("Installing required extensions...")

            for extension in extensions:
                await self.db_service.execute_sql(
                    f"CREATE EXTENSION IF NOT EXISTS {extension}"
                )
                logger.info(f"✓ Installed extension: {extension}")

            # Verify extensions
            result = await self.db_service.execute_sql("""
                SELECT name FROM pg_available_extensions
                WHERE installed_version IS NOT NULL
            """)

            installed_extensions = [row["name"] for row in result]
            missing = set(extensions) - set(installed_extensions)

            if missing:
                logger.warning(f"Some extensions may not be available: {missing}")

            return True

        except Exception:
            logger.exception("Failed to install extensions")
            return False

    async def _create_base_tables(self) -> bool:
        """Create base database tables."""
        try:
            logger.info("Creating base tables...")

            # Create tables from schema files
            schema_files = [
                "00_extensions.sql",
                "01_auth_schema.sql",
                "02_core_tables.sql",
                "03_storage_schema.sql",
            ]

            for schema_file in schema_files:
                file_path = self.schema_dir / schema_file
                if file_path.exists():
                    schema_sql = file_path.read_text()
                    await self.db_service.execute_sql(schema_sql)
                    logger.info(f"✓ Applied schema: {schema_file}")
                else:
                    logger.warning(f"Schema file not found: {schema_file}")

            return True

        except Exception:
            logger.exception("Failed to create base tables")
            return False

    async def _setup_rls_policies(self) -> bool:
        """Setup Row Level Security policies."""
        try:
            logger.info("Setting up RLS policies...")

            # Enable RLS on tables
            tables_with_rls = [
                "user_profiles",
                "trips",
                "trip_participants",
                "trip_messages",
                "file_attachments",
                "user_preferences",
            ]

            for table in tables_with_rls:
                await self.db_service.execute_sql(
                    f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
                )
                logger.info(f"✓ Enabled RLS on: {table}")

            # Apply RLS policies from policy files
            policy_files = [
                "05_rls_policies.sql",
                "06_auth_policies.sql",
            ]

            for policy_file in policy_files:
                file_path = self.schema_dir / policy_file
                if file_path.exists():
                    policy_sql = file_path.read_text()
                    await self.db_service.execute_sql(policy_sql)
                    logger.info(f"✓ Applied policies: {policy_file}")

            return True

        except Exception:
            logger.exception("Failed to setup RLS policies")
            return False

    async def _create_indexes(self) -> bool:
        """Create performance indexes."""
        try:
            logger.info("Creating indexes...")

            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_trip_messages_trip_id "
                "ON trip_messages(trip_id)",
                "CREATE INDEX IF NOT EXISTS idx_file_attachments_trip_id "
                "ON file_attachments(trip_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_profiles_email "
                "ON user_profiles(email)",
                "CREATE INDEX IF NOT EXISTS idx_trip_participants_trip_id "
                "ON trip_participants(trip_id)",
            ]

            for index_sql in indexes:
                await self.db_service.execute_sql(index_sql)
                index_name = index_sql.split(" ON ")[1].split("(")[0]
                logger.info(f"✓ Created index: {index_name}")

            return True

        except Exception:
            logger.exception("Failed to create indexes")
            return False

    async def _seed_initial_data(self) -> bool:
        """Seed initial data for development/testing."""
        try:
            logger.info("Seeding initial data...")

            # Create default user preferences template
            await self.db_service.execute_sql("""
                INSERT INTO user_preferences
                (id, theme, notifications_enabled, language)
                VALUES (gen_random_uuid(), 'system', true, 'en')
                ON CONFLICT DO NOTHING
            """)

            # Create sample categories if they exist
            await self.db_service.execute_sql("""
                INSERT INTO categories (name, description, icon)
                VALUES
                    ('Adventure', 'Outdoor activities and exploration', '🏔️'),
                    ('Culture', 'Cultural experiences and sightseeing', '🏛️'),
                    ('Relaxation', 'Relaxing and wellness activities', '🏖️'),
                    ('Food', 'Culinary experiences and dining', '🍽️')
                ON CONFLICT (name) DO NOTHING
            """)

            logger.info("✓ Seeded initial data")
            return True

        except Exception:
            logger.exception("Failed to seed initial data")
            return False

    async def _validate_initialization(self) -> bool:
        """Validate that initialization was successful."""
        try:
            logger.info("Validating initialization...")

            # Check that required tables exist
            required_tables = [
                "user_profiles",
                "trips",
                "trip_messages",
                "file_attachments",
                "user_preferences",
            ]

            for table in required_tables:
                result = await self.db_service.execute_sql(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = $1)",
                    (table,),
                )
                if not result[0]["exists"]:
                    logger.error(f"Required table missing: {table}")
                    return False

            # Check that RLS is enabled
            rls_check = await self.db_service.execute_sql("""
                SELECT COUNT(*) as rls_count
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                AND c.relrowsecurity = true
                AND c.relname IN ('user_profiles', 'trips', 'trip_messages')
            """)

            if rls_check[0]["rls_count"] < 3:
                logger.warning("Some tables may not have RLS enabled")

            logger.info("✓ Initialization validation passed")
            return True

        except Exception:
            logger.exception("Initialization validation failed")
            return False


@click.command()
@click.option(
    "--with-seed-data", is_flag=True, help="Include initial seed data for development"
)
@click.option(
    "--env",
    type=click.Choice(["development", "staging", "production"]),
    default="development",
    help="Environment to initialize for",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without making changes"
)
def main(with_seed_data: bool, env: str, dry_run: bool) -> None:
    """Initialize TripSage database with schema and optional seed data."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Override environment for initialization
    import os

    os.environ["ENVIRONMENT"] = env

    async def run_initialization():
        try:
            settings = get_settings()

            # Validate required environment variables
            if not settings.database_url:
                raise click.ClickException("DATABASE_URL environment variable required")

            if not settings.supabase_url or not settings.supabase_service_role_key:
                raise click.ClickException(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required"
                )

            if dry_run:
                click.echo("🔍 DRY RUN MODE - No changes will be made")
                click.echo("Database initialization would:")
                click.echo("  1. Install required PostgreSQL extensions")
                click.echo("  2. Create base tables from schema files")
                click.echo("  3. Setup Row Level Security policies")
                click.echo("  4. Create performance indexes")
                if with_seed_data:
                    click.echo("  5. Seed initial development data")
                click.echo("  6. Validate initialization")
                return

            # Initialize services
            db_service = DatabaseService(settings)
            supabase_client = create_client(
                settings.supabase_url, settings.supabase_service_role_key
            )

            # Run initialization
            initializer = DatabaseInitializer(db_service, supabase_client)
            success = await initializer.initialize_database(
                with_seed_data=with_seed_data
            )

            if success:
                click.echo("✅ Database initialization completed successfully!")
                if env == "development" and with_seed_data:
                    click.echo("💡 Development data seeded - ready for testing")
            else:
                raise click.ClickException("Database initialization failed")

        except Exception as e:
            logger.exception("Initialization failed")
            raise click.ClickException(str(e)) from e

    # Run async initialization
    asyncio.run(run_initialization())


if __name__ == "__main__":
    main()
