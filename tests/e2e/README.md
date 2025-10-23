# End-to-End (E2E) Tests

## Overview

This directory contains end-to-end tests that validate complete user workflows and journeys through the TripSage platform. E2E tests simulate real user interactions from start to finish, ensuring all components work together correctly in production-like scenarios.

## Test Structure

```text
e2e/
├── conftest.py               # E2E-specific fixtures and configuration
├── test_auth_flow.py         # Authentication workflow tests
├── test_chat_sessions.py     # Complete chat session tests
├── test_trip_planning_flow.py # Full trip planning journey tests
├── test_collaboration_flow.py # Multi-user collaboration tests
├── test_memory_persistence.py # User memory and personalization tests
└── test_api_workflows.py     # Complete API workflow tests
```

## Prerequisites

### Required Services

- **Database**: PostgreSQL/Supabase instance (test database)
- **Cache**: Redis instance (test cache)
- **AI Services**: OpenAI API access (or mocked)
- **External APIs**: Weather, Maps, Flight APIs (or mocked)

### Environment Setup

```bash
# Required environment variables
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://localhost:6379/1"
export OPENAI_API_KEY="sk-..."
export TEST_USER_EMAIL="test@example.com"
export TEST_USER_PASSWORD="testpassword123"
```

### Test Data

- Pre-seeded test users
- Sample trip data
- Test collaboration scenarios
- Memory test data

## Running Tests

### All E2E Tests

```bash
# Run all E2E tests (may take several minutes)
uv run pytest tests/e2e/

# Run with specific marker
uv run pytest -m e2e

# Run with detailed output
uv run pytest tests/e2e/ -v -s
```

### Specific Workflows

```bash
# Authentication flows only
uv run pytest tests/e2e/test_auth_flow.py

# Chat session tests
uv run pytest tests/e2e/test_chat_sessions.py

# Trip planning workflows
uv run pytest tests/e2e/test_trip_planning_flow.py
```

### Test Environments

```bash
# Run against local environment
uv run pytest tests/e2e/ --env=local

# Run against staging (if configured)
uv run pytest tests/e2e/ --env=staging

# Run with real external services
uv run pytest tests/e2e/ -m "e2e and not mocked"
```

## Key Concepts

### E2E Testing Principles

- **User-Centric**: Tests simulate real user actions and expectations
- **Full Stack**: Tests exercise all layers of the application
- **Realistic Data**: Uses production-like data and scenarios
- **Environment Isolation**: Tests run in isolated test environment
- **Cleanup**: Proper cleanup ensures test independence

### Test Scenarios

- **Complete Workflows**: Start-to-finish user journeys
- **Cross-Component**: Multiple services working together
- **State Persistence**: Data persists across requests/sessions
- **Error Recovery**: System handles failures gracefully
- **Performance**: Acceptable response times under load

## Test Patterns

### Authentication Flow Test

```python
async def test_complete_auth_flow(test_client, test_db):
    """Test complete authentication workflow.
    
    Given: New user registration data
    When: User registers, logs in, and accesses protected resources
    Then: All auth operations succeed with proper tokens
    """
    # Register new user
    register_response = await test_client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User"
    })
    assert register_response.status_code == 201
    
    # Verify email (if applicable)
    # ...
    
    # Login
    login_response = await test_client.post("/api/v1/auth/login", json={
        "email": "newuser@example.com",
        "password": "SecurePass123!"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = await test_client.get("/api/v1/users/me", headers=headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == "newuser@example.com"
```

### Trip Planning Flow Test

```python
async def test_complete_trip_planning(authenticated_client, test_user):
    """Test end-to-end trip planning workflow.
    
    Given: Authenticated user wants to plan a trip
    When: User creates trip, adds destinations, books accommodations
    Then: Complete itinerary is created and accessible
    """
    # Create trip
    trip_response = await authenticated_client.post("/api/v1/trips", json={
        "name": "European Adventure",
        "start_date": "2025-06-01",
        "end_date": "2025-06-15"
    })
    assert trip_response.status_code == 201
    trip_id = trip_response.json()["id"]
    
    # Add destinations
    destinations = ["Paris", "Rome", "Barcelona"]
    for city in destinations:
        dest_response = await authenticated_client.post(
            f"/api/v1/trips/{trip_id}/destinations",
            json={"city": city, "days": 4}
        )
        assert dest_response.status_code == 201
    
    # Search accommodations
    search_response = await authenticated_client.post(
        f"/api/v1/trips/{trip_id}/accommodations/search",
        json={"city": "Paris", "check_in": "2025-06-01", "check_out": "2025-06-05"}
    )
    assert search_response.status_code == 200
    assert len(search_response.json()["results"]) > 0
    
    # Verify complete itinerary
    itinerary_response = await authenticated_client.get(f"/api/v1/trips/{trip_id}")
    assert itinerary_response.status_code == 200
    assert len(itinerary_response.json()["destinations"]) == 3
```

### Chat Session Test

```python
async def test_ai_chat_session(authenticated_client, test_user):
    """Test complete AI chat interaction.
    
    Given: User wants travel recommendations
    When: User has conversation with AI assistant
    Then: AI provides personalized recommendations with memory
    """
    # Start chat session
    session_response = await authenticated_client.post("/api/v1/chat/sessions")
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]
    
    # Send messages
    messages = [
        "I want to plan a romantic trip to Italy",
        "What are the best cities for couples?",
        "Can you recommend restaurants in Rome?"
    ]
    
    for message in messages:
        chat_response = await authenticated_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": message}
        )
        assert chat_response.status_code == 200
        assert "recommendation" in chat_response.json()["response"].lower()
    
    # Verify conversation history
    history_response = await authenticated_client.get(
        f"/api/v1/chat/sessions/{session_id}"
    )
    assert history_response.status_code == 200
    assert len(history_response.json()["messages"]) >= 6  # User + AI messages
```

## Fixtures

E2E-specific fixtures (defined in conftest.py):

| Fixture | Scope | Description |
|---------|-------|-------------|
| `test_client` | function | Async HTTP test client |
| `test_db` | function | Test database connection |
| `test_cache` | function | Test cache connection |
| `test_user` | function | Pre-created test user |
| `authenticated_client` | function | Client with auth headers |
| `sample_trip` | function | Pre-created trip with data |
| `multi_user_scenario` | function | Multiple users for collaboration |

## Test Data Management

### Setup and Teardown

```python
@pytest.fixture
async def test_scenario(test_db):
    """Create test scenario data."""
    # Setup
    user = await create_test_user()
    trip = await create_test_trip(user)
    
    yield {"user": user, "trip": trip}
    
    # Teardown
    await cleanup_test_trip(trip)
    await cleanup_test_user(user)
```

### Data Isolation

- Each test gets fresh data
- No shared state between tests
- Automatic cleanup after tests
- Rollback on test failure

## Coverage

### Workflow Coverage

- ✅ User Registration and Authentication
- ✅ Trip Creation and Management
- ✅ AI Chat Interactions
- ✅ Accommodation Search and Booking
- ✅ User Collaboration
- ✅ Memory and Personalization
- ⏳ Payment Processing (planned)
- ⏳ Email Notifications (planned)

### API Coverage

- Authentication: 100%
- Trips: 95%
- Chat: 90%
- Accommodations: 85%
- Collaboration: 80%

## Common Issues

### 1. Database Connection Errors

**Issue**: `Connection refused` or `Database does not exist`
**Solution**: Ensure test database is running and migrations are applied

### 2. Timeout Errors

**Issue**: Tests timeout waiting for responses
**Solution**: Increase timeout in pytest.ini or use `@pytest.mark.timeout(60)`

### 3. Authentication Failures

**Issue**: `401 Unauthorized` in authenticated requests
**Solution**: Check token generation and header format

### 4. Data Conflicts

**Issue**: `Unique constraint violation` errors
**Solution**: Ensure proper test isolation and cleanup

### 5. External Service Failures

**Issue**: Real API calls failing in tests
**Solution**: Use mocked services or ensure API keys are valid

## Best Practices

### Writing E2E Tests

1. **Think Like a User**: Test from user's perspective
2. **Test Happy Paths**: Ensure primary workflows work
3. **Test Error Scenarios**: Verify graceful error handling
4. **Keep Tests Independent**: No dependencies between tests
5. **Use Realistic Data**: Test with production-like scenarios

### Performance Considerations

- Set appropriate timeouts (default: 30s)
- Use parallel execution carefully
- Mock expensive external calls when possible
- Monitor test execution time

### Debugging E2E Tests

```python
# Add debugging helpers
async def test_workflow_with_debugging(test_client, caplog):
    """Test with enhanced debugging."""
    # Enable debug logging
    caplog.set_level(logging.DEBUG)
    
    # Add checkpoints
    response = await test_client.post("/api/endpoint")
    print(f"Response: {response.status_code}")
    print(f"Body: {response.json()}")
    
    # Check logs
    assert "Expected log message" in caplog.text
```

## Contributing

When adding new E2E tests:

1. **Identify User Journey**: Map complete workflow
2. **Create Test Scenario**: Write test
3. **Handle Edge Cases**: Include error scenarios
4. **Ensure Cleanup**: Proper teardown of test data
5. **Document Workflow**: Add clear docstrings
6. **Test Locally**: Run full suite before pushing

### E2E Test Template

```python
"""E2E test for [workflow name]."""
import pytest

pytestmark = pytest.mark.e2e


class TestWorkflowName:
    """Test suite for [workflow] end-to-end flow."""
    
    async def test_complete_workflow(self, authenticated_client, test_data):
        """Test complete [workflow] from start to finish.
        
        Given: [Initial conditions]
        When: [User actions]
        Then: [Expected outcomes]
        """
        # Step 1: Initial action
        response = await authenticated_client.post(...)
        assert response.status_code == 200
        
        # Step 2: Follow-up action
        # ...
        
        # Verify final state
        # ...
```

## CI/CD Integration

E2E tests in CI/CD pipeline:

```yaml
e2e-tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
    redis:
      image: redis:7
  steps:
    - name: Run E2E tests
      run: |
        uv run pytest tests/e2e/ -v --tb=short
      env:
        DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
        REDIS_URL: redis://localhost:6379
```

## Related Documentation

- [Testing Guide](../TESTING_GUIDE.md) - Testing guide
- [Integration Tests](../integration/README.md) - Component integration tests
- [API Documentation](/docs/api/) - API endpoint reference
- [User Workflows](/docs/workflows/) - Detailed workflow documentation

## Maintenance

E2E tests require regular maintenance:

- **Weekly**: Review failing tests
- **Monthly**: Update test data
- **Quarterly**: Review test coverage
- **Annually**: Refactor test suite

Key maintenance tasks:

- Keep test data current
- Update for API changes
- Optimize slow tests
- Remove obsolete tests
