"""
Schema Adapters for TripSage Database Compatibility.

This module provides adapters and utilities to handle schema mismatches
between the database, API, and frontend layers during the migration period.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class SchemaAdapter:
    """
    Handles schema compatibility during the transition period.

    This adapter helps bridge differences between:
    - Database BIGINT IDs vs UUID strings in services
    - Database 'name' field vs API 'title' field
    - Missing fields in legacy data
    """

    @staticmethod
    def normalize_trip_id(trip_id: Union[str, int]) -> str:
        """
        Normalize trip ID to string format for consistent handling.

        Args:
            trip_id: Trip ID as string or integer

        Returns:
            String representation of trip ID
        """
        if isinstance(trip_id, int):
            return str(trip_id)
        return str(trip_id)

    @staticmethod
    def is_uuid(value: str) -> bool:
        """
        Check if a string is a valid UUID.

        Args:
            value: String to check

        Returns:
            True if valid UUID, False otherwise
        """
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def convert_db_trip_to_api(db_trip: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert database trip record to API format.

        Handles field name mappings and missing field defaults.

        Args:
            db_trip: Raw trip data from database

        Returns:
            Trip data formatted for API response
        """
        # Use UUID if available, fallback to BIGINT ID
        trip_id = db_trip.get("uuid_id") or str(db_trip.get("id"))

        # Handle title/name field mapping (updated for schema alignment)
        title = db_trip.get("title") or db_trip.get("name", "Untitled Trip")

        # Handle enhanced budget structure
        budget_breakdown = db_trip.get("budget_breakdown", {})
        enhanced_budget = None
        if budget_breakdown:
            enhanced_budget = {
                "total": budget_breakdown.get("total", db_trip.get("budget", 0)),
                "currency": db_trip.get("currency", "USD"),
                "spent": db_trip.get("spent_amount", 0),
                "breakdown": budget_breakdown.get("breakdown", {})
            }

        # Handle enhanced preferences
        preferences = db_trip.get("preferences_extended", {}) or db_trip.get("preferences", {})
        if not preferences and db_trip.get("flexibility"):
            preferences = SchemaAdapter.migrate_legacy_preferences(db_trip.get("flexibility"))

        # Provide defaults for missing fields
        api_trip = {
            "id": trip_id,
            "user_id": str(db_trip.get("user_id", "")),
            "title": title,
            "name": db_trip.get("name", title),  # Keep both for compatibility
            "description": db_trip.get("description"),
            "start_date": db_trip.get("start_date"),
            "end_date": db_trip.get("end_date"),
            "destination": db_trip.get("destination", ""),
            "budget": db_trip.get("budget", 0),  # Legacy budget
            "enhanced_budget": enhanced_budget,  # New enhanced budget
            "currency": db_trip.get("currency", "USD"),
            "spent_amount": db_trip.get("spent_amount", 0),
            "travelers": db_trip.get("travelers", 1),
            "status": db_trip.get("status", "planning"),
            "trip_type": db_trip.get("trip_type", "leisure"),
            "flexibility": db_trip.get("flexibility", {}),  # Legacy
            "notes": db_trip.get("notes", []),
            "search_metadata": db_trip.get("search_metadata", {}),
            "visibility": db_trip.get("visibility", "private"),
            "tags": db_trip.get("tags", []),
            "preferences": preferences,  # Enhanced preferences
            "created_at": db_trip.get("created_at"),
            "updated_at": db_trip.get("updated_at"),
        }

        # Remove None values
        return {k: v for k, v in api_trip.items() if v is not None}

    @staticmethod
    def convert_api_trip_to_db(api_trip: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert API trip data to database format.

        Handles field name mappings and proper type conversions.

        Args:
            api_trip: Trip data from API request

        Returns:
            Trip data formatted for database storage
        """
        # Handle title -> name mapping for database (now both use 'title')
        title = api_trip.get("title") or api_trip.get("name", "Untitled Trip")
        
        # Handle enhanced budget conversion
        budget_breakdown = {}
        enhanced_budget = api_trip.get("enhanced_budget")
        if enhanced_budget:
            budget_breakdown = {
                "total": enhanced_budget.get("total", 0),
                "breakdown": enhanced_budget.get("breakdown", {})
            }
        
        db_trip = {
            "title": title,  # Updated to use 'title' consistently
            "user_id": api_trip.get("user_id"),
            "description": api_trip.get("description"),
            "start_date": api_trip.get("start_date"),
            "end_date": api_trip.get("end_date"),
            "destination": api_trip.get("destination", ""),
            "budget": api_trip.get("budget", 0),  # Legacy budget
            "budget_breakdown": budget_breakdown,  # Enhanced budget
            "currency": api_trip.get("currency", "USD"),
            "spent_amount": api_trip.get("spent_amount", 0),
            "travelers": api_trip.get("travelers", 1),
            "status": api_trip.get("status", "planning"),
            "trip_type": api_trip.get("trip_type", "leisure"),
            "flexibility": api_trip.get("flexibility", {}),  # Legacy
            "notes": api_trip.get("notes", []),
            "search_metadata": api_trip.get("search_metadata", {}),
            "visibility": api_trip.get("visibility", "private"),
            "tags": api_trip.get("tags", []),
            "preferences_extended": api_trip.get("preferences", {}),  # Enhanced field
        }

        # Handle timestamps
        if "created_at" in api_trip:
            db_trip["created_at"] = api_trip["created_at"]
        if "updated_at" in api_trip:
            db_trip["updated_at"] = api_trip["updated_at"]

        # Remove None values
        return {k: v for k, v in db_trip.items() if v is not None}

    @staticmethod
    def ensure_uuid_id(record: Dict[str, Any]) -> str:
        """
        Ensure a record has a UUID ID, generating one if needed.

        Args:
            record: Database record

        Returns:
            UUID string
        """
        # Check if uuid_id exists
        if record.get("uuid_id"):
            return str(record["uuid_id"])

        # Check if existing ID is already a UUID
        existing_id = record.get("id")
        if existing_id and SchemaAdapter.is_uuid(str(existing_id)):
            return str(existing_id)

        # Generate new UUID
        new_uuid = str(uuid.uuid4())
        logger.info(f"Generated new UUID {new_uuid} for record with ID {existing_id}")
        return new_uuid

    @staticmethod
    def migrate_legacy_preferences(
        flexibility: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Migrate legacy 'flexibility' field to new 'preferences' structure.

        Args:
            flexibility: Legacy flexibility data

        Returns:
            Preferences data in new format
        """
        if not flexibility:
            return {}

        # Convert old flexibility format to new preferences format
        preferences = {
            "budget_flexibility": flexibility.get("budget_flexibility", 0.1),
            "date_flexibility": flexibility.get("date_flexibility", 0),
            "destination_flexibility": flexibility.get(
                "destination_flexibility", False
            ),
            "accommodation_preferences": flexibility.get("accommodation", {}),
            "transportation_preferences": flexibility.get("transportation", {}),
            "activity_preferences": flexibility.get("activities", []),
        }

        return preferences


class MemorySchemaAdapter:
    """
    Adapter for Mem0 memory system compatibility.

    Handles integration between TripSage memory tables and Mem0 collections.
    """

    @staticmethod
    def create_mem0_collection_data(
        name: str, description: str = None
    ) -> Dict[str, Any]:
        """
        Create Mem0 collection data structure.

        Args:
            name: Collection name
            description: Optional description

        Returns:
            Collection data for Mem0 table
        """
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description or f"TripSage collection: {name}",
            "metadata": {
                "source": "tripsage",
                "created_by": "schema_adapter",
                "version": "1.0",
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def convert_tripsage_memory_to_mem0(
        tripsage_memory: Dict[str, Any], collection_id: str
    ) -> Dict[str, Any]:
        """
        Convert TripSage memory record to Mem0 format.

        Args:
            tripsage_memory: TripSage memory record
            collection_id: Target Mem0 collection ID

        Returns:
            Memory record in Mem0 format
        """
        return {
            "id": str(uuid.uuid4()),
            "collection_id": collection_id,
            "user_id": tripsage_memory.get("user_id"),
            "content": tripsage_memory.get("content", ""),
            "metadata": {
                **tripsage_memory.get("metadata", {}),
                "original_id": tripsage_memory.get("id"),
                "memory_type": tripsage_memory.get("memory_type", "unknown"),
                "migrated_from": "tripsage_memories",
            },
            "embedding": tripsage_memory.get("embedding"),
            "created_at": tripsage_memory.get(
                "created_at", datetime.utcnow().isoformat()
            ),
            "updated_at": datetime.utcnow().isoformat(),
        }


class DatabaseQueryAdapter:
    """
    Adapter for database queries during schema transition.

    Provides methods that work with both old and new schema structures.
    """

    @staticmethod
    def build_trip_query(use_uuid: bool = True) -> str:
        """
        Build SQL query for trip selection with proper ID handling.

        Args:
            use_uuid: Whether to prioritize UUID IDs

        Returns:
            SQL query string
        """
        id_field = "COALESCE(uuid_id::text, id::text) AS id" if use_uuid else "id"

        return f"""
        SELECT 
            {id_field},
            id AS id_bigint,
            uuid_id,
            user_id,
            title,
            COALESCE(title, name) AS title,  -- Handle legacy name field
            description,
            start_date,
            end_date,
            destination,
            budget,
            budget_breakdown,
            currency,
            spent_amount,
            travelers,
            status,
            trip_type,
            flexibility,
            notes,
            search_metadata,
            COALESCE(visibility, 'private') AS visibility,
            COALESCE(tags, '{{}}') AS tags,
            COALESCE(preferences_extended, preferences, '{{}}') AS preferences,
            created_at,
            updated_at
        FROM trips
        """

    @staticmethod
    def build_trip_filter_where_clause(trip_id: str) -> tuple[str, dict]:
        """
        Build WHERE clause for trip filtering that works with both ID types.

        Args:
            trip_id: Trip ID to filter by

        Returns:
            Tuple of (where_clause, parameters)
        """
        if SchemaAdapter.is_uuid(trip_id):
            return "WHERE uuid_id = %(trip_id)s OR id::text = %(trip_id)s", {
                "trip_id": trip_id
            }
        else:
            try:
                # Try to parse as integer
                int_id = int(trip_id)
                return "WHERE id = %(trip_id)s OR uuid_id::text = %(trip_id_str)s", {
                    "trip_id": int_id,
                    "trip_id_str": trip_id,
                }
            except ValueError:
                # Fallback to string comparison
                return "WHERE uuid_id::text = %(trip_id)s OR id::text = %(trip_id)s", {
                    "trip_id": trip_id
                }


def validate_schema_compatibility(db_result: Dict[str, Any]) -> bool:
    """
    Validate that a database result has the required fields for API compatibility.

    Args:
        db_result: Database query result

    Returns:
        True if compatible, False otherwise
    """
    required_fields = ["id", "user_id", "name", "start_date", "end_date"]

    for field in required_fields:
        if field not in db_result or db_result[field] is None:
            logger.warning(f"Missing required field '{field}' in database result")
            return False

    return True


def log_schema_usage(
    operation: str, id_type: str, field_mappings: Dict[str, str] = None
):
    """
    Log schema usage for monitoring migration progress.

    Args:
        operation: Database operation being performed
        id_type: Type of ID used (uuid, bigint, mixed)
        field_mappings: Any field mappings applied
    """
    logger.info(
        "Schema adapter usage",
        extra={
            "operation": operation,
            "id_type": id_type,
            "field_mappings": field_mappings or {},
            "migration_stage": "active",
        },
    )
