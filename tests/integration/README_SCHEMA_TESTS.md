# Supabase Schema Integration Tests

## Overview

This directory contains comprehensive integration tests for the enhanced Supabase schema with collaboration features. The test suite validates RLS policies, foreign key constraints, database functions, performance optimization, and multi-user collaboration workflows.

## Test Architecture

### Core Test Files

```
tests/integration/
├── test_supabase_collaboration_schema.py     # Main integration test suite
├── conftest_supabase_schema.py               # Test fixtures and configuration
├── test_schema_runner.py                     # Test orchestration and reporting
└── README_SCHEMA_TESTS.md                   # This documentation

tests/performance/
└── test_collaboration_performance.py         # Performance-focused tests
```

### Test Categories

#### 1. RLS Policy Validation (`TestRLSPolicyValidation`)
- **Purpose**: Validate Row Level Security policies for collaborative access
- **Coverage**: 
  - Collaborative trip access policies
  - Permission level inheritance
  - View-only permission restrictions
  - Cross-user data isolation
  - Memory system user isolation

#### 2. Foreign Key Constraints (`TestForeignKeyConstraints`)
- **Purpose**: Test database integrity and constraint enforcement
- **Coverage**:
  - Memory-user foreign key relationships
  - Cascade delete behavior
  - Trip collaborator referential integrity
  - Constraint violation handling

#### 3. Index Performance (`TestIndexPerformance`)
- **Purpose**: Validate query optimization and indexing strategy
- **Coverage**:
  - Collaboration index existence and efficiency
  - Vector index optimization for memory search
  - Performance benchmarks for large datasets

#### 4. Database Functions (`TestDatabaseFunctions`)
- **Purpose**: Test correctness of stored procedures and functions
- **Coverage**:
  - `get_user_accessible_trips()` function
  - `check_trip_permission()` function
  - Memory search functions with collaboration context
  - Bulk operations and maintenance functions

#### 5. Collaboration Workflows (`TestCollaborationWorkflows`)
- **Purpose**: End-to-end testing of collaboration features
- **Coverage**:
  - Add collaborator workflow
  - Permission update workflow
  - Remove collaborator workflow
  - Complex permission inheritance chains

#### 6. Multi-User Scenarios (`TestMultiUserScenarios`)
- **Purpose**: Test complex scenarios with multiple users and permission levels
- **Coverage**:
  - Multiple permission levels on single trip
  - Concurrent access scenarios
  - Permission inheritance chains
  - Bulk collaboration operations

#### 7. Security Isolation (`TestSecurityIsolation`)
- **Purpose**: Validate security boundaries and prevent unauthorized access
- **Coverage**:
  - Unauthorized collaboration access prevention
  - Privilege escalation prevention
  - Data leakage prevention between users
  - Anonymous user restrictions

#### 8. Performance Optimization (`TestPerformanceOptimization`)
- **Purpose**: Validate performance under various load conditions
- **Coverage**:
  - Collaboration query performance benchmarks
  - Memory search performance with user filtering
  - Concurrent access performance
  - Large dataset handling

#### 9. Migration Compatibility (`TestMigrationCompatibility`)
- **Purpose**: Ensure safe database migrations and rollback capabilities
- **Coverage**:
  - Transaction safety validation
  - Rollback instruction verification
  - Data preservation during migrations
  - Migration validation blocks

## Performance Test Suite

### Collaboration Performance Tests (`CollaborationPerformanceTestSuite`)

Located in `tests/performance/test_collaboration_performance.py`, these tests focus on:

- **Scale Testing**: Performance with large datasets (50+ users, 100+ trips)
- **Concurrent Access**: Multi-user concurrent operations
- **Query Optimization**: Index efficiency and query performance
- **Memory Operations**: Vector search performance with RLS filtering
- **Bulk Operations**: Large-scale permission updates and data operations

### Performance Thresholds

```python
PERFORMANCE_THRESHOLDS = {
    "collaboration_query": 0.5,    # seconds
    "memory_search": 2.0,          # seconds  
    "permission_check": 0.1,       # seconds
    "bulk_operation": 2.0,         # seconds
    "concurrent_access": 10.0      # seconds total
}
```

## Test Configuration

### MockSupabaseClient

The test suite uses a sophisticated mock client that simulates:

- **RLS Policy Enforcement**: Filters data based on current user context
- **Foreign Key Constraints**: Validates referential integrity
- **User Authentication**: Simulates `auth.uid()` function behavior
- **Transaction Safety**: Validates constraint violations and rollbacks

### Test Data Generation

```python
# Large dataset for performance testing
LARGE_DATASET = {
    "users": 50,           # Test users with different roles
    "trips": 100,          # Trips with varying collaboration patterns  
    "memories_per_user": 20,   # Memory records for vector search testing
    "collaborators_per_trip": 5  # Average collaborators per trip
}
```

## Running the Tests

### Quick Test Suite

```bash
# Run essential schema validation tests
python tests/integration/test_schema_runner.py --quick

# Run specific test categories
python tests/integration/test_schema_runner.py --test-types schema_validation rls_policies
```

### Full Integration Test Suite

```bash
# Run all integration tests
python tests/integration/test_schema_runner.py

# Run with verbose output
python tests/integration/test_schema_runner.py --verbose
```

### Performance Tests Only

```bash
# Run performance-focused tests
python tests/integration/test_schema_runner.py --performance-only

# Run with pytest directly
pytest tests/performance/test_collaboration_performance.py -v -m performance
```

### Individual Test Modules

```bash
# Run RLS policy tests
pytest tests/integration/test_supabase_collaboration_schema.py::TestRLSPolicyValidation -v

# Run collaboration workflow tests
pytest tests/integration/test_supabase_collaboration_schema.py::TestCollaborationWorkflows -v

# Run performance tests with timing
pytest tests/performance/test_collaboration_performance.py --durations=10
```

## Test Reports

### Automated Report Generation

The test runner generates comprehensive reports:

```
test_reports/
└── schema_integration_test_report_20250611_143022.json
```

Report contents:
- **Metadata**: Test execution details, configuration, environment
- **Results**: Detailed results for each test suite  
- **Analysis**: Performance metrics, failure patterns, recommendations
- **Environment**: Python version, dependencies, system info

### Report Analysis

```json
{
  "analysis": {
    "summary": {
      "total_tests": 89,
      "total_passed": 87,
      "total_failed": 2,
      "success_rate": 97.8
    },
    "performance": {
      "slow_tests": [],
      "average_test_duration": 0.45
    },
    "recommendations": [
      "Address 2 failing test suites before production deployment",
      "All critical schema validations passing"
    ]
  }
}
```

## Database Fixtures and Cleanup

### Test Data Management

```python
@pytest.fixture
async def clean_database(mock_db_service):
    """Provides clean database state with automatic cleanup."""
    await cleanup_test_data(mock_db_service)
    yield mock_db_service
    await cleanup_test_data(mock_db_service)

@pytest.fixture
async def sample_collaboration_data(test_users):
    """Creates realistic collaboration test scenarios."""
    # Setup sample trips with different permission levels
    # Automatically cleaned up after test completion
```

### Isolation Guarantees

- **Test Isolation**: Each test runs with clean database state
- **User Isolation**: Test users cannot access each other's data
- **Transaction Safety**: All operations wrapped in test transactions
- **Cleanup Automation**: Automatic cleanup prevents test data pollution

## Schema Validation

### Pre-Test Validation

Before running tests, the system validates:

```python
REQUIRED_SCHEMA_FILES = [
    "supabase/schemas/05_policies.sql",     # RLS policies
    "supabase/schemas/02_indexes.sql",      # Performance indexes  
    "supabase/schemas/03_functions.sql",    # Database functions
    "supabase/schemas/01_tables.sql"        # Table definitions
]

REQUIRED_MIGRATION_FILES = [
    "supabase/migrations/20250610_01_fix_user_id_constraints.sql",
    "supabase/migrations/20250609_02_consolidated_production_schema.sql"
]
```

### Schema Component Validation

```python
# Validate RLS policies
assert "ENABLE ROW LEVEL SECURITY" in policies_sql
assert "auth.uid() = user_id" in policies_sql

# Validate performance indexes
assert "idx_trip_collaborators_user_trip" in indexes_sql
assert "vector_cosine_ops" in indexes_sql

# Validate database functions
assert "get_user_accessible_trips" in functions_sql
assert "check_trip_permission" in functions_sql
```

## Continuous Integration Integration

### GitHub Actions Configuration

```yaml
name: Schema Integration Tests
on: [push, pull_request]

jobs:
  schema-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Run schema validation tests
        run: |
          python tests/integration/test_schema_runner.py --quick
      
      - name: Run full integration tests
        run: |
          python tests/integration/test_schema_runner.py
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
      
      - name: Upload test reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test_reports/
        if: always()
```

### Test Markers

```python
# Performance tests (may be slow)
@pytest.mark.performance
@pytest.mark.slow

# Integration tests requiring database
@pytest.mark.integration  
@pytest.mark.database

# Security-focused tests
@pytest.mark.security

# Schema validation tests
@pytest.mark.schema
```

## Troubleshooting

### Common Issues

1. **Schema File Not Found**
   ```
   FileNotFoundError: Required schema file not found: 05_policies.sql
   ```
   **Solution**: Ensure all schema files exist in `supabase/schemas/`

2. **Performance Test Failures**
   ```
   AssertionError: Collaboration query took 0.75s, exceeding threshold of 0.5s
   ```
   **Solution**: Review query optimization and index usage

3. **RLS Policy Violations**
   ```
   Exception: RLS policy violation: insufficient permissions
   ```
   **Solution**: Verify RLS policies allow intended access patterns

### Debug Mode

```bash
# Run tests with detailed debugging
python tests/integration/test_schema_runner.py --verbose

# Run single test with debugging
pytest tests/integration/test_supabase_collaboration_schema.py::TestRLSPolicyValidation::test_collaborative_trip_access_policies -vvv -s
```

### Performance Profiling

```bash
# Profile test performance
pytest tests/performance/test_collaboration_performance.py --profile-svg

# Measure test coverage
pytest tests/integration/ --cov=tripsage_core --cov-report=html
```

## Best Practices

### Writing New Tests

1. **Use Descriptive Names**: Test names should clearly describe the scenario
2. **Follow AAA Pattern**: Arrange, Act, Assert
3. **Mock External Dependencies**: Use MockSupabaseClient for database operations
4. **Test Edge Cases**: Include boundary conditions and error scenarios
5. **Performance Awareness**: Set appropriate performance thresholds

### Test Data Management

```python
# Good: Use fixtures for consistent test data
@pytest.fixture
def collaboration_scenario(test_users):
    owner = test_users['owner']
    trip = TestTrip(owner, "Test Collaboration")
    trip.add_collaborator(test_users['editor'], "edit")
    return trip

# Good: Clean isolation between tests  
async def test_permission_update(collaboration_scenario, clean_database):
    # Test operates on clean database state
    pass
```

### Performance Test Guidelines

```python
# Good: Set realistic thresholds
assert_performance_threshold(duration, 0.5, "Collaboration query")

# Good: Test with representative data sizes
large_dataset = create_large_dataset(users=50, trips=100)

# Good: Monitor resource usage
performance_tracker.track_collaboration_query("concurrent_access", duration, user_count)
```

## Contributing

When adding new schema features:

1. **Add Corresponding Tests**: New schema components require integration tests
2. **Update Performance Tests**: New queries should be performance tested
3. **Document Changes**: Update this README with new test categories
4. **Validate Security**: Ensure RLS policies are properly tested
5. **Check Migration Safety**: Add migration compatibility tests

### Test Review Checklist

- [ ] Tests cover happy path and error scenarios
- [ ] Performance thresholds are realistic and measurable
- [ ] Security boundaries are properly validated
- [ ] Migration safety is ensured
- [ ] Documentation is updated
- [ ] CI/CD integration works correctly

---

This test suite ensures the Supabase schema is production-ready with robust collaboration features, proper security isolation, and optimal performance characteristics.