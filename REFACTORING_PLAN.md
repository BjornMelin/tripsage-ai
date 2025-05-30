# API Services Refactoring Plan

## Overview

Refactor all service classes in `api/services/` to act as thin wrappers that delegate to core business services in `tripsage_core.services.business/`.

## Current Services Analysis

### 1. `api/services/auth_service.py` (418 lines)

**Current Issues:**

- Contains extensive business logic (password hashing, JWT creation, user management)
- Direct database access via Supabase
- Duplicates functionality that should be in core services

**Refactoring Plan:**

- Remove all business logic
- Delegate to `tripsage_core.services.business.auth_service.AuthenticationService`
- Handle API model adaptation between frontend and core models
- Maintain FastAPI dependency injection compatibility

### 2. `api/services/key_service.py` (344 lines)

**Current Issues:**

- Contains business logic for key validation and storage
- Direct database access
- Duplicates `tripsage_core.services.business.key_management_service.KeyManagementService`

**Refactoring Plan:**

- Remove all business logic
- Delegate to `tripsage_core.services.business.key_management_service.KeyManagementService`
- Handle model adaptation between API and core models
- Maintain FastAPI dependency injection

### 3. `api/services/trip_service.py` (111 lines)

**Current Status:**

- Already partially refactored as thin wrapper
- Delegates to `tripsage_core.services.business.trip_service.TripService`

**Refactoring Plan:**

- Review and improve error handling
- Ensure proper model adaptation
- Add comprehensive testing

## Implementation Steps

### Phase 1: Auth Service Refactoring

1. Create API models for auth requests/responses
2. Refactor `AuthService` to delegate to core `AuthenticationService`
3. Handle model adaptation
4. Update dependency injection
5. Create comprehensive tests

### Phase 2: Key Service Refactoring

1. Create API models for key management
2. Refactor `KeyService` to delegate to core `KeyManagementService`
3. Handle model adaptation
4. Update dependency injection
5. Create comprehensive tests

### Phase 3: Trip Service Enhancement

1. Review current implementation
2. Improve error handling and model adaptation
3. Enhance testing coverage

### Phase 4: Testing and Validation

1. Ensure 80%+ test coverage for all refactored services
2. Integration testing
3. Performance validation
4. Security review

## Model Adaptation Strategy

### API Models Location

- Request models: `api/schemas/requests/`
- Response models: `api/schemas/responses/`

### Core Models Location

- Business models: `tripsage_core/models/`
- Service models: `tripsage_core/services/business/`

### Adaptation Patterns

1. **Request Adaptation**: API request models → Core service models
2. **Response Adaptation**: Core service models → API response models
3. **Error Handling**: Core exceptions → API-appropriate HTTP responses

## Dependency Injection Strategy

### FastAPI Dependencies

- Use `Depends()` for service injection
- Create factory functions for service instantiation
- Ensure proper lifecycle management

### Service Dependencies

- Core services should be injected into API services
- Use dependency injection for database services
- Maintain loose coupling between layers

## Testing Strategy

### Unit Tests

- Test each API service in isolation
- Mock core service dependencies
- Test model adaptation logic
- Test error handling scenarios

### Integration Tests

- Test full request/response cycles
- Test with real core services
- Validate end-to-end functionality

### Coverage Goals

- Minimum 80% code coverage
- 100% coverage for critical paths
- Comprehensive error scenario testing
