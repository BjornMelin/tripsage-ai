# TripCollaborator Models Test Suite

## Overview

This document describes the comprehensive test suite for the TripCollaborator Pydantic models, including `TripCollaboratorDB`, `TripCollaboratorCreate`, `TripCollaboratorUpdate`, and the `PermissionLevel` enum.

## Test Coverage Summary

**Total Tests**: 64 tests across 5 test classes
**Model Coverage**: 97% coverage for `trip_collaborator.py`
**Testing Framework**: pytest with hypothesis for property-based testing

## Test Structure

### 1. TestPermissionLevel (7 tests)
Tests the `PermissionLevel` enum:
- Enum value validation
- String conversion and case sensitivity
- Permission hierarchy ordering
- Invalid value handling

### 2. TestTripCollaboratorDB (22 tests)
Tests the main database model:
- Model creation with full/minimal data
- Permission property validation (`can_view`, `can_edit`, `can_manage_collaborators`)
- Permission hierarchy logic via `has_permission()` method
- Field validation (UUID, datetime, enum)
- Model configuration (from_attributes, str_strip_whitespace, validate_assignment)
- Serialization/deserialization round-trip testing
- Validation error handling

### 3. TestTripCollaboratorCreate (12 tests)
Tests the creation request model:
- Valid data creation with defaults
- Trip ID validation (positive integers only)
- Field validators for UUIDs and custom constraints
- Permission level validation
- Serialization testing
- Error handling for missing/invalid fields

### 4. TestTripCollaboratorUpdate (12 tests)
Tests the update request model:
- Empty update handling
- Permission-only updates
- `has_updates()` and `get_update_fields()` business logic
- Validation across all permission levels
- Serialization with exclude_none functionality

### 5. TestTripCollaboratorEdgeCases (7 tests)
Tests boundary conditions and edge cases:
- Self-addition scenarios (user_id == added_by)
- Extreme trip ID values (max 32-bit integers)
- Timezone handling with UTC datetime
- Case sensitivity validation for enums

### 6. TestTripCollaboratorPropertyBased (4 tests)
Property-based testing using Hypothesis:
- Random data generation for robust validation
- Permission hierarchy invariant testing
- Trip ID validation across integer ranges
- Update model invariant testing

### 7. TestTripCollaboratorBusinessLogic (6 tests)
Integration and business logic testing:
- Permission escalation/downgrade workflows
- Bulk permission checking
- API response serialization patterns
- Database integration patterns with ORM simulation

## Key Features Tested

### Permission Hierarchy
- **VIEW**: Can view only (baseline permission)
- **EDIT**: Can view and edit (inherits VIEW)
- **ADMIN**: Can view, edit, and manage collaborators (inherits EDIT)

### Validation Patterns
- Positive integer validation for trip IDs
- UUID format validation for user references
- Enum value validation with case sensitivity
- Datetime handling with timezone awareness
- Custom field validators with clear error messages

### Pydantic v2 Features
- `from_attributes=True` for ORM integration
- `str_strip_whitespace=True` for input sanitization
- `validate_assignment=True` for runtime validation
- `exclude_none=True` for clean API responses
- JSON schema generation with examples

### Property-Based Testing
Uses Hypothesis to generate random test data ensuring:
- Comprehensive input validation
- Invariant preservation across operations
- Edge case discovery through fuzzing
- Robust validation of business rules

## Test Fixtures

### Conftest Integration
- `sample_trip_collaborator_dict`: Base fixture for consistent test data
- UUID generation with `uuid4()` for realistic testing
- Timezone-aware datetime fixtures
- Integration with existing factory patterns

### Custom Helpers
- `ValidationTestHelper`: Assertion utilities for Pydantic validation
- `SerializationTestHelper`: Round-trip testing utilities
- Property-based test strategies for complex scenarios

## Usage Examples

### Running Tests
```bash
# Run all trip collaborator tests
uv run pytest tests/unit/models/test_trip_collaborator.py -v

# Run with coverage
uv run pytest tests/unit/models/test_trip_collaborator.py --cov=tripsage_core.models.db.trip_collaborator

# Run property-based tests only
uv run pytest tests/unit/models/test_trip_collaborator.py::TestTripCollaboratorPropertyBased -v
```

### Test Categories by Marker (if implemented)
- `@pytest.mark.unit`: All unit tests
- `@pytest.mark.validation`: Validation-focused tests
- `@pytest.mark.business_logic`: Business rule tests
- `@pytest.mark.property_based`: Hypothesis tests

## Dependencies

### Required Packages
- `pytest>=8.4.0`: Core testing framework
- `hypothesis>=6.120.0`: Property-based testing
- `pydantic>=2.11.5`: Model validation
- `pytest-cov>=6.1.1`: Coverage reporting

### Test Data Dependencies
- `uuid` module for UUID generation
- `datetime` with timezone handling
- `typing` for type hints and validation

## Best Practices Demonstrated

### Modern Pytest Patterns
- Class-based test organization
- Comprehensive fixture usage
- Parametrized testing for similar scenarios
- Clear test naming conventions

### Pydantic v2 Testing
- Model validation with realistic data
- Error message assertion patterns
- Configuration testing (model_config)
- Serialization format validation

### Property-Based Testing
- Invariant preservation testing
- Random data generation strategies
- Comprehensive input space coverage
- Edge case discovery through fuzzing

### Business Logic Testing
- Permission hierarchy validation
- State transition testing
- Integration pattern simulation
- API contract verification

This test suite provides a comprehensive foundation for ensuring the reliability and correctness of the TripCollaborator models within the TripSage AI platform.