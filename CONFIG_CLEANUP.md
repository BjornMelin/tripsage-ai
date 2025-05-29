# Configuration and Utilities Cleanup Plan

## Overview

This document outlines the cleanup and consolidation needed for the `/tripsage/config/`, `/tripsage/db/`, `/tripsage/storage/`, and `/tripsage/utils/` directories after the MCP-to-SDK migration.

## 1. Config Directory Cleanup

### Files to Update

#### `feature_flags.py`

**Issues**: Contains flags for deleted MCP services
**Actions**:

- Remove lines 61-75 (weather, flights, calendar, time integration flags)
- Update migration status methods to reflect current state
- Remove any logic related to deleted MCPs

#### `webcrawl_feature_flags.py`

**Issues**: Not really feature flags, just performance metrics
**Actions**:

- Move to `/tripsage/monitoring/performance_metrics.py`
- Generalize for all services, not just webcrawl

#### `example_webcrawl_config.py`

**Issues**: Example file in wrong location
**Actions**:

- Move to `/examples/webcrawl_config_example.py`

### Files to Keep (Already Clean)

- `app_settings.py` - Main settings (already updated)
- `mcp_settings.py` - Airbnb-only MCP settings
- `service_registry.py` - Well-designed service registry
- `file_config.py` - Simple file constants

## 2. Database Directory Cleanup

### Critical Refactoring Needed

#### `db/initialize.py`

**Issues**: Entirely MCP-based initialization
**Actions**:

1. Remove all MCP imports and MCPManager usage
2. Replace with direct Supabase SDK:

   ```python
   from supabase import create_client, Client
   from tripsage.config.app_settings import settings
   
   def get_supabase_client() -> Client:
       return create_client(
           settings.database.supabase_url,
           settings.database.supabase_anon_key.get_secret_value()
       )
   ```

3. Update all database operations to use Supabase client directly
4. Remove MCP abstraction layers

#### `db/migrations/runner.py`

**Issues**: Runs migrations through MCP
**Actions**:

1. Replace MCP-based SQL execution with direct Supabase SDK
2. Use `supabase.postgrest.rpc()` or raw SQL execution
3. Add proper transaction handling
4. Improve error reporting

## 3. Storage Directory Cleanup

### Files Need Minor Updates

#### `storage/base.py`

**Status**: Clean, no MCP references
**Enhancement**: Add async context manager support

#### `storage/dual_storage.py`

**Status**: Clean but underutilized
**Actions**:

1. Enhance with connection pooling
2. Add retry logic
3. Better error handling
4. Create usage examples

### Missing File

- `neo4j_runner.py` is referenced but doesn't exist - either create or remove references

## 4. Utils Directory Cleanup

### Major Consolidation Needed

#### Cache Consolidation

**Files**: `cache.py` and `cache_tools.py`
**Actions**:

1. Merge into single `/tripsage/utils/caching.py`
2. Keep best implementations:
   - Redis operations from `cache_tools.py`
   - Decorators from both
   - Remove duplicate InMemoryCache implementations
3. Create unified caching interface

#### Files to Update

##### `decorators.py`

**Issues**: Memory decorator uses MCPManager
**Actions**:

1. Update `ensure_memory_client_initialized` to use direct Neo4j:

   ```python
   from neo4j import GraphDatabase
   from tripsage.config.app_settings import settings
   
   def ensure_memory_client_initialized(func):
       @functools.wraps(func)
       async def wrapper(*args, **kwargs):
           # Use direct Neo4j driver instead of MCP
           driver = GraphDatabase.driver(
               settings.neo4j.uri,
               auth=(settings.neo4j.user, settings.neo4j.password.get_secret_value())
           )
           # ... rest of implementation
   ```

2. Remove TODO comment about Week 2 migration

##### `session_memory.py`

**Issues**: May have MCP dependencies via imports
**Actions**:

1. Check and update `memory_tools` imports
2. Remove legacy compatibility functions (lines 332-368)
3. Update to use direct Neo4j operations

##### `db_utils.py`

**Issues**: Mentions MCP in comments
**Actions**:

1. Update comment on line 5 to remove "via MCP clients"
2. Consider renaming to `database_config.py` since it just returns settings

##### `settings.py`

**Issues**: Contains settings for deleted MCPs
**Actions**:

1. Remove `GoogleMapsMCPSettings` class
2. Remove any other MCP settings for migrated services
3. Keep only settings still in use

#### Files to Keep (Clean)

- `client_utils.py` - Still needed for Airbnb MCP
- `content_types.py` - Clean enums
- `error_handling.py` - Generic error handling
- `file_validation.py` - File validation utilities
- `logging.py` - Logging configuration

## Implementation Priority

### Phase 1: Critical Database Fixes (HIGH)

1. Refactor `db/initialize.py` to use Supabase SDK
2. Refactor `db/migrations/runner.py` for direct SQL
3. Update `decorators.py` memory decorator

### Phase 2: Config Cleanup (MEDIUM)

1. Remove outdated feature flags
2. Move example files
3. Consolidate performance metrics

### Phase 3: Utils Consolidation (MEDIUM)

1. Merge cache implementations
2. Update session memory
3. Clean up imports and comments

### Phase 4: Documentation (LOW)

1. Update docstrings
2. Add usage examples
3. Create migration guide

## Expected Outcomes

After this cleanup:

1. **No MCP dependencies** except for Airbnb operations
2. **Direct SDK usage** for all database operations
3. **Consolidated utilities** with clear purposes
4. **Cleaner directory structure** with proper file organization
5. **Better performance** from direct database connections
6. **Easier maintenance** with less abstraction layers

## Files to Delete

- `webcrawl_feature_flags.py` (after moving content)
- `example_webcrawl_config.py` (after moving to examples)
- Duplicate cache implementations (after consolidation)

## New Files to Create

- `/tripsage/monitoring/performance_metrics.py`
- `/tripsage/utils/caching.py` (consolidated)
- `/examples/webcrawl_config_example.py`
