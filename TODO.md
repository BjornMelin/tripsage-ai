# TripSage Refactoring TODO List

This TODO list outlines refactoring opportunities to simplify the TripSage AI codebase following KISS/DRY/YAGNI/SIMPLE principles. The goal is to eliminate redundancy, improve maintainability, and ensure adherence to project standards.

## Coding Standards Reference

- **Python 3.12** with PEP-8 (88-char lines max)
- Type hints are mandatory
- Run `ruff check --select I --fix .` for import sorting
- Run `ruff check . --fix` and `ruff format .` on touched files
- Files should be ≤350 LoC (hard cap: 500)
- Test coverage target: ≥90%

## High Priority

- [x] **Error Handling Decorator Enhancement**
  - **Target:** `/src/utils/decorators.py`
  - **Goal:** Support both sync and async functions in `with_error_handling`
  - **Tasks:**
    - ✓ Add synchronous function support
    - ✓ Improve type hints using TypeVar
    - ✓ Add comprehensive docstrings and examples
    - ✓ Ensure proper error message formatting
  - **PR:** Completed in #85

- [ ] **Apply Error Handling Decorator to Remaining Agent Tools**
  - **Target:** `/src/agents/flight_search.py`, `/src/agents/accommodations.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - Refactor `flight_search.py` tools to use the decorator
    - Refactor `accommodations.py` tools to use the decorator
    - Create tests to verify error handling

- [ ] **Standardize MCP Client Pattern**
  - **Target:** `/src/mcp/base_mcp_client.py` and implementations
  - **Goal:** Create consistent patterns for all MCP clients
  - **Tasks:**
    - Define standard client factory interfaces
    - Centralize configuration validation logic
    - Implement consistent initialization patterns
    - Standardize error handling approach

- [ ] **Consolidate Dual Storage Pattern**
  - **Target:** `/src/utils/dual_storage.py`
  - **Goal:** Extract common persistence logic to avoid duplication
  - **Tasks:**
    - Create a `DualStorageService` base class
    - Implement standard persistence operations
    - Refactor existing services to use the base class
    - Add proper interface for both Supabase and Memory backends

## Medium Priority

- [ ] **Simplify Tool Registration Logic**
  - **Target:** `/src/agents/base_agent.py`
  - **Goal:** Reduce verbosity in tool registration
  - **Tasks:**
    - Implement a generic `register_tool_group` method
    - Create a more declarative approach to tool registration
    - Add automatic tool discovery in specified modules

- [ ] **Centralize Parameter Validation**
  - **Target:** MCP client implementations
  - **Goal:** Use Pydantic more consistently for validation
  - **Tasks:**
    - Define standard field validators for common patterns
    - Create base model classes for common parameter groups
    - Implement consistent validation messages

- [ ] **Optimize Cache Implementation**
  - **Target:** `/src/cache/redis_cache.py`
  - **Goal:** Standardize caching across clients
  - **Tasks:**
    - Create a standard cache key generation utility
    - Implement TTL management based on data type
    - Add cache invalidation patterns

- [ ] **Improve HTTP Client Usage**
  - **Target:** Client implementation files
  - **Goal:** Switch from `requests` to `httpx` per coding standards
  - **Tasks:**
    - Identify all uses of the `requests` library
    - Replace with async `httpx` client
    - Implement proper connection pooling and timeouts

- [ ] **Library Modernization**
  - **Target:** Throughout codebase
  - **Goal:** Adopt high-performance libraries
  - **Tasks:**
    - Replace any pandas usage with polars
    - Use pyarrow for columnar data operations
    - Ensure proper async patterns with anyio/asyncio

## Low Priority

- [ ] **Extract Common Service Patterns**
  - **Target:** Service modules in MCP implementations
  - **Goal:** Standardize service layer patterns
  - **Tasks:**
    - Define base service interfaces
    - Create standard patterns for service methods
    - Extract common logic to base classes

- [ ] **Refactor Function Tool Signatures**
  - **Target:** Agent tool implementation files
  - **Goal:** Simplify function signatures, reduce parameters
  - **Tasks:**
    - Create standard request/response models
    - Replace parameter lists with configuration objects
    - Use default class instantiation for common configurations

- [ ] **Eliminate Duplicated Logging**
  - **Target:** All modules with custom logging
  - **Goal:** Standardize logging approach
  - **Tasks:**
    - Create context-aware logging decorator
    - Implement standard log formatters
    - Use structured logging patterns

- [ ] **Clean Up Test Utilities**
  - **Target:** Test files and fixtures
  - **Goal:** Create reusable test fixtures
  - **Tasks:**
    - Extract common test fixtures
    - Implement factory methods for test data
    - Standardize mocking approach

- [ ] **File Size Reduction**
  - **Target:** Files exceeding 350 LoC
  - **Goal:** Split large files into smaller modules
  - **Tasks:**
    - Identify files exceeding the size limit
    - Extract logical components to separate modules
    - Ensure proper imports and exports

## Code Quality Enforcement

- [ ] **Add Pre-commit Hooks**
  - **Target:** Root repository
  - **Goal:** Automate code quality checks
  - **Tasks:**
    - Configure pre-commit for ruff checking
    - Add type checking with mypy
    - Enforce import sorting

- [ ] **Improve Test Coverage**
  - **Target:** Modules with <90% coverage
  - **Goal:** Meet 90% coverage target
  - **Tasks:**
    - Identify modules with insufficient coverage
    - Add unit tests for untested functions
    - Create integration tests for major components

## Compliance Checklist for Each Task

For each completed task, ensure:

- [ ] `ruff check --fix` & `ruff format .` pass cleanly
- [ ] Imports are properly sorted
- [ ] Type hints are complete and accurate
- [ ] Tests cover the changes (aim for ≥90%)
- [ ] No secrets are committed
- [ ] File size ≤500 LoC, ideally ≤350 LoC
- [ ] Code follows KISS/DRY/YAGNI/SIMPLE principles

## Progress Tracking

| Task | Status | PR | Notes |
|------|--------|----|----|
| Calendar Tools Refactoring | ✅ | #PR | Applied error handling decorator pattern |