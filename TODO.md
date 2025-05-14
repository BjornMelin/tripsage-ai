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

- [ ] **Complete Codebase Restructuring (Issue #31)**
  - **Target:** Throughout codebase
  - **Goal:** Consolidate application logic into the `tripsage/` directory
  - **Tasks:**
    - [x] Update tool imports:
      - ✓ Update `tripsage/tools/time_tools.py` to use `from agents import function_tool`
      - ✓ Update `tripsage/tools/memory_tools.py` to use `from agents import function_tool`
      - ✓ Update `tripsage/tools/webcrawl_tools.py` to use `from agents import function_tool`
    - [x] Migrate remaining agent files:
      - ✓ Migrate `src/agents/budget_agent.py` → `tripsage/agents/budget.py`
      - ✓ Migrate `src/agents/itinerary_agent.py` → `tripsage/agents/itinerary.py`
    - [x] Migrate remaining tool files:
      - ✓ Migrate `src/agents/planning_tools.py` → `tripsage/tools/planning_tools.py`
    - [x] Migrate additional agent files:
      - ✓ Migrate `src/agents/travel_insights.py` → `tripsage/agents/travel_insights.py`
      - ✓ Migrate `src/agents/flight_booking.py` → `tripsage/tools/flight_booking.py`
      - ✓ Migrate `src/agents/flight_search.py` → `tripsage/tools/flight_search.py`
    - [x] Migrate browser tools:
      - ✓ Migrate `src/agents/tools/browser/` → `tripsage/tools/browser/`
      - ✓ Update imports in `tripsage/tools/browser/tools.py` to use `from agents import function_tool`
      - ✓ Update imports in `tripsage/tools/browser_tools.py` to use `from agents import function_tool`
    - [ ] Update remaining imports:
      - Update all `from src.*` imports to `from tripsage.*`
      - Ensure consistent use of the `agents` module instead of `openai_agents_sdk`
    - [ ] Update tests to match new structure:
      - Update imports in test files to use tripsage module
      - Create new test files for migrated tools and agents
      - Ensure all tests pass with new structure
    - [ ] Clean up duplicated files:
      - Remove unnecessary files from src/ after migration
      - Ensure no duplicate functionality exists
    - [ ] Documentation updates:
      - Update README.md to reflect new structure
      - Add directory structure documentation
      - Create migration guide for developers

- [ ] **MCP Client Cleanup**
  - **Target:** `/src/mcp/` directory
  - **Goal:** Remove redundant MCP client implementations
  - **Tasks:**
    - [ ] Audit `src/mcp/` to identify what can be removed
    - [ ] Update documentation to reflect the use of external MCP services
    - [ ] Ensure proper use of Pydantic V2 patterns in remaining MCP clients
    - [ ] Create proper factory patterns for all MCP clients
    - [ ] Standardize configuration across all clients
    - [ ] Migrate essential clients to tripsage/clients/ directory
    - [ ] Implement comprehensive test suite for each client

- [ ] **Ensure Proper Pydantic V2 Implementation**
  - **Target:** Throughout codebase
  - **Goal:** Ensure all models use Pydantic V2 patterns
  - **Tasks:**
    - [ ] Audit and update method usage:
      - Replace `dict()` with `model_dump()` (found in 12+ files)
      - Replace `json()` with `model_dump_json()` (found in 13+ files)
      - Replace `parse_obj()` with `model_validate()` (found in 5+ files)
      - Replace `parse_raw()` with `model_validate_json()` (found in 3+ files)
      - Replace `schema()` with `model_json_schema()` (found in 2+ files)
    - [ ] Audit and update validation patterns:
      - Replace `validator` with `field_validator` and add `@classmethod`
      - Update validator modes to use `"before"` and `"after"` parameters
      - Update any root validator usage with `model_validator`
    - [ ] Update type validation:
      - Update Union type usage for proper validation
      - Replace `typing.Optional` with field default values
      - Replace `ConstrainedInt` with `Annotated[int, Field(ge=0)]`
    - [ ] Implement advanced features:
      - Use `field_serializer` for custom serialization logic
      - Use `model_serializer` for whole-model serialization
      - Implement `TypeAdapter` for non-BaseModel validation
      - Use `discriminated_union` for polymorphic models
    - [ ] Update documentation with Pydantic V2 examples
    - [ ] Add type checking with mypy and Pydantic plugin

- [ ] **Ensure Proper OpenAI Agents SDK Implementation**
  - **Target:** Agent implementations
  - **Goal:** Ensure agents use the latest SDK patterns
  - **Tasks:**
    - [ ] Standardize agent class structure:
      - Consistent initialization with settings-based defaults
      - Proper tool registration patterns
      - Standard error handling implementation
    - [ ] Improve tool implementation:
      - Use proper parameter models with strict validation
      - Implement consistent error reporting
      - Add comprehensive docstrings with examples
    - [ ] Ensure proper handoff configuration:
      - Standardize handoff methods across agents
      - Implement context passing between agents
      - Create proper initialization in handoff list
    - [ ] Implement guardrails:
      - Add input validation on all tools
      - Implement standardized safety checks
      - Create comprehensive logging for tool usage
    - [ ] Improve conversation history management:
      - Implement proper conversation storage
      - Create efficient context retrieval methods
      - Ensure consistent memory integration

- [ ] **Implement Neo4j Knowledge Graph Integration**
  - **Target:** Throughout codebase
  - **Goal:** Standardize Neo4j integration
  - **Tasks:**
    - [ ] Define standard entity models
    - [ ] Create reusable CRUD operations
    - [ ] Implement graph query patterns
    - [ ] Define relationship type constants
    - [ ] Create standard validation for graph operations
    - [ ] Implement caching for graph operations
    - [ ] Add comprehensive test suite

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
    - [ ] Create a standard cache key generation utility
    - [ ] Implement TTL management based on data type
    - [ ] Add cache invalidation patterns
    - [ ] Add cache hit/miss statistics tracking
    - [ ] Implement cache prefetching for common queries
    - [ ] Create cache warming strategies
    - [ ] Add distributed cache locking
    - [ ] Implement typed cache interface

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
    - [ ] Add structured logging with structlog
    - [ ] Implement typed API clients for external services
    - [ ] Use proper dependency injection patterns

- [ ] **API and Database Migrations**
  - **Target:** `/src/api/` and `/src/db/` directories
  - **Goal:** Migrate API and database components to tripsage structure
  - **Tasks:**
    - [ ] Create tripsage/api directory with FastAPI structure:
      - Create endpoint groups by domain (users, trips, flights, etc.)
      - Implement proper dependency injection
      - Add comprehensive request/response models
    - [ ] Implement database migration:
      - Move database models to tripsage/models/db
      - Update repositories with proper typing
      - Ensure consistent error handling
      - Implement proper connection pooling
    - [ ] API Improvements:
      - Add OpenAPI documentation
      - Implement API versioning
      - Add proper rate limiting
      - Implement comprehensive logging
      - Add request validation with Pydantic
    - [ ] Neo4j Database Improvements:
      - Standardize Neo4j query patterns
      - Implement proper transaction handling
      - Add efficient indexing strategies
      - Implement proper error handling for Neo4j operations

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
    - [ ] Create standard request/response models
    - [ ] Replace parameter lists with configuration objects
    - [ ] Use default class instantiation for common configurations
    - [ ] Implement proper typing for all parameters
    - [ ] Add comprehensive validation with helpful error messages
    - [ ] Create reusable parameter validators

- [ ] **Eliminate Duplicated Logging**

  - **Target:** All modules with custom logging
  - **Goal:** Standardize logging approach
  - **Tasks:**
    - [ ] Create context-aware logging decorator
    - [ ] Implement standard log formatters
    - [ ] Use structured logging patterns
    - [ ] Add correlation IDs for request tracing
    - [ ] Implement log level control by module
    - [ ] Add performance metrics logging

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
    - [ ] Extract remaining common test fixtures
    - [ ] Implement factory methods for test data
    - [ ] Apply isolated testing pattern more broadly
    - [ ] Create standard patterns for mocking
    - [ ] Add comprehensive assertion helpers
    - [ ] Implement proper test teardown
    - [ ] Add performance testing utilities

- [ ] **File Size Reduction**
  - **Target:** Files exceeding 350 LoC
  - **Goal:** Split large files into smaller modules
  - **Tasks:**
    - [ ] Identify files exceeding the size limit
    - [ ] Extract logical components to separate modules
    - [ ] Ensure proper imports and exports
    - [ ] Maintain documentation for separated modules
    - [ ] Add index files for grouped exports

## Code Quality Enforcement

- [ ] **Add Pre-commit Hooks**

  - **Target:** Root repository
  - **Goal:** Automate code quality checks
  - **Tasks:**
    - [ ] Configure pre-commit for ruff checking
    - [ ] Add type checking with mypy
    - [ ] Enforce import sorting
    - [ ] Add line length enforcement
    - [ ] Implement docstring validation
    - [ ] Add security scanning with bandit
    - [ ] Enforce consistent file naming

- [ ] **Improve Test Coverage**
  - **Target:** Modules with <90% coverage
  - **Goal:** Meet 90% coverage target
  - **Tasks:**
    - [ ] Identify modules with insufficient coverage
    - [ ] Add unit tests for untested functions
    - [ ] Create integration tests for major components
    - [ ] Implement property-based testing for complex logic
    - [ ] Add mutation testing for critical components
    - [ ] Create comprehensive edge case tests
    - [ ] Implement performance regression tests

## Compliance Checklist for Each Task

For each completed task, ensure:

- [x] `ruff check --fix` & `ruff format .` pass cleanly
- [x] Imports are properly sorted
- [x] Type hints are complete and accurate
- [x] Tests cover the changes (aim for ≥90%)
- [x] No secrets are committed
- [x] File size ≤500 LoC, ideally ≤350 LoC
- [x] Code follows KISS/DRY/YAGNI/SIMPLE principles

## Detailed Implementation Plans

### Codebase Restructuring (Issue #31)

- **Target:** Core application logic
- **Goal:** Move all application logic to `tripsage/` directory with consistent patterns
- **Implementation Phases:**

1. **Phase 1: Core Components** (In Progress)
   - [x] Migrate base agent and tool implementations
   - [x] Update import patterns to use the `agents` module
   - [x] Implement consistent agent class naming (remove redundant "Agent" suffixes)
   - [x] Migrate browser tools with updated imports
   - [ ] Update the remaining imports in all migrated files
   - [ ] Create `__init__.py` files with proper exports

2. **Phase 2: Agent Implementation**
   - [ ] Create agent factory for standardized initialization
   - [ ] Implement triage pattern for agent selection
   - [ ] Create consistent handoff mechanisms
   - [ ] Update prompt templates for all agents
   - [ ] Standardize agent metadata structure

3. **Phase 3: MCP Integration**
   - [ ] Migrate MCP clients to `tripsage/clients/` directory
   - [ ] Implement consistent client factory pattern
   - [ ] Create standardized error handling for MCP operations
   - [ ] Add response validation with Pydantic V2
   - [ ] Implement proper async context management

4. **Phase 4: Database Integration**
   - [ ] Move database models to `tripsage/models/` directory
   - [ ] Update repositories with proper dependency injection
   - [ ] Create consistent error handling for database operations
   - [ ] Implement efficient connection pooling
   - [ ] Add comprehensive validation for all database operations

5. **Phase 5: Final Integration**
   - [ ] Create integration tests for the new structure
   - [ ] Update documentation with architecture diagrams
   - [ ] Create usage examples for all components
   - [ ] Implement API endpoints with the new structure
   - [ ] Create comprehensive deployment documentation

### OpenAI Agents SDK Integration (Issue #28)

- **Target:** Agent implementation
- **Goal:** Implement the latest OpenAI Agents SDK patterns
- **Implementation Tasks:**

1. **SDK Setup and Configuration**
   - [ ] Create standardized SDK configuration
   - [ ] Implement proper initialization patterns
   - [ ] Add environment variable validation
   - [ ] Create fallback mechanisms for missing settings
   - [ ] Implement centralized settings management

2. **Agent Architecture**
   - [ ] Implement hierarchical agent structure
   - [ ] Create triage agent for request routing
   - [ ] Implement specialized agents with defined responsibilities
   - [ ] Create consistent handoff mechanisms between agents
   - [ ] Implement context preservation during handoffs

3. **Function Tool Implementation**
   - [ ] Create standardized tool parameter models
   - [ ] Implement consistent error handling for all tools
   - [ ] Add comprehensive validation for tool inputs
   - [ ] Create proper documentation for all tools
   - [ ] Implement typed return values for all tools

4. **MCP Server Integration**
   - [ ] Implement `MCPServerManager` class
   - [ ] Create async context management for server connections
   - [ ] Add proper error handling for server failures
   - [ ] Implement reconnection strategies
   - [ ] Create consistent initialization pattern

5. **Advanced Features**
   - [ ] Implement structured output with JSON mode
   - [ ] Add parallel tool execution for efficiency
   - [ ] Create streaming response handlers
   - [ ] Implement memory integration with graph database
   - [ ] Add custom model integration capabilities

### Pydantic V2 Migration

- **Target:** Core models and validation
- **Goal:** Upgrade to Pydantic V2 patterns for validation and serialization
- **Implementation Tasks:**

1. **Core Models Update**
   - [ ] Replace `BaseSettings` with `ConfigDict` approach
   - [ ] Update field validators with `@field_validator`
   - [ ] Replace `validator` with `field_validator` and add `@classmethod`
   - [ ] Update model serialization methods
   - [ ] Implement model validators with `@model_validator`

2. **MCP Client Models**
   - [ ] Update request/response models
   - [ ] Implement proper field validation
   - [ ] Create standardized error messages
   - [ ] Add type adapters for non-model validation
   - [ ] Implement serializers for custom types

3. **API Models**
   - [ ] Update FastAPI request/response models
   - [ ] Implement proper field validation
   - [ ] Create standardized error responses
   - [ ] Add model examples for documentation
   - [ ] Implement comprehensive validation for all API endpoints

## Progress Tracking

| Task                          | Status | PR  | Notes                                                                   |
| ----------------------------- | ------ | --- | ----------------------------------------------------------------------- |
| Calendar Tools Refactoring    | ✅     | #87 | Applied error handling decorator pattern                                |
| Flight Search Refactoring     | ✅     | #88 | Applied error handling decorator to four methods                        |
| Error Handling Tests          | ✅     | #88 | Created standalone tests for decorator functionality                    |
| Accommodations Refactoring    | ✅     | #89 | Applied error handling decorator to two methods                         |
| MCP Client Standardization    | ✅     | #90 | Implemented client factory pattern, improved error handling             |
| MCP Factory Pattern           | ✅     | #90 | Created standard factory interface + implementations for Time & Flights |
| MCP Error Classification      | ✅     | #90 | Added error categorization system for better error handling             |
| MCP Documentation             | ✅     | #90 | Added comprehensive README for MCP architecture                         |
| Dual Storage Service          | ✅     | #91 | Created DualStorageService base class with standard CRUD operations     |
| Trip Storage Service          | ✅     | #91 | Implemented TripStorageService with Pydantic validation                 |
| Fix Circular Imports          | ✅     | #92 | Fixed circular imports in base_mcp_client.py and decorators.py          |
| Isolated Test Patterns        | ✅     | #93 | Created environment-independent test suite for dual storage services    |
| Comprehensive Test Coverage   | ✅     | #93 | Added tests for abstract interfaces and error handling                  |
| MCP Isolated Testing          | ✅     | #94 | Implemented isolated testing pattern for MCP clients                    |
| MCP Testing Documentation     | ✅     | #94 | Created documentation for isolated MCP testing pattern                  |
| Tool Registration Logic       | ✅     | #95 | Simplified tool registration with automatic discovery                   |
| Parameter Validation          | ✅     | #95 | Centralized parameter validation with Pydantic base models              |
| Service Pattern Extraction    | ✅     | #95 | Extracted common service patterns for MCP implementations               |
| Codebase Restructuring - Part 1 | ✅   | -   | Updated tool imports, migrated all agent files and tools              |
| Browser Tools Migration         | ✅   | -   | Updated browser tools with correct imports and tools registration        |
| Codebase Restructuring - Part 2 | 🔄   | -   | Remaining import updates and test updates in progress                    |
| OpenAI Agents SDK Integration   | 🔄   | -   | Research completed, implementation planning in progress                  |
| Pydantic V2 Migration           | 📅   | -   | Scheduled to start after Codebase Restructuring is complete              |