# TripSage Schema Consolidation Plan

## Overview
Consolidate duplicate Pydantic models between API and service layers following FastAPI best practices and Pydantic V2 patterns.

## Current State Analysis
- **API Schemas**: `/tripsage/api/schemas/` - Request/Response models for endpoints
- **Service Models**: `/tripsage_core/services/business/` - Business logic models 
- **Domain Models**: `/tripsage_core/models/domain/` - Core domain entities
- **DB Models**: `/tripsage_core/models/db/` - Database persistence models
- **Common Schemas**: `/tripsage_core/models/schemas_common/` - Shared types and validators

## Identified Duplications

### Flight Models
- `CabinClass` - Defined in API schemas, service, and domain layers
- `FlightSearchRequest` - API vs Service versions
- `BookingStatus` - Multiple definitions
- `Airport` - Response model vs domain model

### Accommodation Models
- `AccommodationType` - Multiple definitions
- `AccommodationSearchRequest` - API vs potential service version
- Location/amenity models

### User/Auth Models
- User response models vs domain models
- Auth request/response vs service models

## Consolidation Strategy

### Phase 1: Establish Single Source of Truth
**Location**: Use `tripsage_core/models/schemas_common/` as the canonical location for:
- Enums (CabinClass, BookingStatus, etc.)
- Common validators and types
- Base models

**Location**: Use `tripsage_core/models/domain/` for:
- Core business entities (Flight, Accommodation, User, Trip)
- Domain-specific models

### Phase 2: Consolidate Request/Response Models  
**Keep API-specific schemas only for**:
- Request models with API-specific validation
- Response models with API-specific formatting
- Models that differ significantly from domain models

**Move to service layer**:
- Models that are identical between API and service
- Search request models
- Common response formatting

### Phase 3: Update Import Structure
```python
# API routers will import from:
from tripsage_core.models.domain.flight import FlightOffer, Airport
from tripsage_core.models.schemas_common import CabinClass, BookingStatus
from tripsage_core.services.business.flight_service import FlightSearchRequest

# Only keep API-specific models in tripsage.api.schemas
from tripsage.api.schemas.flights import FlightSearchResponse  # If API-specific formatting needed
```

## Implementation Steps

### Step 1: Consolidate Common Enums and Types
- [x] Move all enums to `schemas_common/enums.py`
- [x] Update imports across codebase
- [x] Remove duplicate enum definitions

### Step 2: Consolidate Domain Models
- [ ] Review domain models for consistency
- [ ] Ensure proper Pydantic V2 model_config usage
- [ ] Standardize field definitions and validators

### Step 3: Eliminate Duplicate Request Models
- [ ] Remove duplicate `FlightSearchRequest` from API schemas
- [ ] Use service layer models directly in API routes
- [ ] Update router imports

### Step 4: Streamline Response Models
- [ ] Keep only API-specific response models in API schemas
- [ ] Use domain models directly where possible
- [ ] Add response formatting in routers if needed

### Step 5: Update All Imports
- [ ] Update API router imports
- [ ] Update service imports  
- [ ] Update test imports
- [ ] Remove unused schema files

### Step 6: Verification
- [ ] Run full test suite
- [ ] Verify API endpoints work correctly
- [ ] Check OpenAPI docs generation
- [ ] Performance validation

## Files to Modify

### Remove/Consolidate:
- `tripsage/api/schemas/flights.py` - Consolidate with service models
- Duplicate enum definitions across layers
- Redundant request models

### Update:
- All API routers to use consolidated imports
- Service layer to be canonical source
- Tests to use new import paths

### Keep:
- API-specific response formatting models
- Request models with unique API validation
- Domain models in `tripsage_core/models/domain/`

## Expected Benefits
1. **Reduced Maintenance**: Single source of truth for schemas
2. **Better Consistency**: Unified validation and types
3. **Improved Performance**: Less object creation/conversion
4. **Cleaner Architecture**: Clear separation of concerns
5. **Easier Testing**: Consistent models across layers

## Migration Notes
- Use Pydantic V2 `model_config` consistently
- Maintain backward compatibility during transition
- Update documentation to reflect new import patterns
- Consider deprecation warnings for old imports

## Success Criteria
- [ ] Zero duplicate model definitions
- [ ] All API endpoints functional 
- [ ] Test suite passes
- [ ] OpenAPI docs generate correctly
- [ ] Import structure follows FastAPI best practices