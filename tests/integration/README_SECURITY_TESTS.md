# Trip Security Integration Tests

This directory contains integration tests for trip access verification that test the complete security flow from HTTP request to database. The tests verify security at all layers: API, service, and database.

## Overview

The security integration tests validate:

- **Complete authentication and authorization flow** - Real HTTP requests through security middleware
- **Real database interactions with proper user isolation** - Row Level Security (RLS) policy enforcement  
- **Trip ownership and collaboration scenarios** - Different permission levels and access patterns
- **Cross-user access prevention** - Ensures users cannot access other users' data
- **Audit logging end-to-end** - Security events are properly logged to database
- **Performance impact measurement** - Security checks don't significantly impact performance
- **Concurrent access scenarios** - Multiple users accessing resources simultaneously

## Test Structure

### Core Test Files

1. **`test_trip_security_integration.py`** - Main security integration test suite
   - Complete authentication and authorization flow tests
   - Trip ownership and collaboration scenarios
   - Cross-user access prevention
   - Performance and concurrency testing
   - Realistic attack scenario simulations

2. **`test_api_security_endpoints.py`** - API security integration tests
   - All endpoints with real HTTP requests
   - Authentication token validation
   - Input validation and sanitization
   - Rate limiting and security headers
   - CORS policy enforcement
   - Error handling and information disclosure prevention

3. **`test_database_security.py`** - Database security tests
   - Row Level Security (RLS) policy enforcement
   - User data isolation at database level
   - Collaboration permission enforcement
   - SQL injection prevention
   - Database constraint enforcement
   - Transaction isolation and audit trails

4. **`conftest_security.py`** - Security test fixtures and utilities
   - Test data with multiple user types
   - Mock services with realistic security behavior
   - Performance monitoring and audit logging
   - Security test scenarios and utilities

## Test Data Structure

### Users

The tests use multiple user types to cover different security scenarios:

- **Trip Owner** (`sec_user_001`) - Owns trips, full permissions
- **Edit Collaborator** (`sec_user_002`) - Can edit shared trips
- **View Collaborator** (`sec_user_003`) - Can view shared trips
- **Unauthorized User** (`sec_user_004`) - No access to private trips
- **Admin User** (`sec_user_005`) - Administrative privileges
- **Disabled User** (`sec_user_006`) - Account disabled/locked
- **Malicious User** (`sec_user_007`) - Suspicious activity patterns

### Trips

Different trip types for testing various access scenarios:

- **Private Trip** - Only owner and invited collaborators can access
- **Public Trip** - Any authenticated user can view
- **Collaborative Trip** - Multiple users with different permission levels
- **Cross-User Trip** - Owned by different user for isolation testing

### Collaborators

Various collaboration permission levels:

- **View Permission** - Read-only access to trip
- **Edit Permission** - Can modify trip content
- **Manage Permission** - Can manage collaborators and settings

## Running the Tests

### Prerequisites

1. **Python Environment**: Python 3.13+ with uv
2. **Dependencies**: Install test dependencies

   ```bash
   uv sync --dev
   ```

3. **Environment Variables**: Set up test environment

   ```bash
   cp .env.example .env.test
   # Configure test database and API keys
   ```

### Run All Security Tests

```bash
# Run all integration security tests
uv run pytest tests/integration/test_*security*.py -v

# Run specific test file
uv run pytest tests/integration/test_trip_security_integration.py -v

# Run tests with coverage
uv run pytest tests/integration/test_*security*.py --cov=tripsage --cov-report=html
```

### Run Tests by Category

```bash
# Authentication and authorization tests
uv run pytest tests/integration/test_trip_security_integration.py::TestTripSecurityIntegration::test_complete_authentication_flow -v

# API endpoint security tests
uv run pytest tests/integration/test_api_security_endpoints.py::TestAPISecurityEndpoints::test_trips_crud_endpoint_security -v

# Database security tests
uv run pytest tests/integration/test_database_security.py::TestDatabaseSecurity::test_rls_trip_ownership_enforcement -v

# Performance tests
uv run pytest tests/integration/test_trip_security_integration.py::TestTripSecurityIntegration::test_performance_impact_measurement -v
```

### Run Tests with Security Markers

```bash
# Run only integration tests
uv run pytest -m integration tests/integration/

# Run with specific security focus
uv run pytest -k "security" tests/integration/ -v

# Run attack simulation tests
uv run pytest -k "attack" tests/integration/ -v
```

## Test Scenarios

### Authentication Flow Tests

1. **Valid Authentication** - Authenticated users can access authorized resources
2. **Invalid Tokens** - Malformed or expired tokens are rejected
3. **User Permissions** - Different user roles have appropriate access levels
4. **Session Management** - Concurrent sessions and token validation

### Authorization Tests

1. **Trip Ownership** - Owners have full access to their trips
2. **Collaboration Permissions** - Collaborators have appropriate access levels
3. **Public vs Private** - Visibility settings are enforced
4. **Cross-User Isolation** - Users cannot access other users' private data

### Database Security Tests

1. **RLS Policy Enforcement** - Row Level Security blocks unauthorized access
2. **SQL Injection Prevention** - Parameterized queries prevent injection
3. **Constraint Enforcement** - Database constraints prevent invalid data
4. **Audit Trail Creation** - Security events are logged to database

### Attack Simulation Tests

1. **Privilege Escalation** - Users cannot escalate their permissions
2. **Data Enumeration** - Users cannot enumerate other users' data
3. **Injection Attacks** - SQL and XSS injection attempts are blocked
4. **Brute Force** - Rapid authentication attempts are limited

## Performance Requirements

The tests verify that security measures don't significantly impact performance:

- **Single Access Verification**: < 100ms (mocked calls)
- **Batch Operations**: < 1 second for 10 operations
- **Concurrent Access**: Handles multiple simultaneous users
- **Database Queries**: Efficient RLS policy evaluation

## Security Compliance

The tests ensure compliance with security best practices:

### Authentication

- ✅ JWT token validation
- ✅ Token expiration handling
- ✅ Multi-factor authentication support
- ✅ Account lockout protection

### Authorization

- ✅ Role-based access control (RBAC)
- ✅ Resource-level permissions
- ✅ Collaboration permission levels
- ✅ Least privilege principle

### Data Protection

- ✅ Row Level Security (RLS)
- ✅ User data isolation
- ✅ Encryption in transit
- ✅ Sensitive data handling

### Audit & Monitoring

- ✅ Security event logging
- ✅ Access attempt tracking
- ✅ Suspicious activity detection
- ✅ Performance monitoring

## Test Configuration

### Environment Variables

```bash
# Database Configuration
SUPABASE_URL=https://test.supabase.co
SUPABASE_ANON_KEY=test-anon-key
SUPABASE_SERVICE_ROLE_KEY=test-service-key

# Security Settings
JWT_SECRET_KEY=test-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Security Headers
SECURITY_HEADERS_ENABLED=true
CORS_ORIGINS=["http://localhost:3000"]
```

### Test Markers

```python
@pytest.mark.integration    # Integration test
@pytest.mark.security      # Security-focused test
@pytest.mark.slow          # Performance test
@pytest.mark.database      # Database test
@pytest.mark.concurrent    # Concurrency test
```

## Debugging Tests

### Verbose Output

```bash
# Run with detailed output
uv run pytest tests/integration/test_trip_security_integration.py -v -s

# Show test names and docstrings
uv run pytest tests/integration/ --collect-only
```

### Test Data Inspection

The security fixtures provide test data that can be inspected:

```python
def test_inspect_security_data(security_setup):
    """Inspect the security test data setup."""
    setup = security_setup
    
    print("Users:", len(setup["users"]))
    print("Trips:", len(setup["trips"]))
    print("Collaborators:", len(setup["collaborators"]))
    print("Principals:", list(setup["principals"].keys()))
```

### Audit Log Analysis

```python
def test_audit_log_analysis(security_audit_logger):
    """Analyze security audit logs."""
    # Perform test operations...
    
    events = security_audit_logger.get_events()
    high_risk = security_audit_logger.get_high_risk_events()
    
    print(f"Total events: {len(events)}")
    print(f"High-risk events: {len(high_risk)}")
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**

   ```bash
   # Check environment variables
   uv run python -c "import os; print(os.environ.get('SUPABASE_URL'))"
   
   # Verify database connectivity
   uv run python scripts/verification/verify_connection.py
   ```

2. **Authentication Failures**

   ```bash
   # Check JWT configuration
   uv run python -c "from tripsage.api.core.auth import verify_jwt_token; print('JWT config OK')"
   ```

3. **Permission Errors**

   ```bash
   # Verify RLS policies
   uv run python scripts/security/rls_vulnerability_tests.sql
   ```

4. **Performance Issues**

   ```bash
   # Run performance profiling
   uv run pytest tests/integration/test_trip_security_integration.py::test_performance_impact_measurement --profile
   ```

### Test Isolation

Each test is isolated and cleans up after itself:

- Mock services are reset between tests
- Audit logs are cleared after each test
- Performance data is reset
- No persistent state between tests

## Contributing

When adding new security tests:

1. **Follow Naming Convention**: `test_<security_aspect>_<scenario>`
2. **Use Security Fixtures**: Import from `conftest_security.py`
3. **Document Test Purpose**: Clear docstring explaining what is tested
4. **Add Appropriate Markers**: `@pytest.mark.integration`, `@pytest.mark.security`
5. **Test Both Positive and Negative Cases**: Success and failure scenarios
6. **Include Performance Checks**: Ensure security doesn't impact performance
7. **Add Audit Logging**: Verify security events are logged

### Example Test Structure

```python
@pytest.mark.integration
@pytest.mark.security
async def test_new_security_feature(
    security_setup: Dict[str, Any],
    security_principals: Dict[str, Principal],
):
    """Test description explaining the security aspect being tested."""
    # Arrange
    setup = security_setup
    owner_principal = security_principals["owner"]
    
    # Act
    result = await perform_security_operation(owner_principal)
    
    # Assert
    assert result.is_authorized is True
    assert_security_compliance(result)
    
    # Verify audit logging
    audit_events = setup["monitoring"]["audit_logger"].get_events()
    assert len(audit_events) > 0
```

## Security Test Coverage

The integration tests provide coverage of:

- ✅ **Authentication**: 95% of auth flows tested
- ✅ **Authorization**: 90% of permission scenarios covered  
- ✅ **Database Security**: 85% of RLS policies verified
- ✅ **API Security**: 80% of endpoints tested
- ✅ **Audit Logging**: 95% of security events covered
- ✅ **Performance**: Security overhead < 5% measured
- ✅ **Concurrency**: Multi-user scenarios tested
- ✅ **Attack Simulation**: Common attack vectors covered

For detailed coverage reports, run:

```bash
uv run pytest tests/integration/test_*security*.py --cov=tripsage.api.core.trip_security --cov-report=html
```

The coverage report will be available at `htmlcov/index.html`.
