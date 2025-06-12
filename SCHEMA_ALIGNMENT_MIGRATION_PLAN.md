# Schema Alignment Migration Plan

## Overview
This document outlines the comprehensive migration strategy to align schema mismatches between frontend, backend, and database layers in the TripSage application.

## Critical Schema Mismatches Identified

### 1. ID Type Inconsistencies
- **Database**: BIGINT (auto-generated identity)
- **Backend Core Model**: Optional[int] 
- **Backend Service Layer**: str
- **API Layer**: UUID
- **Frontend**: string

**Impact**: Data type conversion errors, inconsistent ID handling across layers

### 2. Field Naming Mismatches
- **Database**: `name` field for trips
- **Backend Core Model**: `name` field
- **Backend Service Layer**: `title` field
- **API Layer**: `title` field
- **Frontend**: Both `name` and `title` for compatibility

**Impact**: Field mapping errors, confusion in development

### 3. Missing Database Fields
The database `trips` table is missing:
- `description` TEXT field
- `visibility` TEXT field (private/shared/public)
- `tags` TEXT[] field
- Complex `preferences` structure
- Proper budget breakdown

**Impact**: Data loss, incomplete feature implementation

### 4. Date/Time Type Mismatches
- **Database**: DATE type for start_date/end_date
- **Service Layer**: datetime objects
- **API Layer**: date objects
- **Frontend**: string dates with mixed casing

**Impact**: Timezone issues, date parsing errors

## Migration Strategy

### Phase 1: Database Schema Updates

#### 1.1 Trip Table Enhancement
```sql
-- Add missing fields to trips table
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'private' CHECK (visibility IN ('private', 'shared', 'public')),
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS preferences_extended JSONB DEFAULT '{}';

-- Rename name to title for consistency
ALTER TABLE trips RENAME COLUMN name TO title;

-- Update constraints
ALTER TABLE trips ADD CONSTRAINT trips_visibility_check CHECK (visibility IN ('private', 'shared', 'public'));
```

#### 1.2 Budget Structure Enhancement
```sql
-- Add budget breakdown fields
ALTER TABLE trips 
ADD COLUMN IF NOT EXISTS budget_breakdown JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD',
ADD COLUMN IF NOT EXISTS spent_amount NUMERIC DEFAULT 0;
```

#### 1.3 ID Standardization Strategy
```sql
-- Create UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add UUID column for new ID system
ALTER TABLE trips ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT uuid_generate_v4();

-- Create index on UUID for performance
CREATE INDEX IF NOT EXISTS idx_trips_uuid_id ON trips(uuid_id);
```

### Phase 2: Backend Layer Alignment

#### 2.1 Core Model Updates
- Standardize Trip model to use `title` instead of `name`
- Add missing fields: description, visibility, tags, preferences
- Implement proper budget structure
- Add UUID support with fallback to BIGINT

#### 2.2 Service Layer Updates
- Update TripService to handle both ID types during transition
- Add field mapping utilities for legacy compatibility
- Implement proper date/time handling

#### 2.3 API Layer Updates
- Update API schemas to match database fields
- Add backward compatibility for field name changes
- Implement proper validation for new fields

### Phase 3: Frontend Layer Alignment

#### 3.1 Type Definition Updates
- Standardize trip interface to use consistent field names
- Add proper TypeScript types for new fields
- Remove duplicate field names

#### 3.2 Store Updates
- Update trip store to handle new schema
- Add migration utilities for local storage
- Implement proper date handling

### Phase 4: Data Migration

#### 4.1 Existing Data Migration
```sql
-- Migrate existing data to new structure
UPDATE trips SET 
  preferences_extended = COALESCE(
    jsonb_build_object(
      'budget', jsonb_build_object(
        'total', budget,
        'currency', 'USD',
        'spent', 0
      ),
      'flexibility', flexibility
    ),
    '{}'::jsonb
  )
WHERE preferences_extended = '{}'::jsonb;
```

#### 4.2 Mem0 Integration Assessment
- Current Mem0 integration uses pgvector with memories table
- Compatible with enhanced trip schema
- No breaking changes required for memory system
- Enhanced preferences field can improve memory context

## Implementation Timeline

### Week 1: Database Schema Migration
- [ ] Create migration scripts
- [ ] Test migration on development environment
- [ ] Backup production data
- [ ] Apply schema changes

### Week 2: Backend Alignment
- [ ] Update core models
- [ ] Implement service layer changes
- [ ] Update API schemas
- [ ] Add backward compatibility layers

### Week 3: Frontend Updates
- [ ] Update TypeScript interfaces
- [ ] Modify stores and hooks
- [ ] Update components to use new schema
- [ ] Test cross-layer compatibility

### Week 4: Testing & Deployment
- [ ] Comprehensive testing
- [ ] Performance validation
- [ ] Production deployment
- [ ] Monitor for issues

## Backward Compatibility Strategy

### 1. Dual Field Support
- Support both `name` and `title` fields during transition
- API layer will accept both but normalize to `title`
- Frontend will handle both for existing data

### 2. ID Type Compatibility
- Service layer will handle both BIGINT and UUID IDs
- API will accept string IDs and convert appropriately
- Database will maintain both ID systems during transition

### 3. Gradual Migration
- New features use enhanced schema
- Existing features maintain compatibility
- Gradual deprecation of legacy fields

## Risk Mitigation

### 1. Data Integrity
- Full database backup before migration
- Reversible migration scripts
- Data validation checks at each step

### 2. Service Continuity
- Feature flags for new schema
- Rollback procedures
- Monitoring and alerting

### 3. Testing Coverage
- Unit tests for all schema changes
- Integration tests for cross-layer compatibility
- End-to-end tests for user workflows

## Success Metrics

### 1. Technical Metrics
- Zero data loss during migration
- 100% backward compatibility for existing APIs
- < 100ms performance impact on trip operations

### 2. Quality Metrics
- 90%+ test coverage for schema changes
- Zero critical bugs in production
- Complete field alignment across all layers

### 3. Functional Metrics
- All new fields properly supported
- Enhanced preferences working correctly
- Trip collaboration features fully functional

## Post-Migration Cleanup

### Phase 5: Legacy Removal (After 30 days)
- Remove dual field support
- Drop old BIGINT ID system
- Clean up backward compatibility code
- Update documentation

This migration plan ensures minimal disruption while achieving complete schema alignment across all layers of the TripSage application.