# Migration Checklist: src/ to tripsage/

This document tracks the migration progress from the old `src/` directory to the new `tripsage/` directory. Files are categorized as either ready for deletion from `src/` or requiring further investigation.

## Status Legend

- ✅ Can be deleted from src/
- ⚠️ Needs investigation before deletion
- 🔍 Notable differences found
- ❌ Not found in tripsage/ (keep in src/)

## Directory Structure Comparison

### agents/

| File                          | Status     | Notes                                                            |
| ----------------------------- | ---------- | ---------------------------------------------------------------- |
| accommodation_agent.py        | 🗑️ DELETED | Renamed to accommodation.py in tripsage/agents/                  |
| accommodations.py             | 🗑️ DELETED | Migrated caching logic to tripsage/tools/accommodations_tools.py |
| base_agent.py                 | 🗑️ DELETED | Renamed to base.py in tripsage/agents/                           |
| budget_agent.py               | 🗑️ DELETED | Renamed to budget.py in tripsage/agents/                         |
| destination_research_agent.py | 🗑️ DELETED | Renamed to destination_research.py in tripsage/agents/           |
| flight_agent.py               | 🗑️ DELETED | Renamed to flight.py in tripsage/agents/                         |
| itinerary_agent.py            | 🗑️ DELETED | Renamed to itinerary.py in tripsage/agents/                      |
| travel_planning_agent.py      | 🗑️ DELETED | Renamed to planning.py in tripsage/agents/                       |
| travel_agent.py               | 🗑️ DELETED | Renamed to travel.py in tripsage/agents/                         |
| travel_insights.py            | 🗑️ DELETED | Exists in tripsage/agents/                                       |
| calendar_tools.py             | ❌         | Moved to tripsage/tools/                                         |
| flight_booking.py             | ❌         | Moved to tripsage/tools/                                         |
| flight_search.py              | ❌         | Moved to tripsage/tools/                                         |
| memory_tools.py               | ❌         | Moved to tripsage/tools/                                         |
| planning_tools.py             | ❌         | Moved to tripsage/tools/                                         |
| time_tools.py                 | ❌         | Moved to tripsage/tools/                                         |
| webcrawl_tools.py             | ❌         | Moved to tripsage/tools/                                         |
| config.py                     | ❌         | Moved to tripsage/config/                                        |
| demo.py                       | ❌         | Not found in tripsage/                                           |
| destination_research.py       | 🗑️ DELETED | Different impl with ResearchTopicResult class                    |
| README.md                     | ⚠️         | Check content differences                                        |
| requirements.txt              | ❌         | Project-level requirements                                       |

### api/

| File             | Status | Notes                                                           |
| ---------------- | ------ | --------------------------------------------------------------- |
| **init**.py      | ❌     | Not migrated to tripsage/api/                                   |
| auth.py          | ❌     | Not migrated                                                    |
| database.py      | ❌     | Not migrated                                                    |
| dependencies.py  | 🔍     | Completely different - src focuses on DB repos, tripsage on MCP |
| main.py          | ❌     | Not migrated                                                    |
| requirements.txt | ❌     | Not migrated                                                    |
| CHANGES.md       | ❌     | Not migrated                                                    |
| README.md        | ❌     | Not migrated                                                    |
| routes/\*        | ❌     | Not migrated                                                    |

### cache/

| File           | Status | Notes                                                                     |
| -------------- | ------ | ------------------------------------------------------------------------- |
| **init**.py    | ✅     | Can be deleted - functionality covered by web_cache and future Redis MCP |
| redis_cache.py | ✅     | Can be deleted - web ops in web_cache, generic caching will use Redis MCP |

### db/

| File      | Status | Notes                                                 |
| --------- | ------ | ----------------------------------------------------- |
| All files | ❌     | No direct equivalent in tripsage/ - may be refactored |

### mcp/

| File      | Status | Notes                                                           |
| --------- | ------ | --------------------------------------------------------------- |
| All files | ❌     | Refactored into tripsage/mcp_abstraction/ and tripsage/clients/ |

### utils/

| File                    | Status | Notes                                                                |
| ----------------------- | ------ | -------------------------------------------------------------------- |
| **init**.py             | ✅     | Exists in tripsage/utils/                                            |
| cache.py                | ⚠️     | Appears to be new implementation in tripsage/utils/                  |
| client_utils.py         | ❌     | Only in tripsage/utils/                                              |
| config.py               | 🗑️ DELETED | Superseded by tripsage/config/app_settings.py and mcp_settings.py |
| db_utils.py             | ❌     | Only in tripsage/utils/                                              |
| decorators.py           | 🗑️ DELETED | Migrated to tripsage/utils/decorators.py with both decorators     |
| dual_storage.py         | 🔍     | Different abstraction - tripsage is generic storage class            |
| dual_storage_service.py | ⚠️     | Check if functionality in tripsage/storage/                          |
| error_decorators.py     | 🗑️ DELETED | Merged into tripsage/utils/decorators.py                          |
| error_handling.py       | 🗑️ DELETED | Functionality covered by tripsage/utils/error_handling.py         |
| logging.py              | ⚠️     | Check differences between versions                                   |
| session_memory.py       | ⚠️     | Check differences between versions                                   |
| settings.py             | ⚠️     | Check differences between versions                                   |
| settings_init.py        | ❌     | Not found in tripsage/                                               |
| trip_storage_service.py | ⚠️     | Check if functionality in tripsage/storage/                          |

### tests/

| File      | Status | Notes                                                 |
| --------- | ------ | ----------------------------------------------------- |
| All files | ❌     | Separate test structure in src/ - needs investigation |

### types/

| File        | Status | Notes                                      |
| ----------- | ------ | ------------------------------------------ |
| supabase.ts | ❌     | TypeScript type definitions - not migrated |

## Files to Investigate Further

Before deleting these files, we need to:

1. Compare content between `src/agents/accommodations.py` and `tripsage/agents/accommodation.py`
2. Check if `src/cache/redis_cache.py` functionality is fully covered by `tripsage/utils/cache.py`
3. Verify `src/api/dependencies.py` vs `tripsage/api/dependencies.py` differences
4. Compare utility files for overlapping functionality
5. Determine if test files in `src/tests/` should be migrated

## Next Steps

1. Use file comparison tools to check content differences
2. Identify any unique functionality in src/ that needs preservation
3. Create migration scripts for database-related code if needed
4. Update import statements in remaining src/ files
5. Gradually delete confirmed duplicate files

## Summary of Key Findings

### Files Already Deleted

1. **Agent Files**: All agent files that were renamed (e.g., accommodation_agent.py → accommodation.py)
2. **destination_research.py**: Different implementation with ResearchTopicResult class

### Major Architectural Differences

1. **MCP Integration**:

   - src/mcp/: Old MCP client implementations
   - tripsage/mcp_abstraction/: New abstraction layer with wrappers
   - tripsage/clients/: Refactored MCP client implementations

2. **Storage Strategy**:

   - src/utils/dual_storage.py: Direct TripStorageService implementation
   - tripsage/storage/dual_storage.py: Generic DualStorage class

3. **Error Handling**:

   - src/utils/error_handling.py: Basic error classes
   - tripsage/utils/error_handling.py: Enhanced with MCPError and decorators

4. **API Dependencies**:

   - src/api/dependencies.py: Database repository focused
   - tripsage/api/dependencies.py: MCP manager focused

5. **Cache Implementation**:
   - src/cache/redis_cache.py: Direct Redis implementation
   - tripsage/utils/cache.py: Advanced caching with content types and TTL

### Files Requiring Further Investigation

1. **src/agents/accommodations.py**: Contains AccommodationSearchTool class - determine if functionality is covered by new agent
2. **src/api/**: Entire API directory not migrated - check if needed
3. **src/db/**: Database implementation - may be replaced by MCP abstraction
4. **src/tests/**: Test files - need to determine migration strategy

## Migration Progress

- [x] Agents directory (complete - all files migrated or deleted)
- [ ] API directory
- [x] Cache directory (complete - functionality migrated to web_cache and Redis MCP)
- [ ] Database directory
- [ ] MCP directory
- [ ] Utils directory
- [ ] Tests directory
- [ ] Types directory

## Recommended Actions

1. **Immediate**: Delete clearly duplicate utils files after verifying functionality
2. **Investigation**: Compare src/agents/accommodations.py with new implementation
3. **Decision Required**: Determine if src/api/ and src/db/ are still needed
4. **Test Migration**: Create plan for migrating test files to match new structure
