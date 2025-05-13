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

- [x] **Apply Error Handling Decorator to Flight Search Tools**

  - **Target:** `/src/agents/flight_search.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - ✓ Refactor `search_flights` to use the decorator
    - ✓ Refactor `_add_price_history` to use the decorator
    - ✓ Refactor `_get_price_history` to use the decorator
    - ✓ Refactor `search_flexible_dates` to use the decorator

- [x] **Apply Error Handling Decorator to Accommodations Tools**

  - **Target:** `/src/agents/accommodations.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - ✓ Refactor `search_accommodations` to use the decorator
    - ✓ Refactor `get_accommodation_details` to use the decorator
    - ✓ Create standalone tests to verify error handling

- [x] **Standardize MCP Client Pattern**

  - **Target:** `/src/mcp/base_mcp_client.py` and implementations
  - **Goal:** Create consistent patterns for all MCP clients
  - **Tasks:**
    - ✓ Define standard client factory interfaces
    - ✓ Centralize configuration validation logic
    - ✓ Implement consistent initialization patterns
    - ✓ Standardize error handling approach
  - **Follow-up Tasks:**
    - ✓ Fix circular import between base_mcp_client.py and memory_client.py
    - ✓ Apply factory pattern to all other MCP clients (weather, calendar, etc.)
    - ✓ Improve unit test infrastructure for MCP client testing

- [x] **Consolidate Dual Storage Pattern**
  - **Target:** `/src/utils/dual_storage.py`
  - **Goal:** Extract common persistence logic to avoid duplication
  - **Tasks:**
    - ✓ Create a `DualStorageService` base class
    - ✓ Implement standard persistence operations
    - ✓ Refactor existing services to use the base class
    - ✓ Add proper interface for both Supabase and Memory backends
    - ✓ Create comprehensive test suite with mocked dependencies
    - ✓ Implement isolated tests for generic class behavior
  - **PR:** Completed in #91
  - **Added:** Created comprehensive documentation in dual_storage_refactoring.md

## Medium Priority

- [x] **Fix MCP Import Circularity**

  - **Target:** `/src/mcp/base_mcp_client.py` and `/src/utils/decorators.py`
  - **Goal:** Resolve circular imports between modules
  - **Tasks:**
    - ✓ Refactor decorators.py to remove dependency on memory_client
    - ✓ Extract error handling logic to prevent circular dependencies
    - ✓ Implement proper module initialization order
    - ✓ Add clear documentation about module dependencies
  - **PR:** Completed

- [x] **Improve MCP Client Testing**

  - **Target:** `/tests/mcp/` directory
  - **Goal:** Create robust testing infrastructure for MCP clients
  - **Tasks:**
    - ✓ Create reusable mocks for settings and cache dependencies
    - ✓ Implement test fixtures for standard MCP client testing
    - ✓ Create factories for generating test data
    - ✓ Achieve 90%+ test coverage for all MCP client code
  - **PR:** Completed
  - **Added:** Created comprehensive documentation in isolated_mcp_testing.md

- [x] **Simplify Tool Registration Logic**

  - **Target:** `/src/agents/base_agent.py`
  - **Goal:** Reduce verbosity in tool registration
  - **Tasks:**
    - ✓ Implement a generic `register_tool_group` method
    - ✓ Create a more declarative approach to tool registration
    - ✓ Add automatic tool discovery in specified modules

- [x] **Centralize Parameter Validation**

  - **Target:** MCP client implementations
  - **Goal:** Use Pydantic more consistently for validation
  - **Tasks:**
    - ✓ Define standard field validators for common patterns
    - ✓ Create base model classes for common parameter groups
    - ✓ Implement consistent validation messages

- [ ] **Optimize Cache Implementation**

  - **Target:** `/src/cache/redis_cache.py`
  - **Goal:** Standardize caching across clients
  - **Tasks:**
    - Create a standard cache key generation utility
    - Implement TTL management based on data type
    - Add cache invalidation patterns

- [x] **Improve HTTP Client Usage**

  - **Target:** Client implementation files
  - **Goal:** Switch from `requests` to `httpx` per coding standards
  - **Tasks:**
    - [x] Identify all uses of the `requests` library (No active usage found in Python source code as of YYYY-MM-DD)
    - [N/A] Replace with async `httpx` client (Not applicable as no `requests` usage to replace)
    - [N/A] Implement proper connection pooling and timeouts (Not applicable)

- [ ] **Library Modernization**
  - **Target:** Throughout codebase
  - **Goal:** Adopt high-performance libraries
  - **Tasks:**
    - [x] Replace any pandas usage with polars (No pandas usage found in src)
    - [x] Use pyarrow for columnar data operations (No pyarrow usage found; no immediate pandas/columnar processing to optimize with it)
    - [ ] Ensure proper async patterns with anyio/asyncio (Generally good; minor sync file I/O in migrations noted - likely acceptable)

## Low Priority

- [x] **Extract Common Service Patterns**

  - **Target:** Service modules in MCP implementations
  - **Goal:** Standardize service layer patterns
  - **Tasks:**
    - ✓ Define base service interfaces
    - ✓ Create standard patterns for service methods
    - ✓ Extract common logic to base classes

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

- [x] **Create Isolated Test Utilities**

  - **Target:** Test files and fixtures
  - **Goal:** Create reusable test fixtures independent of environment variables
  - **Tasks:**
    - ✓ Create portable test modules that don't depend on settings
    - ✓ Implement isolated test fixtures with proper mocking
    - ✓ Standardize mocking approach for database and MCP clients
    - ✓ Add comprehensive test coverage for abstract base classes

- [ ] **Clean Up Test Utilities**

  - **Target:** All test files and fixtures
  - **Goal:** Refactor remaining test utilities
  - **Tasks:**
    - Extract remaining common test fixtures
    - Implement factory methods for test data
    - Apply isolated testing pattern more broadly

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

- [x] `ruff check --fix` & `ruff format .` pass cleanly
- [x] Imports are properly sorted
- [x] Type hints are complete and accurate
- [x] Tests cover the changes (aim for ≥90%)
- [x] No secrets are committed
- [x] File size ≤500 LoC, ideally ≤350 LoC
- [x] Code follows KISS/DRY/YAGNI/SIMPLE principles

## Progress Tracking

| Task                        | Status | PR  | Notes                                                                   |
| --------------------------- | ------ | --- | ----------------------------------------------------------------------- |
| Calendar Tools Refactoring  | ✅     | #87 | Applied error handling decorator pattern                                |
| Flight Search Refactoring   | ✅     | #88 | Applied error handling decorator to four methods                        |
| Error Handling Tests        | ✅     | #88 | Created standalone tests for decorator functionality                    |
| Accommodations Refactoring  | ✅     | #89 | Applied error handling decorator to two methods                         |
| MCP Client Standardization  | ✅     | #90 | Implemented client factory pattern, improved error handling             |
| MCP Factory Pattern         | ✅     | #90 | Created standard factory interface + implementations for Time & Flights |
| MCP Error Classification    | ✅     | #90 | Added error categorization system for better error handling             |
| MCP Documentation           | ✅     | #90 | Added comprehensive README for MCP architecture                         |
| Dual Storage Service        | ✅     | #91 | Created DualStorageService base class with standard CRUD operations     |
| Trip Storage Service        | ✅     | #91 | Implemented TripStorageService with Pydantic validation                 |
| Fix Circular Imports        | ✅     | #92 | Fixed circular imports in base_mcp_client.py and decorators.py          |
| Isolated Test Patterns      | ✅     | #93 | Created environment-independent test suite for dual storage services    |
| Comprehensive Test Coverage | ✅     | #93 | Added tests for abstract interfaces and error handling                  |
| MCP Isolated Testing        | ✅     | #94 | Implemented isolated testing pattern for MCP clients                    |
| MCP Testing Documentation   | ✅     | #94 | Created documentation for isolated MCP testing pattern                  |
| Tool Registration Logic     | ✅     | #95 | Simplified tool registration with automatic discovery                   |
| Parameter Validation        | ✅     | #95 | Centralized parameter validation with Pydantic base models              |
| Service Pattern Extraction  | ✅     | #95 | Extracted common service patterns for MCP implementations               |