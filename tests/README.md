# TripSage Test Suite

This directory contains the organized test suite for TripSage, restructured for better maintainability and clarity.

## Directory Structure

### `unit/`

Unit tests for individual components and modules:

- `unit/api/` - API endpoint unit tests (auth, health, keys, trips, chat)
- `unit/agents/` - Agent class unit tests (base, chat, flight, travel planning)
- `unit/services/` - Service layer unit tests (memory, chat orchestration, error handling)
- `unit/models/` - Data model unit tests (database models)
- `unit/tools/` - Tool function unit tests (memory, weather, planning, browser)
- `unit/utils/` - Utility function unit tests (decorators, settings, cache, storage)

### `integration/`

Integration tests that test component interactions:

- `integration/api/` - API integration tests (BYOK, endpoints, memory integration)
- `integration/database/` - Database integration tests (migrations, connections)
- `integration/memory/` - Memory system integration tests (workflows, system integration)
- `integration/agents/` - Agent integration tests (handoffs, LangGraph migration, travel flows)

### `e2e/`

End-to-end tests that simulate complete user workflows:

- Complete chat authentication flows
- Chat session management
- Full API workflows

### `performance/`

Performance and benchmark tests:

- Memory system performance tests
- Migration performance benchmarks
- SDK migration structure tests

### `security/`

Security and compliance tests:

- Memory system security tests
- Data isolation validation
- GDPR compliance tests

### `deprecate/`

Deprecated tests that are no longer relevant due to:

- MCP to SDK migration (per docs/REFACTOR/API_INTEGRATION/)
- Service deprecations (Firecrawl → Crawl4AI)
- Obsolete test variants and duplicates

## Running Tests

### All Tests

```bash
uv run pytest
```

### By Category

```bash
# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# E2E tests only
uv run pytest tests/e2e/

# Performance tests
uv run pytest tests/performance/

# Security tests
uv run pytest tests/security/
```

### By Component

```bash
# Memory system tests
uv run pytest tests/unit/services/test_memory_service*.py tests/integration/memory/

# API tests
uv run pytest tests/unit/api/ tests/integration/api/

# Agent tests
uv run pytest tests/unit/agents/ tests/integration/agents/
```

## Test Coverage

Target: ≥90% coverage across all test categories.

Current coverage can be checked with:

```bash
uv run pytest --cov=tripsage --cov-report=html
```

## Migration from Old Structure

The following changes were made to improve organization:

1. **Removed deprecated MCP wrapper tests** - These are no longer needed as we migrate to direct SDK integrations
2. **Consolidated duplicate tests** - Removed multiple chat agent test variants, keeping only the main ones
3. **Separated concerns** - Unit, integration, and e2e tests are now clearly separated
4. **Removed obsolete services** - Firecrawl, cached websearch, and other deprecated service tests
5. **Better categorization** - Tests are now organized by what they test rather than where the code lives

## Deprecated Tests

The following types of tests have been moved to `deprecate/`:

### MCP-Related Tests (per API_INTEGRATION migration docs)

- MCP wrapper tests for services being migrated to direct SDKs
- MCP abstraction layer tests
- MCP configuration tests
- Phase 3 MCP bridge tests

### Service Migration Tests (per migration roadmap)

- Firecrawl tests (deprecated in favor of Crawl4AI)
- Cached websearch tests (deprecated)
- Redis migration tests (completed)
- Duffel HTTP client tests (migrated to direct SDK)

### Obsolete Test Variants

- Multiple chat agent test variants (demo, isolated, phase5, proper, simple, working)
- Basic decorator tests (replaced by unit tests)
- Flight search decorator tests (migrated)
- Calendar decorator tests (migrated)

### Legacy Integration Tests

- Phase 3 orchestration tests (completed)
- Missing operations tests (resolved)
- Final verification tests (completed)
- Simple functionality tests (replaced by organized unit tests)

## Adding New Tests

When adding new tests:

1. **Unit tests** go in `unit/{component}/` - test individual functions/classes in isolation
2. **Integration tests** go in `integration/{system}/` - test component interactions
3. **E2E tests** go in `e2e/` - test complete user workflows
4. **Performance tests** go in `performance/` - benchmark and load tests
5. **Security tests** go in `security/` - security and compliance validation

## Test Naming Convention

- Unit tests: `test_{module_name}.py`
- Integration tests: `test_{system}_integration.py`
- E2E tests: `test_{workflow}_flow.py`
- Performance tests: `test_{component}_performance.py`
- Security tests: `test_{component}_security.py`

## Dependencies

All test dependencies are defined in:

- `conftest.py` files in each directory for shared fixtures
- `requirements.txt` for external test dependencies
- Test configuration in `pytest.ini`

## Writing Tests

### Unit Tests

Focus on testing individual functions and classes in isolation:

```python
# unit/services/test_memory_service.py
def test_memory_extraction():
    """Test memory extraction from conversation."""
    service = MemoryService()
    result = service.extract_memory("I love visiting Paris")
    assert "Paris" in result.entities
```

### Integration Tests

Test component interactions and data flow:

```python
# integration/memory/test_memory_workflow.py
async def test_complete_memory_workflow():
    """Test complete memory storage and retrieval workflow."""
    # Test memory storage → search → retrieval
```

### E2E Tests

Test complete user journeys:

```python
# e2e/test_chat_auth_flow.py
async def test_authenticated_chat_session():
    """Test complete authenticated chat session."""
    # Test login → chat → memory storage → response
```

## Test Organization Benefits

This reorganization provides:

1. **Clear separation of concerns** - Unit vs integration vs e2e
2. **Better discoverability** - Tests organized by what they test
3. **Reduced maintenance** - Deprecated tests clearly separated
4. **Improved CI/CD** - Run test categories independently
5. **Better coverage tracking** - Coverage per component type
6. **Cleaner structure** - No more scattered test files
