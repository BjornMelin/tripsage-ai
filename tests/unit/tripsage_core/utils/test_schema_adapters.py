"""
Tests for schema adapters and compatibility utilities.

This module tests the schema adaptation layer that handles mismatches
between database, API, and frontend schemas during the migration period.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

from tripsage_core.utils.schema_adapters import (
    SchemaAdapter,
    MemorySchemaAdapter,
    DatabaseQueryAdapter,
    validate_schema_compatibility,
    log_schema_usage,
)


class TestSchemaAdapter:
    """Test schema adapter functionality."""

    def test_normalize_trip_id_with_int(self):
        """Test trip ID normalization with integer input."""
        result = SchemaAdapter.normalize_trip_id(123)
        assert result == "123"
        assert isinstance(result, str)

    def test_normalize_trip_id_with_string(self):
        """Test trip ID normalization with string input."""
        result = SchemaAdapter.normalize_trip_id("456")
        assert result == "456"
        assert isinstance(result, str)

    def test_is_uuid_valid(self):
        """Test UUID validation with valid UUID."""
        test_uuid = str(uuid.uuid4())
        assert SchemaAdapter.is_uuid(test_uuid) is True

    def test_is_uuid_invalid(self):
        """Test UUID validation with invalid UUID."""
        assert SchemaAdapter.is_uuid("not-a-uuid") is False
        assert SchemaAdapter.is_uuid("123") is False
        assert SchemaAdapter.is_uuid("") is False

    def test_convert_db_trip_to_api_with_uuid(self):
        """Test database to API conversion with UUID."""
        db_trip = {
            'id': 123,
            'uuid_id': str(uuid.uuid4()),
            'name': 'Test Trip',
            'user_id': str(uuid.uuid4()),
            'start_date': '2025-06-01',
            'end_date': '2025-06-10',
            'destination': 'Paris',
            'budget': 1000,
            'travelers': 2,
            'status': 'planning',
            'trip_type': 'leisure',
            'flexibility': {},
            'notes': [],
            'search_metadata': {},
            'visibility': 'private',
            'tags': ['vacation'],
            'preferences': {'budget_flexible': True},
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z',
        }

        result = SchemaAdapter.convert_db_trip_to_api(db_trip)

        assert result['id'] == db_trip['uuid_id']  # Should use UUID
        assert result['title'] == db_trip['name']  # Should map name to title
        assert result['name'] == db_trip['name']   # Should keep name
        assert result['visibility'] == 'private'
        assert result['tags'] == ['vacation']
        assert result['preferences'] == {'budget_flexible': True}

    def test_convert_db_trip_to_api_without_uuid(self):
        """Test database to API conversion without UUID."""
        db_trip = {
            'id': 123,
            'name': 'Test Trip',
            'user_id': str(uuid.uuid4()),
            'start_date': '2025-06-01',
            'end_date': '2025-06-10',
            'destination': 'Paris',
            'budget': 1000,
            'travelers': 2,
            'status': 'planning',
            'trip_type': 'leisure',
        }

        result = SchemaAdapter.convert_db_trip_to_api(db_trip)

        assert result['id'] == '123'  # Should convert BIGINT to string
        assert result['title'] == 'Test Trip'
        assert result['visibility'] == 'private'  # Default value
        assert result['tags'] == []  # Default value
        assert result['preferences'] == {}  # Default value

    def test_convert_api_trip_to_db(self):
        """Test API to database conversion."""
        api_trip = {
            'id': str(uuid.uuid4()),
            'user_id': str(uuid.uuid4()),
            'title': 'API Trip',
            'description': 'Test description',
            'start_date': '2025-06-01',
            'end_date': '2025-06-10',
            'budget': 2000,
            'visibility': 'shared',
            'tags': ['business'],
            'preferences': {'flexible_dates': True},
            'status': 'confirmed',
        }

        result = SchemaAdapter.convert_api_trip_to_db(api_trip)

        assert result['name'] == 'API Trip'  # Should map title to name
        assert result['visibility'] == 'shared'
        assert result['tags'] == ['business']
        assert result['preferences'] == {'flexible_dates': True}
        assert 'title' not in result  # Should not include title in DB format

    def test_ensure_uuid_id_with_existing_uuid(self):
        """Test UUID generation with existing UUID."""
        test_uuid = str(uuid.uuid4())
        record = {'uuid_id': test_uuid, 'id': 123}
        
        result = SchemaAdapter.ensure_uuid_id(record)
        assert result == test_uuid

    def test_ensure_uuid_id_without_uuid(self):
        """Test UUID generation without existing UUID."""
        record = {'id': 123}
        
        result = SchemaAdapter.ensure_uuid_id(record)
        assert SchemaAdapter.is_uuid(result)
        assert result != '123'

    def test_migrate_legacy_preferences_empty(self):
        """Test legacy preferences migration with empty data."""
        result = SchemaAdapter.migrate_legacy_preferences(None)
        assert result == {}

        result = SchemaAdapter.migrate_legacy_preferences({})
        assert result == {}

    def test_migrate_legacy_preferences_with_data(self):
        """Test legacy preferences migration with data."""
        flexibility = {
            'budget_flexibility': 0.2,
            'date_flexibility': 5,
            'accommodation': {'type': 'hotel'},
            'transportation': {'class': 'economy'},
            'activities': ['sightseeing', 'food']
        }

        result = SchemaAdapter.migrate_legacy_preferences(flexibility)

        assert result['budget_flexibility'] == 0.2
        assert result['date_flexibility'] == 5
        assert result['accommodation_preferences'] == {'type': 'hotel'}
        assert result['transportation_preferences'] == {'class': 'economy'}
        assert result['activity_preferences'] == ['sightseeing', 'food']


class TestMemorySchemaAdapter:
    """Test memory schema adapter functionality."""

    def test_create_mem0_collection_data(self):
        """Test Mem0 collection data creation."""
        result = MemorySchemaAdapter.create_mem0_collection_data(
            'test_collection',
            'Test description'
        )

        assert SchemaAdapter.is_uuid(result['id'])
        assert result['name'] == 'test_collection'
        assert result['description'] == 'Test description'
        assert result['metadata']['source'] == 'tripsage'
        assert 'created_at' in result
        assert 'updated_at' in result

    def test_convert_tripsage_memory_to_mem0(self):
        """Test TripSage memory to Mem0 conversion."""
        collection_id = str(uuid.uuid4())
        tripsage_memory = {
            'id': 123,
            'user_id': str(uuid.uuid4()),
            'content': 'User prefers luxury hotels',
            'metadata': {'type': 'preference'},
            'memory_type': 'user_preference',
            'embedding': [0.1, 0.2, 0.3],
            'created_at': '2025-01-01T00:00:00Z',
        }

        result = MemorySchemaAdapter.convert_tripsage_memory_to_mem0(
            tripsage_memory, collection_id
        )

        assert SchemaAdapter.is_uuid(result['id'])
        assert result['collection_id'] == collection_id
        assert result['user_id'] == tripsage_memory['user_id']
        assert result['content'] == tripsage_memory['content']
        assert result['metadata']['original_id'] == 123
        assert result['metadata']['memory_type'] == 'user_preference'
        assert result['metadata']['migrated_from'] == 'tripsage_memories'
        assert result['embedding'] == [0.1, 0.2, 0.3]


class TestDatabaseQueryAdapter:
    """Test database query adapter functionality."""

    def test_build_trip_query_with_uuid(self):
        """Test trip query building with UUID preference."""
        query = DatabaseQueryAdapter.build_trip_query(use_uuid=True)
        
        assert "COALESCE(uuid_id::text, id::text) AS id" in query
        assert "uuid_id" in query
        assert "COALESCE(title, name) AS title" in query
        assert "COALESCE(visibility, 'private') AS visibility" in query

    def test_build_trip_query_without_uuid(self):
        """Test trip query building without UUID preference."""
        query = DatabaseQueryAdapter.build_trip_query(use_uuid=False)
        
        assert "id" in query
        assert "COALESCE(uuid_id::text, id::text) AS id" not in query

    def test_build_trip_filter_where_clause_uuid(self):
        """Test WHERE clause building with UUID."""
        trip_id = str(uuid.uuid4())
        where_clause, params = DatabaseQueryAdapter.build_trip_filter_where_clause(trip_id)
        
        assert "uuid_id = %(trip_id)s" in where_clause
        assert params['trip_id'] == trip_id

    def test_build_trip_filter_where_clause_bigint(self):
        """Test WHERE clause building with BIGINT ID."""
        trip_id = "123"
        where_clause, params = DatabaseQueryAdapter.build_trip_filter_where_clause(trip_id)
        
        assert "id = %(trip_id)s" in where_clause
        assert params['trip_id'] == 123
        assert params['trip_id_str'] == "123"

    def test_build_trip_filter_where_clause_invalid(self):
        """Test WHERE clause building with invalid ID."""
        trip_id = "not-a-valid-id"
        where_clause, params = DatabaseQueryAdapter.build_trip_filter_where_clause(trip_id)
        
        assert "uuid_id::text = %(trip_id)s" in where_clause
        assert params['trip_id'] == trip_id


class TestValidationFunctions:
    """Test validation and utility functions."""

    def test_validate_schema_compatibility_valid(self):
        """Test schema compatibility validation with valid data."""
        db_result = {
            'id': 123,
            'user_id': str(uuid.uuid4()),
            'name': 'Test Trip',
            'start_date': '2025-06-01',
            'end_date': '2025-06-10',
        }

        assert validate_schema_compatibility(db_result) is True

    def test_validate_schema_compatibility_missing_fields(self):
        """Test schema compatibility validation with missing fields."""
        db_result = {
            'id': 123,
            'user_id': str(uuid.uuid4()),
            # Missing name, start_date, end_date
        }

        assert validate_schema_compatibility(db_result) is False

    def test_validate_schema_compatibility_null_fields(self):
        """Test schema compatibility validation with null fields."""
        db_result = {
            'id': 123,
            'user_id': None,  # Null required field
            'name': 'Test Trip',
            'start_date': '2025-06-01',
            'end_date': '2025-06-10',
        }

        assert validate_schema_compatibility(db_result) is False

    @patch('tripsage_core.utils.schema_adapters.logger')
    def test_log_schema_usage(self, mock_logger):
        """Test schema usage logging."""
        log_schema_usage(
            'test_operation',
            'uuid',
            {'field1': 'value1', 'field2': 'value2'}
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        assert 'Schema adapter usage' in call_args[0][0]
        extra = call_args[1]['extra']
        assert extra['operation'] == 'test_operation'
        assert extra['id_type'] == 'uuid'
        assert extra['field_mappings'] == {'field1': 'value1', 'field2': 'value2'}
        assert extra['migration_stage'] == 'active'


@pytest.fixture
def sample_db_trip():
    """Sample database trip record."""
    return {
        'id': 123,
        'uuid_id': str(uuid.uuid4()),
        'user_id': str(uuid.uuid4()),
        'name': 'Sample Trip',
        'start_date': '2025-06-01',
        'end_date': '2025-06-10',
        'destination': 'Tokyo',
        'budget': 3000,
        'travelers': 2,
        'status': 'planning',
        'trip_type': 'leisure',
        'flexibility': {'budget_flexibility': 0.1},
        'notes': ['Bring camera'],
        'search_metadata': {'source': 'manual'},
        'visibility': 'private',
        'tags': ['japan', 'culture'],
        'preferences': {'accommodation': 'hotel'},
        'created_at': '2025-01-01T00:00:00Z',
        'updated_at': '2025-01-01T12:00:00Z',
    }


@pytest.fixture
def sample_api_trip():
    """Sample API trip record."""
    return {
        'id': str(uuid.uuid4()),
        'user_id': str(uuid.uuid4()),
        'title': 'API Sample Trip',
        'description': 'A trip created via API',
        'start_date': '2025-07-01',
        'end_date': '2025-07-14',
        'destinations': [
            {'name': 'London', 'country': 'UK'},
            {'name': 'Paris', 'country': 'France'}
        ],
        'budget': {'total_budget': 4000, 'currency': 'USD'},
        'visibility': 'shared',
        'tags': ['europe', 'history'],
        'preferences': {'transportation': 'train'},
        'status': 'confirmed',
    }


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple adapters."""

    def test_full_trip_conversion_cycle(self, sample_db_trip, sample_api_trip):
        """Test full conversion cycle: DB -> API -> DB."""
        # Convert DB to API
        api_format = SchemaAdapter.convert_db_trip_to_api(sample_db_trip)
        
        # Verify API format
        assert api_format['title'] == sample_db_trip['name']
        assert api_format['visibility'] == sample_db_trip['visibility']
        
        # Convert back to DB format
        db_format = SchemaAdapter.convert_api_trip_to_db(api_format)
        
        # Verify DB format
        assert db_format['name'] == sample_db_trip['name']
        assert db_format['visibility'] == sample_db_trip['visibility']
        assert 'title' not in db_format

    def test_uuid_migration_simulation(self, sample_db_trip):
        """Test UUID migration simulation."""
        # Start with BIGINT-only trip
        bigint_trip = sample_db_trip.copy()
        del bigint_trip['uuid_id']
        
        # Ensure UUID assignment
        new_uuid = SchemaAdapter.ensure_uuid_id(bigint_trip)
        assert SchemaAdapter.is_uuid(new_uuid)
        
        # Simulate adding UUID to record
        bigint_trip['uuid_id'] = new_uuid
        
        # Convert to API format (should use UUID)
        api_format = SchemaAdapter.convert_db_trip_to_api(bigint_trip)
        assert api_format['id'] == new_uuid

    def test_legacy_data_handling(self):
        """Test handling of legacy data with missing fields."""
        legacy_trip = {
            'id': 456,
            'name': 'Legacy Trip',
            'user_id': str(uuid.uuid4()),
            'start_date': '2024-01-01',
            'end_date': '2024-01-07',
            'destination': 'Legacy Destination',
            'budget': 1500,
            'travelers': 1,
            'status': 'completed',
            'trip_type': 'business',
            # Missing: visibility, tags, preferences, flexibility, etc.
        }

        # Should handle missing fields gracefully
        api_format = SchemaAdapter.convert_db_trip_to_api(legacy_trip)
        
        assert api_format['id'] == '456'
        assert api_format['title'] == 'Legacy Trip'
        assert api_format['visibility'] == 'private'  # Default
        assert api_format['tags'] == []  # Default
        assert api_format['preferences'] == {}  # Default

    def test_memory_migration_integration(self):
        """Test memory system migration integration."""
        # Create collection
        collection_data = MemorySchemaAdapter.create_mem0_collection_data(
            'test_migration',
            'Test migration collection'
        )
        
        # Create legacy memory
        legacy_memory = {
            'id': 789,
            'user_id': str(uuid.uuid4()),
            'content': 'User likes Japanese cuisine',
            'metadata': {'confidence': 0.9},
            'memory_type': 'user_preference',
            'embedding': [0.1] * 1536,  # 1536-dimensional embedding
            'created_at': '2024-12-01T00:00:00Z',
        }
        
        # Convert to Mem0 format
        mem0_memory = MemorySchemaAdapter.convert_tripsage_memory_to_mem0(
            legacy_memory,
            collection_data['id']
        )
        
        # Verify conversion
        assert mem0_memory['collection_id'] == collection_data['id']
        assert mem0_memory['content'] == legacy_memory['content']
        assert mem0_memory['metadata']['original_id'] == 789
        assert mem0_memory['metadata']['memory_type'] == 'user_preference'
        assert len(mem0_memory['embedding']) == 1536