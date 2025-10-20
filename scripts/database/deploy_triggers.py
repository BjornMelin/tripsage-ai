#!/usr/bin/env python3
"""Deploy Database Triggers Script
Applies business logic and automation triggers to the database.
"""

import asyncio
import contextlib
import logging
import sys
from pathlib import Path

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.database_service import DatabaseService


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TriggerDeploymentService:
    """Service for deploying database triggers."""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.migrations_dir = (
            Path(__file__).parent.parent.parent / "supabase" / "migrations"
        )

    async def check_prerequisites(self) -> bool:
        """Check if database is ready for trigger deployment."""
        try:
            # Check if base tables exist
            required_tables = [
                "trips",
                "trip_collaborators",
                "flights",
                "accommodations",
                "chat_sessions",
                "chat_messages",
                "file_attachments",
                "memories",
                "session_memories",
                "users",
            ]

            for table in required_tables:
                result = await self.db_service.fetch_query(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = $1
                    )
                    """,
                    table,
                )

                if not result[0]["exists"]:
                    logger.exception(f"Required table '{table}' does not exist")
                    return False

            logger.info("All prerequisite tables found")
            return True

        except Exception:
            logger.exception("Error checking prerequisites")
            return False

    async def check_existing_triggers(self) -> dict:
        """Check what triggers already exist."""
        try:
            existing_triggers = await self.db_service.fetch_query(
                """
                SELECT trigger_name, event_object_table, action_timing,
                       event_manipulation
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                ORDER BY trigger_name
                """
            )

            trigger_info = {}
            for trigger in existing_triggers:
                table = trigger["event_object_table"]
                if table not in trigger_info:
                    trigger_info[table] = []
                trigger_info[table].append(
                    {
                        "name": trigger["trigger_name"],
                        "timing": trigger["action_timing"],
                        "event": trigger["event_manipulation"],
                    }
                )

            logger.info(f"Found {len(existing_triggers)} existing triggers")
            return trigger_info

        except Exception:
            logger.exception("Error checking existing triggers")
            return {}

    async def check_existing_functions(self) -> list:
        """Check what trigger functions already exist."""
        try:
            existing_functions = await self.db_service.fetch_query(
                """
                SELECT routine_name, routine_type
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_type = 'FUNCTION'
                AND (routine_name LIKE '%trigger%'
                     OR routine_name LIKE '%cleanup%'
                     OR routine_name LIKE '%notify%')
                ORDER BY routine_name
                """
            )

            function_names = [f["routine_name"] for f in existing_functions]
            logger.info(f"Found {len(function_names)} trigger-related functions")
            return function_names

        except Exception:
            logger.exception("Error checking existing functions")
            return []

    async def deploy_trigger_migration(self) -> bool:
        """Deploy the trigger migration file."""
        try:
            migration_file = (
                self.migrations_dir / "20250611_02_add_business_logic_triggers.sql"
            )

            if not migration_file.exists():
                logger.exception(f"Migration file not found: {migration_file}")
                return False

            logger.info(f"Reading migration file: {migration_file}")
            migration_sql = migration_file.read_text()

            # Execute the migration
            logger.info("Executing trigger migration...")
            await self.db_service.execute_query(migration_sql)

            logger.info("Trigger migration executed successfully")
            return True

        except Exception:
            logger.exception("Error deploying trigger migration")
            return False

    async def validate_trigger_deployment(self) -> bool:
        """Validate that triggers were deployed correctly."""
        try:
            # Expected triggers to be created
            expected_triggers = [
                ("trip_collaborators", "notify_trip_collaboration_changes"),
                ("trip_collaborators", "validate_collaboration_permissions_trigger"),
                ("trip_collaborators", "audit_trip_collaboration_changes"),
                ("trips", "notify_trips_cache_invalidation"),
                ("flights", "notify_flights_cache_invalidation"),
                ("accommodations", "notify_accommodations_cache_invalidation"),
                ("chat_sessions", "auto_expire_inactive_sessions"),
                ("chat_messages", "cleanup_message_attachments"),
                ("flights", "update_trip_status_from_flight_bookings"),
                ("accommodations", "update_trip_status_from_accommodation_bookings"),
            ]

            missing_triggers = []

            for table, trigger_name in expected_triggers:
                result = await self.db_service.fetch_query(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.triggers
                        WHERE trigger_schema = 'public'
                        AND event_object_table = $1
                        AND trigger_name = $2
                    )
                    """,
                    table,
                    trigger_name,
                )

                if not result[0]["exists"]:
                    missing_triggers.append(f"{table}.{trigger_name}")

            if missing_triggers:
                logger.exception(f"Missing triggers: {', '.join(missing_triggers)}")
                return False

            # Expected functions to be created
            expected_functions = [
                "notify_collaboration_change",
                "validate_collaboration_permissions",
                "notify_cache_invalidation",
                "cleanup_related_search_cache",
                "auto_expire_chat_session",
                "cleanup_orphaned_attachments",
                "update_trip_status_from_bookings",
                "audit_collaboration_changes",
                "daily_cleanup_job",
                "weekly_maintenance_job",
                "monthly_cleanup_job",
            ]

            missing_functions = []

            for function_name in expected_functions:
                result = await self.db_service.fetch_query(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.routines
                        WHERE routine_schema = 'public'
                        AND routine_name = $1
                        AND routine_type = 'FUNCTION'
                    )
                    """,
                    function_name,
                )

                if not result[0]["exists"]:
                    missing_functions.append(function_name)

            if missing_functions:
                logger.exception(f"Missing functions: {', '.join(missing_functions)}")
                return False

            logger.info("All expected triggers and functions are present")
            return True

        except Exception:
            logger.exception("Error validating trigger deployment")
            return False

    async def test_trigger_functionality(self) -> bool:
        """Test basic trigger functionality."""
        try:
            # Test collaboration trigger
            logger.info("Testing collaboration triggers...")

            # Create test data
            user_id = "550e8400-e29b-41d4-a716-446655440000"
            owner_id = "550e8400-e29b-41d4-a716-446655440001"

            trip_result = await self.db_service.execute_query(
                """
                INSERT INTO trips (
                    user_id, name, destination, start_date, end_date, status
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                owner_id,
                "Trigger Test Trip",
                "Test City",
                "2025-12-01",
                "2025-12-10",
                "planning",
            )

            trip_id = trip_result[0]["id"]

            # Test collaboration trigger (should work without errors)
            await self.db_service.execute_query(
                """
                INSERT INTO trip_collaborators
                (trip_id, user_id, added_by, permission_level)
                VALUES ($1, $2, $3, $4)
                """,
                trip_id,
                user_id,
                owner_id,
                "view",
            )

            # Test cache invalidation trigger
            logger.info("Testing cache invalidation triggers...")

            await self.db_service.execute_query(
                """
                UPDATE trips SET destination = 'Updated Test City'
                WHERE id = $1
                """,
                trip_id,
            )

            # Test permission validation trigger
            logger.info("Testing permission validation trigger...")

            try:
                # This should fail due to permission validation
                await self.db_service.execute_query(
                    """
                    UPDATE trip_collaborators
                    SET permission_level = 'admin', added_by = $1
                    WHERE trip_id = $2 AND user_id = $1
                    """,
                    user_id,
                    trip_id,
                )
                logger.warning(
                    "Permission validation trigger did not prevent invalid operation"
                )
            except Exception as e:
                if "Cannot modify your own permission level" in str(e):
                    logger.info("Permission validation trigger working correctly")
                else:
                    logger.exception("Unexpected error in permission validation")
                    return False

            # Cleanup test data
            await self.db_service.execute_query(
                "DELETE FROM trip_collaborators WHERE trip_id = $1", trip_id
            )
            await self.db_service.execute_query(
                "DELETE FROM trips WHERE id = $1", trip_id
            )

            logger.info("Trigger functionality tests passed")
            return True

        except Exception:
            logger.exception("Error testing trigger functionality")
            return False

    async def setup_pg_cron_jobs(self) -> bool:
        """Setup pg_cron scheduled jobs if extension is available."""
        try:
            # Check if pg_cron extension is available
            result = await self.db_service.fetch_query(
                """
                SELECT EXISTS (
                    SELECT FROM pg_extension WHERE extname = 'pg_cron'
                )
                """
            )

            if not result[0]["exists"]:
                logger.warning(
                    "pg_cron extension not available - "
                    "scheduled jobs will not be configured"
                )
                return True

            logger.info("Setting up pg_cron scheduled jobs...")

            # Schedule jobs
            jobs = [
                ("daily-cleanup", "0 2 * * *", "SELECT daily_cleanup_job();"),
                ("weekly-maintenance", "0 3 * * 0", "SELECT weekly_maintenance_job();"),
                ("monthly-cleanup", "0 4 1 * *", "SELECT monthly_cleanup_job();"),
                (
                    "search-cache-cleanup",
                    "0 */6 * * *",
                    "SELECT cleanup_expired_search_cache();",
                ),
                (
                    "expire-sessions",
                    "0 * * * *",
                    "SELECT expire_inactive_sessions(24);",
                ),
            ]

            for job_name, schedule, command in jobs:
                try:
                    # Check if job already exists
                    existing = await self.db_service.fetch_query(
                        "SELECT jobid FROM cron.job WHERE jobname = $1", job_name
                    )

                    if existing:
                        logger.info(f"Job '{job_name}' already exists, skipping")
                        continue

                    # Schedule the job
                    await self.db_service.execute_query(
                        "SELECT cron.schedule($1, $2, $3)", job_name, schedule, command
                    )

                    logger.info(
                        f"Scheduled job '{job_name}' with schedule '{schedule}'"
                    )

                except Exception:
                    logger.exception(f"Error scheduling job '{job_name}'")

            logger.info("pg_cron jobs setup completed")
            return True

        except Exception:
            logger.exception("Error setting up pg_cron jobs")
            return False

    async def generate_deployment_report(self) -> dict:
        """Generate a deployment status report."""
        try:
            report = {
                "deployment_time": str(asyncio.get_event_loop().time()),
                "triggers": await self.check_existing_triggers(),
                "functions": await self.check_existing_functions(),
            }

            # Check pg_cron status
            try:
                result = await self.db_service.fetch_query(
                    "SELECT COUNT(*) as job_count FROM cron.job "
                    "WHERE jobname LIKE '%cleanup%' OR jobname LIKE '%maintenance%'"
                )
                report["scheduled_jobs"] = result[0]["job_count"]
            except Exception:
                report["scheduled_jobs"] = "pg_cron not available"

            # Get recent maintenance logs
            try:
                logs = await self.db_service.fetch_query(
                    """
                    SELECT content, metadata, created_at
                    FROM session_memories
                    WHERE metadata->>'type' = 'maintenance'
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                )
                report["recent_maintenance"] = [
                    {
                        "content": log["content"],
                        "job": log["metadata"].get("job"),
                        "timestamp": str(log["created_at"]),
                    }
                    for log in logs
                ]
            except Exception:
                report["recent_maintenance"] = []

            return report

        except Exception as e:
            logger.exception("Error generating deployment report")
            return {"error": str(e)}


async def main():
    """Main deployment function."""
    logger.info("Starting database trigger deployment...")

    try:
        # Initialize services
        settings = get_settings()
        db_service = DatabaseService(settings)
        await db_service.initialize()

        deployment_service = TriggerDeploymentService(db_service)

        # Check prerequisites
        logger.info("Checking prerequisites...")
        if not await deployment_service.check_prerequisites():
            logger.exception("Prerequisites not met - aborting deployment")
            return False

        # Show current state
        logger.info("Current database state:")
        triggers = await deployment_service.check_existing_triggers()
        functions = await deployment_service.check_existing_functions()

        logger.info(f"Existing triggers: {sum(len(t) for t in triggers.values())}")
        logger.info(f"Existing functions: {len(functions)}")

        # Deploy triggers
        logger.info("Deploying trigger migration...")
        if not await deployment_service.deploy_trigger_migration():
            logger.exception("Trigger deployment failed")
            return False

        # Validate deployment
        logger.info("Validating deployment...")
        if not await deployment_service.validate_trigger_deployment():
            logger.exception("Trigger deployment validation failed")
            return False

        # Test functionality
        logger.info("Testing trigger functionality...")
        if not await deployment_service.test_trigger_functionality():
            logger.exception("Trigger functionality tests failed")
            return False

        # Setup scheduled jobs
        logger.info("Setting up scheduled jobs...")
        await deployment_service.setup_pg_cron_jobs()

        # Generate report
        logger.info("Generating deployment report...")
        report = await deployment_service.generate_deployment_report()

        logger.info("=== DEPLOYMENT REPORT ===")
        total_triggers = sum(len(t) for t in report["triggers"].values())
        logger.info(f"Total triggers deployed: {total_triggers}")
        logger.info(f"Total functions deployed: {len(report['functions'])}")
        logger.info(f"Scheduled jobs: {report['scheduled_jobs']}")

        if report.get("recent_maintenance"):
            logger.info("Recent maintenance activity found:")
            for maintenance in report["recent_maintenance"][:3]:
                logger.info(f"  {maintenance['timestamp']}: {maintenance['content']}")

        logger.info("Database trigger deployment completed successfully!")
        return True

    except Exception:
        logger.exception("Deployment failed with error")
        return False

    finally:
        with contextlib.suppress(Exception):
            await db_service.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
