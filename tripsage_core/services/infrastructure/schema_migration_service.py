"""
Schema Migration Service for TripSage Database.

This service handles the migration from BIGINT IDs to UUIDs and manages
schema compatibility during the transition period.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from tripsage_core.utils.schema_adapters import (
    MemorySchemaAdapter,
    SchemaAdapter,
)

logger = logging.getLogger(__name__)


class SchemaMigrationService:
    """
    Service for managing schema migrations and compatibility.

    Handles the transition from BIGINT IDs to UUIDs while maintaining
    backward compatibility with existing data and APIs.
    """

    def __init__(self, database_service):
        """
        Initialize the migration service.

        Args:
            database_service: Database service instance
        """
        self.db = database_service
        self.migration_status = {}

    async def check_migration_status(self) -> Dict[str, Any]:
        """
        Check the current migration status of the database.

        Returns:
            Dictionary with migration status information
        """
        try:
            # Check if new columns exist
            columns_check = await self.db.execute_query("""
                SELECT 
                    table_name,
                    column_name,
                    data_type
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                    AND table_name IN ('trips', 'flights', 'accommodations')
                    AND column_name IN ('uuid_id', 'visibility', 'tags', 'preferences', 'title')
                ORDER BY table_name, column_name
            """)

            # Check UUID population status
            uuid_status = await self.db.execute_query("""
                SELECT 
                    'trips' as table_name,
                    COUNT(*) as total_records,
                    COUNT(uuid_id) as uuid_populated,
                    COUNT(title) as title_populated
                FROM trips
                UNION ALL
                SELECT 
                    'flights' as table_name,
                    COUNT(*) as total_records,
                    COUNT(uuid_id) as uuid_populated,
                    COUNT(trip_uuid) as trip_uuid_populated
                FROM flights
                UNION ALL
                SELECT 
                    'accommodations' as table_name,
                    COUNT(*) as total_records,
                    COUNT(uuid_id) as uuid_populated,
                    COUNT(trip_uuid) as trip_uuid_populated
                FROM accommodations
            """)

            # Check if Mem0 tables exist
            mem0_check = await self.db.execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                    AND table_name IN ('mem0_collections', 'mem0_memories')
            """)

            self.migration_status = {
                "timestamp": datetime.utcnow().isoformat(),
                "columns_added": len(columns_check),
                "uuid_status": {row["table_name"]: row for row in uuid_status},
                "mem0_tables_exist": len(mem0_check) == 2,
                "migration_complete": self._assess_migration_complete(
                    columns_check, uuid_status, mem0_check
                ),
            }

            return self.migration_status

        except Exception as e:
            logger.error(f"Failed to check migration status: {e}")
            return {"error": str(e)}

    async def execute_schema_migration(self) -> Dict[str, Any]:
        """
        Execute the schema alignment migration.

        Returns:
            Migration execution results
        """
        try:
            logger.info("Starting schema alignment migration")

            # Run the migration SQL
            migration_sql_path = (
                "supabase/migrations/20250611_02_schema_alignment_fixes.sql"
            )
            await self.db.execute_migration_file(migration_sql_path)

            # Verify migration success
            status = await self.check_migration_status()

            if status.get("migration_complete"):
                logger.info("Schema alignment migration completed successfully")
                return {"success": True, "status": status}
            else:
                logger.warning("Migration completed but status check indicates issues")
                return {
                    "success": False,
                    "status": status,
                    "warning": "Migration may be incomplete",
                }

        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            return {"success": False, "error": str(e)}

    async def migrate_trip_ids_to_uuid(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Migrate trip IDs from BIGINT to UUID in batches.

        Args:
            batch_size: Number of records to process per batch

        Returns:
            Migration results
        """
        try:
            logger.info(
                f"Starting trip ID migration to UUID (batch size: {batch_size})"
            )

            # Get trips that need UUID migration
            trips_to_migrate = await self.db.execute_query(
                """
                SELECT id, uuid_id, name 
                FROM trips 
                WHERE uuid_id IS NULL
                LIMIT %s
            """,
                (batch_size,),
            )

            if not trips_to_migrate:
                logger.info("No trips need UUID migration")
                return {
                    "success": True,
                    "migrated": 0,
                    "message": "All trips already have UUIDs",
                }

            migrated_count = 0

            for trip in trips_to_migrate:
                # Generate UUID for the trip
                new_uuid = str(uuid.uuid4())

                # Update the trip with UUID
                await self.db.execute_query(
                    """
                    UPDATE trips 
                    SET uuid_id = %s, updated_at = NOW()
                    WHERE id = %s
                """,
                    (new_uuid, trip["id"]),
                )

                # Update related tables with trip_uuid references
                await self._update_related_trip_references(trip["id"], new_uuid)

                migrated_count += 1
                logger.debug(f"Migrated trip {trip['id']} to UUID {new_uuid}")

            logger.info(f"Successfully migrated {migrated_count} trips to UUID")
            return {
                "success": True,
                "migrated": migrated_count,
                "remaining": await self._count_trips_needing_migration(),
            }

        except Exception as e:
            logger.error(f"Trip ID migration failed: {e}")
            return {"success": False, "error": str(e)}

    async def migrate_legacy_preferences(self) -> Dict[str, Any]:
        """
        Migrate legacy 'flexibility' field data to new 'preferences' structure.

        Returns:
            Migration results
        """
        try:
            logger.info("Starting legacy preferences migration")

            # Get trips with flexibility data but no preferences
            trips_to_migrate = await self.db.execute_query("""
                SELECT id, uuid_id, flexibility 
                FROM trips 
                WHERE flexibility IS NOT NULL 
                    AND flexibility != '{}'
                    AND (preferences IS NULL OR preferences = '{}')
            """)

            migrated_count = 0

            for trip in trips_to_migrate:
                flexibility_data = trip.get("flexibility", {})
                if not flexibility_data:
                    continue

                # Convert flexibility to preferences format
                preferences = SchemaAdapter.migrate_legacy_preferences(flexibility_data)

                # Update the trip
                await self.db.execute_query(
                    """
                    UPDATE trips 
                    SET preferences = %s, updated_at = NOW()
                    WHERE id = %s
                """,
                    (preferences, trip["id"]),
                )

                migrated_count += 1
                logger.debug(f"Migrated preferences for trip {trip['id']}")

            logger.info(f"Successfully migrated preferences for {migrated_count} trips")
            return {"success": True, "migrated": migrated_count}

        except Exception as e:
            logger.error(f"Preferences migration failed: {e}")
            return {"success": False, "error": str(e)}

    async def setup_mem0_collections(self) -> Dict[str, Any]:
        """
        Set up default Mem0 collections for the application.

        Returns:
            Setup results
        """
        try:
            logger.info("Setting up Mem0 collections")

            # Default collections to create
            default_collections = [
                {
                    "name": "user_preferences",
                    "description": "User travel preferences and patterns",
                },
                {
                    "name": "trip_history",
                    "description": "Historical trip data and experiences",
                },
                {
                    "name": "destination_knowledge",
                    "description": "Knowledge about destinations and locations",
                },
                {
                    "name": "conversation_context",
                    "description": "Chat conversation context and memory",
                },
            ]

            created_count = 0

            for collection_config in default_collections:
                # Check if collection already exists
                existing = await self.db.execute_query(
                    """
                    SELECT id FROM mem0_collections WHERE name = %s
                """,
                    (collection_config["name"],),
                )

                if existing:
                    logger.debug(
                        f"Collection {collection_config['name']} already exists"
                    )
                    continue

                # Create collection
                collection_data = MemorySchemaAdapter.create_mem0_collection_data(
                    collection_config["name"], collection_config["description"]
                )

                await self.db.execute_query(
                    """
                    INSERT INTO mem0_collections (id, name, description, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        collection_data["id"],
                        collection_data["name"],
                        collection_data["description"],
                        collection_data["metadata"],
                        collection_data["created_at"],
                        collection_data["updated_at"],
                    ),
                )

                created_count += 1
                logger.info(f"Created Mem0 collection: {collection_config['name']}")

            return {"success": True, "created": created_count}

        except Exception as e:
            logger.error(f"Mem0 collection setup failed: {e}")
            return {"success": False, "error": str(e)}

    async def validate_schema_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of the migrated schema.

        Returns:
            Validation results
        """
        try:
            logger.info("Validating schema integrity")

            validation_results = {}

            # Check for orphaned records
            orphaned_flights = await self.db.execute_query("""
                SELECT COUNT(*) as count 
                FROM flights f 
                LEFT JOIN trips t ON f.trip_id = t.id 
                WHERE t.id IS NULL
            """)
            validation_results["orphaned_flights"] = orphaned_flights[0]["count"]

            # Check UUID consistency
            uuid_consistency = await self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_trips,
                    COUNT(uuid_id) as trips_with_uuid,
                    COUNT(CASE WHEN uuid_id IS NOT NULL THEN 1 END) as valid_uuids
                FROM trips
            """)
            validation_results["uuid_consistency"] = uuid_consistency[0]

            # Check title/name consistency
            title_consistency = await self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN title IS NOT NULL THEN 1 END) as trips_with_title,
                    COUNT(CASE WHEN name IS NOT NULL THEN 1 END) as trips_with_name
                FROM trips
            """)
            validation_results["title_consistency"] = title_consistency[0]

            # Check preferences migration
            preferences_check = await self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_trips,
                    COUNT(CASE WHEN preferences IS NOT NULL AND preferences != '{}' THEN 1 END) as trips_with_preferences,
                    COUNT(CASE WHEN flexibility IS NOT NULL AND flexibility != '{}' THEN 1 END) as trips_with_flexibility
                FROM trips
            """)
            validation_results["preferences_migration"] = preferences_check[0]

            # Determine overall integrity status
            integrity_issues = []

            if validation_results["orphaned_flights"] > 0:
                integrity_issues.append(
                    f"{validation_results['orphaned_flights']} orphaned flight records"
                )

            uuid_data = validation_results["uuid_consistency"]
            if uuid_data["total_trips"] != uuid_data["trips_with_uuid"]:
                missing_uuids = uuid_data["total_trips"] - uuid_data["trips_with_uuid"]
                integrity_issues.append(f"{missing_uuids} trips missing UUIDs")

            validation_results["integrity_status"] = {
                "valid": len(integrity_issues) == 0,
                "issues": integrity_issues,
            }

            return {"success": True, "validation": validation_results}

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _update_related_trip_references(
        self, trip_bigint_id: int, trip_uuid: str
    ):
        """Update all related tables with new trip UUID reference."""

        # Update flights
        await self.db.execute_query(
            """
            UPDATE flights 
            SET trip_uuid = %s 
            WHERE trip_id = %s
        """,
            (trip_uuid, trip_bigint_id),
        )

        # Update accommodations
        await self.db.execute_query(
            """
            UPDATE accommodations 
            SET trip_uuid = %s 
            WHERE trip_id = %s
        """,
            (trip_uuid, trip_bigint_id),
        )

        # Update transportation
        await self.db.execute_query(
            """
            UPDATE transportation 
            SET trip_uuid = %s 
            WHERE trip_id = %s
        """,
            (trip_uuid, trip_bigint_id),
        )

        # Update itinerary_items
        await self.db.execute_query(
            """
            UPDATE itinerary_items 
            SET trip_uuid = %s 
            WHERE trip_id = %s
        """,
            (trip_uuid, trip_bigint_id),
        )

        # Update chat_sessions
        await self.db.execute_query(
            """
            UPDATE chat_sessions 
            SET trip_uuid = %s 
            WHERE trip_id = %s
        """,
            (trip_uuid, trip_bigint_id),
        )

        # Update trip_collaborators
        await self.db.execute_query(
            """
            UPDATE trip_collaborators 
            SET trip_uuid = %s 
            WHERE trip_id = %s
        """,
            (trip_uuid, trip_bigint_id),
        )

    async def _count_trips_needing_migration(self) -> int:
        """Count trips that still need UUID migration."""
        result = await self.db.execute_query("""
            SELECT COUNT(*) as count 
            FROM trips 
            WHERE uuid_id IS NULL
        """)
        return result[0]["count"] if result else 0

    def _assess_migration_complete(
        self, columns_check, uuid_status, mem0_check
    ) -> bool:
        """Assess if migration is complete based on checks."""
        # Check if required columns exist (should be at least 15 columns total)
        if len(columns_check) < 10:
            return False

        # Check if UUID population is complete for trips
        trips_status = next(
            (row for row in uuid_status if row["table_name"] == "trips"), None
        )
        if (
            trips_status
            and trips_status["total_records"] != trips_status["uuid_populated"]
        ):
            return False

        # Check if Mem0 tables exist
        if len(mem0_check) < 2:
            return False

        return True


# Dependency function for FastAPI
async def get_schema_migration_service():
    """Get schema migration service instance."""
    from tripsage_core.services.infrastructure.database_service import (
        get_database_service,
    )

    database_service = await get_database_service()
    return SchemaMigrationService(database_service)
