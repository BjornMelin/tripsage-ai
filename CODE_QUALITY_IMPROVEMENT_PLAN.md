# TripSage AI - Code Quality Improvement Plan

> **Status**: Backend tasks prioritized for immediate implementation
> **Frontend**: Tasks documented but deferred (another developer working on frontend)

## 🎯 Backend Code Quality Tasks

### **Phase 1: High Priority (Complete First - 1-2 weeks)**

#### 1. **Implement Error Handling Decorator**

- [ ] Create `@with_error_handling` decorator in `tripsage_core/utils/decorator_utils.py`
- [ ] Replace 50+ duplicate try-catch patterns across business services
- [ ] Target files:
  - `tripsage_core/services/business/auth_service.py`
  - `tripsage_core/services/business/user_service.py`
  - `tripsage_core/services/business/flight_service.py`
  - `tripsage_core/services/business/accommodation_service.py`
  - `tripsage_core/services/business/memory_service.py`
- [ ] Update all services to use the decorator
- [ ] Test error handling consistency
- **Impact**: Eliminate 200+ lines of duplicate error handling code

#### 2. **Create BaseService Pattern**

- [ ] Create `BaseService` class in `tripsage_core/services/base_service.py`
- [ ] Implement dependency injection pattern for database/external services
- [ ] Refactor all business services to inherit from `BaseService`
- [ ] Remove duplicate initialization code (219 lines in service registry)
- [ ] Update service tests
- **Impact**: Reduce service initialization duplication by 80%

#### 3. **Backend Linting & Formatting Cleanup**

- [ ] Run `ruff format .` on entire backend codebase
- [ ] Run `ruff check . --fix` to auto-fix issues
- [ ] Fix remaining manual linting issues
- [ ] Update import sorting with `ruff check --select I --fix .`
- [ ] Ensure all backend code passes lint checks
- **Impact**: Consistent code style across 500+ Python files

#### 4. **Remove Legacy Backend Code**

- [ ] Remove duplicate service registry in `tripsage/agents/service_registry.py` (219 lines)
- [ ] Keep config-based registry, deprecate agents registry
- [ ] Update all imports to use config registry pattern
- [ ] Clean duplicate dependencies in `pyproject.toml`
- [ ] Remove unused imports across backend
- **Impact**: 300+ lines of legacy code removed

### **Phase 2: Medium Priority (2-4 weeks)**

#### 5. **Implement Common Validators**

- [ ] Create `CommonValidators` class in `tripsage_core/models/schemas_common/validators.py`
- [ ] Extract duplicate validation logic (password, email, airport codes)
- [ ] Update all Pydantic models to use common validators
- [ ] Remove duplicate `@field_validator` implementations
- **Impact**: Eliminate validation code duplication across 15+ models

#### 6. **Create SearchCacheMixin**

- [ ] Implement `SearchCacheMixin` in `tripsage_core/utils/cache_utils.py`
- [ ] Refactor flight service to use mixin
- [ ] Refactor accommodation service to use mixin
- [ ] Standardize cache key generation and cleanup logic
- **Impact**: Remove 100+ lines of duplicate cache management

#### 7. **Simplify Complex Backend Logic**

- [ ] Refactor `chat_orchestration.py` (673 lines) - break into smaller focused services
- [ ] Extract `execute_parallel_tools` into separate utility class
- [ ] Simplify memory bridge `_map_session_to_state` method using strategy pattern
- [ ] Break down handoff coordinator condition evaluation (10+ cyclomatic complexity)
- [ ] Implement strategy pattern for complex condition chains
- **Impact**: Reduce average function complexity from 15+ to <8

#### 8. **Create BaseAPIService Pattern**

- [ ] Implement `BaseAPIService` in `tripsage/api/services/base.py`
- [ ] Refactor API services to use common adapter pattern
- [ ] Standardize request/response transformation logic
- [ ] Eliminate duplicate error handling in API layer
- **Impact**: Reduce API service duplication by 40%

### **Phase 3: Documentation & Cleanup (4-6 weeks)**

#### 9. **Backend Documentation**

- [ ] Create README.md for `tripsage/agents/` - agent architecture overview
- [ ] Create README.md for `tripsage_core/services/business/` - service patterns
- [ ] Create README.md for `tripsage_core/services/infrastructure/` - infrastructure setup
- [ ] Create README.md for `tripsage/orchestration/` - LangGraph workflows
- [ ] Create README.md for `tripsage/tools/` - agent tools documentation
- [ ] Add docstring improvements for complex algorithms
- [ ] Update ARCHITECTURE.md files to reflect refactoring changes

#### 10. **Backend Testing Improvements**

- [ ] Update tests for refactored services
- [ ] Ensure 90%+ coverage for new base classes and utilities
- [ ] Add integration tests for error handling decorator
- [ ] Test service registry refactoring
- [ ] Performance test cache mixin implementations

---

## 📋 Frontend Code Quality Tasks (DEFERRED)

> **Note**: Frontend tasks documented for future implementation by frontend developer

### **Phase 1: High Priority Frontend Tasks**

#### 1. **Create Generic Search Card Component**

- [ ] Implement `SearchCard<T>` component in `frontend/src/components/ui/search-card.tsx`
- [ ] Refactor accommodation, activity, destination, trip cards to use generic component
- [ ] Create configurable render props for image, content, actions
- **Impact**: Reduce card component duplication by 60-70%

#### 2. **Implement Generic Search Hook**

- [ ] Create `useGenericSearch<TParams, TResponse>` in `frontend/src/lib/hooks/use-generic-search.ts`
- [ ] Refactor accommodation, activity, destination search hooks
- [ ] Standardize mutation patterns and store integration
- **Impact**: Eliminate 200+ lines of duplicate search logic

#### 3. **Frontend Linting Cleanup**

- [ ] Run `npx biome format . --write` on frontend codebase
- [ ] Run `npx biome lint --apply .` to fix issues
- [ ] Remove console.log statements from production code (25+ files)
- [ ] Fix import organization

#### 4. **Remove Legacy Frontend Code**

- [ ] Remove legacy `ToolInvocation` types from `frontend/src/types/chat.ts`
- [ ] Clean up backward compatibility shims in API routes
- [ ] Remove unused type definitions and imports

### **Phase 2: Medium Priority Frontend Tasks**

#### 5. **Break Down Chat Store**

- [ ] Split 1000+ line chat store into domain stores:
  - `useChatSessionStore` - session management
  - `useChatMessagesStore` - message operations  
  - `useChatWebSocketStore` - WebSocket handling
  - `useChatMemoryStore` - memory integration

#### 6. **Create Common Form Components**

- [ ] Implement `NumberField`, `DateField`, `SelectField` components
- [ ] Standardize form validation patterns with Zod
- [ ] Reduce form duplication across search components

#### 7. **Frontend Documentation**

- [ ] Add JSDoc comments to all exported React components
- [ ] Create README.md files for component directories
- [ ] Document prop interfaces and usage examples

---

## 📊 Success Metrics

### **Backend Completion Targets**

- [ ] **Code Reduction**: 25-30% fewer lines through DRY implementation
- [ ] **Complexity**: Average cyclomatic complexity <8 (currently 10-15)
- [ ] **Coverage**: Maintain 90%+ test coverage through refactoring
- [ ] **Linting**: 100% backend files pass ruff checks
- [ ] **Documentation**: 80% of key directories have README.md files

### **Quality Indicators**

- [ ] **Build Time**: Faster builds due to reduced complexity
- [ ] **Maintainability**: Easier service extension and modification
- [ ] **Consistency**: Standardized patterns across all services
- [ ] **Developer Experience**: Clear documentation and examples

---

## 🚀 Getting Started

### **Immediate Next Steps (This Week)**

1. **Start with error handling decorator** - highest impact, lowest risk
2. **Run linting cleanup** - prepare codebase for refactoring
3. **Remove legacy service registry** - simplify architecture

### **Development Workflow**

1. Create feature branch for each phase
2. Implement changes with tests
3. Run full test suite: `uv run pytest --cov=tripsage`
4. Verify linting: `ruff check . && ruff format .`
5. Update documentation as you go
6. Merge when phase is complete

### **Risk Mitigation**

- **Test thoroughly** before removing legacy code
- **Keep git history** of removed patterns for reference
- **Implement incrementally** - don't change everything at once
- **Verify behavior** matches before/after refactoring

---

*Last Updated: 2025-01-06*
*Estimated Timeline: 6-8 weeks for complete backend implementation*
