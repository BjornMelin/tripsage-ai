#!/usr/bin/env python3
"""
Schema Alignment Validation Script

This script validates that the schema alignment migration has been applied correctly
and that all layers (database, backend, frontend) are properly aligned.
"""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from tripsage_core.models.db.trip import Trip, TripBudget, TripVisibility
    from tripsage_core.utils.schema_adapters import SchemaAdapter
    from tripsage_core.services.infrastructure.database_service import get_database_service
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaAlignmentValidator:
    """Validates schema alignment across all layers."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.db_service = None

    async def initialize_database(self) -> bool:
        """Initialize database connection."""
        try:
            self.db_service = get_database_service()
            return True
        except Exception as e:
            self.errors.append(f"Failed to connect to database: {e}")
            return False

    def validate_trip_model_structure(self) -> bool:
        """Validate the enhanced Trip model structure."""
        logger.info("Validating Trip model structure...")
        
        try:
            # Test basic trip creation
            trip = Trip(
                title="Test Trip",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 15),
                destination="Test Destination",
                travelers=2,
            )
            
            # Check enhanced fields exist
            required_fields = [
                'title', 'description', 'visibility', 'tags', 'preferences',
                'enhanced_budget', 'currency', 'spent_amount'
            ]
            
            for field in required_fields:
                if not hasattr(trip, field):
                    self.errors.append(f"Trip model missing field: {field}")
            
            # Check legacy compatibility
            if trip.name != trip.title:
                self.errors.append("Legacy 'name' property not working correctly")
            
            # Check property methods
            if not hasattr(trip, 'effective_budget'):
                self.errors.append("Trip model missing 'effective_budget' property")
            
            if not hasattr(trip, 'budget_utilization'):
                self.errors.append("Trip model missing 'budget_utilization' property")
            
            if not hasattr(trip, 'is_shared'):
                self.errors.append("Trip model missing 'is_shared' property")
            
            # Test enhanced budget
            enhanced_budget = TripBudget(
                total=1000.0,
                currency="USD",
                spent=200.0,
                breakdown={"accommodation": 500, "food": 300}
            )
            
            trip_with_budget = Trip(
                title="Budget Test",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 15),
                destination="Test",
                travelers=1,
                enhanced_budget=enhanced_budget,
                spent_amount=200.0
            )
            
            if trip_with_budget.effective_budget != 1000.0:
                self.errors.append("Enhanced budget not working correctly")
            
            if abs(trip_with_budget.budget_utilization - 20.0) > 0.01:
                self.errors.append("Budget utilization calculation incorrect")
            
            logger.info("✓ Trip model structure validation passed")
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Trip model validation failed: {e}")
            return False

    def validate_schema_adapter(self) -> bool:
        """Validate the schema adapter functionality."""
        logger.info("Validating schema adapter...")
        
        try:
            # Test database to API conversion
            db_record = {
                "id": 123,
                "uuid_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user123",
                "title": "Test Trip",
                "description": "Test Description",
                "start_date": date(2025, 6, 1),
                "end_date": date(2025, 6, 15),
                "destination": "Test Destination",
                "budget": 1000,
                "budget_breakdown": {
                    "total": 1000,
                    "breakdown": {"accommodation": 600, "food": 400}
                },
                "currency": "USD",
                "spent_amount": 150,
                "travelers": 2,
                "status": "planning",
                "visibility": "private",
                "tags": ["test", "validation"],
                "preferences_extended": {
                    "accommodation": {"type": "hotel"}
                }
            }
            
            api_data = SchemaAdapter.convert_db_trip_to_api(db_record)
            
            # Validate conversions
            expected_mappings = [
                ("title", "Test Trip"),
                ("name", "Test Trip"),  # Legacy compatibility
                ("visibility", "private"),
                ("tags", ["test", "validation"]),
            ]
            
            for field, expected_value in expected_mappings:
                if field not in api_data:
                    self.errors.append(f"Missing field in API conversion: {field}")
                elif api_data[field] != expected_value:
                    self.errors.append(
                        f"Incorrect value for {field}: got {api_data[field]}, "
                        f"expected {expected_value}"
                    )
            
            # Validate enhanced budget conversion
            if "enhanced_budget" not in api_data:
                self.errors.append("Enhanced budget not converted correctly")
            else:
                budget = api_data["enhanced_budget"]
                if budget["total"] != 1000:
                    self.errors.append("Enhanced budget total incorrect")
                if budget["spent"] != 150:
                    self.errors.append("Enhanced budget spent amount incorrect")
            
            # Test API to database conversion
            api_trip = {
                "title": "API Test Trip",
                "description": "API Test Description",
                "start_date": date(2025, 7, 1),
                "end_date": date(2025, 7, 10),
                "enhanced_budget": {
                    "total": 2000,
                    "currency": "EUR",
                    "spent": 300,
                    "breakdown": {"accommodation": 1200, "food": 500}
                },
                "visibility": "shared",
                "tags": ["api", "test"],
                "preferences": {
                    "accommodation": {"min_rating": 4}
                }
            }
            
            db_data = SchemaAdapter.convert_api_trip_to_db(api_trip)
            
            # Validate database conversion
            if db_data["title"] != "API Test Trip":
                self.errors.append("Title not converted correctly to database")
            
            if "budget_breakdown" not in db_data:
                self.errors.append("Budget breakdown not converted to database")
            
            if "preferences_extended" not in db_data:
                self.errors.append("Preferences not converted to database field")
            
            logger.info("✓ Schema adapter validation passed")
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Schema adapter validation failed: {e}")
            return False

    async def validate_database_schema(self) -> bool:
        """Validate database schema has been updated correctly."""
        logger.info("Validating database schema...")
        
        if not self.db_service:
            self.errors.append("Database service not initialized")
            return False
        
        try:
            # Check if new columns exist
            query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'trips' 
            AND table_schema = 'public'
            ORDER BY column_name;
            """
            
            result = await self.db_service.fetch_all(query)
            columns = {row["column_name"]: row for row in result}
            
            # Check required new columns
            required_columns = [
                "title", "description", "visibility", "tags", 
                "preferences_extended", "budget_breakdown", 
                "currency", "spent_amount", "uuid_id"
            ]
            
            for column in required_columns:
                if column not in columns:
                    self.errors.append(f"Missing database column: {column}")
            
            # Check column types
            expected_types = {
                "title": "text",
                "description": "text", 
                "visibility": "text",
                "tags": "ARRAY",
                "preferences_extended": "jsonb",
                "budget_breakdown": "jsonb",
                "currency": "text",
                "spent_amount": "numeric",
                "uuid_id": "uuid"
            }
            
            for column, expected_type in expected_types.items():
                if column in columns:
                    actual_type = columns[column]["data_type"]
                    if expected_type not in actual_type:
                        self.warnings.append(
                            f"Column {column} type mismatch: "
                            f"expected {expected_type}, got {actual_type}"
                        )
            
            # Check constraints
            constraints_query = """
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'trips' 
            AND table_schema = 'public'
            AND constraint_type = 'CHECK';
            """
            
            constraints = await self.db_service.fetch_all(constraints_query)
            constraint_names = [c["constraint_name"] for c in constraints]
            
            expected_constraints = [
                "trips_visibility_check",
                "trips_spent_amount_check"
            ]
            
            for constraint in expected_constraints:
                if constraint not in constraint_names:
                    self.warnings.append(f"Missing database constraint: {constraint}")
            
            # Check indexes
            indexes_query = """
            SELECT indexname
            FROM pg_indexes 
            WHERE tablename = 'trips'
            AND schemaname = 'public';
            """
            
            indexes = await self.db_service.fetch_all(indexes_query)
            index_names = [idx["indexname"] for idx in indexes]
            
            expected_indexes = [
                "idx_trips_uuid_id",
                "idx_trips_visibility",
                "idx_trips_tags"
            ]
            
            for index in expected_indexes:
                if index not in index_names:
                    self.warnings.append(f"Missing database index: {index}")
            
            logger.info("✓ Database schema validation passed")
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Database schema validation failed: {e}")
            return False

    def validate_frontend_types(self) -> bool:
        """Validate frontend TypeScript types alignment."""
        logger.info("Validating frontend types...")
        
        try:
            # Read the frontend trip store file
            frontend_file = project_root / "frontend" / "src" / "stores" / "trip-store.ts"
            
            if not frontend_file.exists():
                self.errors.append("Frontend trip store file not found")
                return False
            
            content = frontend_file.read_text()
            
            # Check for required interfaces and types
            required_elements = [
                "interface EnhancedBudget",
                "interface TripPreferences", 
                "enhanced_budget?: EnhancedBudget",
                "visibility?: 'private' | 'shared' | 'public'",
                "tags?: string[]",
                "preferences?: TripPreferences",
                "uuid_id?: string",
                "spent_amount?: number"
            ]
            
            for element in required_elements:
                if element not in content:
                    self.errors.append(f"Missing frontend type element: {element}")
            
            # Check for backward compatibility elements
            compatibility_elements = [
                "name?: string", # Legacy compatibility
                "isPublic?: boolean", # Legacy field
                "start_date?: string", # API compatibility
                "startDate?: string", # Frontend compatibility
            ]
            
            for element in compatibility_elements:
                if element not in content:
                    self.warnings.append(f"Missing compatibility element: {element}")
            
            logger.info("✓ Frontend types validation passed")
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Frontend types validation failed: {e}")
            return False

    async def run_validation(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validation checks."""
        logger.info("Starting schema alignment validation...")
        
        # Initialize database if possible
        await self.initialize_database()
        
        # Run all validations
        validations = [
            ("Trip Model Structure", self.validate_trip_model_structure),
            ("Schema Adapter", self.validate_schema_adapter),
            ("Frontend Types", self.validate_frontend_types),
        ]
        
        # Add database validation if connected
        if self.db_service:
            validations.append(("Database Schema", self.validate_database_schema))
        else:
            self.warnings.append("Skipping database validation - no connection")
        
        success = True
        for name, validation_func in validations:
            try:
                if asyncio.iscoroutinefunction(validation_func):
                    result = await validation_func()
                else:
                    result = validation_func()
                
                if not result:
                    success = False
                    logger.error(f"✗ {name} validation failed")
                else:
                    logger.info(f"✓ {name} validation passed")
                    
            except Exception as e:
                success = False
                self.errors.append(f"{name} validation error: {e}")
                logger.error(f"✗ {name} validation error: {e}")
        
        return success, self.errors, self.warnings


async def main():
    """Main validation function."""
    validator = SchemaAlignmentValidator()
    success, errors, warnings = await validator.run_validation()
    
    print("\n" + "="*60)
    print("SCHEMA ALIGNMENT VALIDATION RESULTS")
    print("="*60)
    
    if success:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ VALIDATION FAILED")
    
    if errors:
        print(f"\n🚨 ERRORS ({len(errors)}):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if not errors and not warnings:
        print("\n🎉 Schema alignment is perfect!")
    
    print("\n" + "="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)