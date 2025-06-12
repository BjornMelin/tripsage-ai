#!/usr/bin/env python
"""
Deploy API key management migration directly to Supabase.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.utils.logging_utils import configure_logging

logger = configure_logging("deploy_api_key_migration")


async def deploy_migration():
    """Deploy the API key migration."""
    db_service = DatabaseService()

    try:
        # Connect to database
        await db_service.connect()
        logger.info("Connected to database")

        # Read migration file
        migration_file = (
            project_root
            / "supabase"
            / "migrations"
            / "20250611_02_add_api_key_usage_tables.sql"
        )
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        logger.info(f"Executing migration: {migration_file.name}")

        # Execute migration
        result = await db_service.execute_sql(migration_sql)

        if result:
            logger.info("✅ Migration completed successfully")
        else:
            logger.error("❌ Migration failed")

    except Exception as e:
        logger.error(f"❌ Migration failed with error: {e}")
        raise
    finally:
        await db_service.disconnect()


if __name__ == "__main__":
    asyncio.run(deploy_migration())
