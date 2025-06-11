# TripSage Infrastructure Gap Analysis Report

## Storage/Buckets and Edge Functions Audit

### Executive Summary
This report identifies critical infrastructure gaps in the TripSage Supabase implementation, focusing on storage buckets and edge functions. The application has comprehensive file upload/processing code but lacks the underlying Supabase infrastructure to support it.

### 1. Storage Infrastructure Gaps

#### Missing Storage Buckets
| Resource Type | Referenced in Code | File/Line | Exists in Supabase? | Gap/Action |
|--------------|-------------------|-----------|---------------------|------------|
| Storage Bucket | `file_processing_service.py` | Lines 292-299: StorageService() | ❌ No | Need to create storage buckets |
| File Attachments Table | `file_processing_service.py` | Lines 1154-1156: db.store_file() | ❌ No | Need `file_attachments` table |
| Storage Policies | Not implemented | N/A | ❌ No | Need RLS policies for buckets |

#### Code References Without Infrastructure:
1. **File Processing Service** (`tripsage_core/services/business/file_processing_service.py`):
   - Attempts to use `StorageService` (lines 289-299)
   - Falls back to local storage when service unavailable
   - References database methods that don't exist:
     - `db.store_file()` (line 1155)
     - `db.get_file()` (line 605)
     - `db.delete_file()` (line 764)
     - `db.get_file_by_hash()` (line 983)
     - `db.search_files()` (line 715)
     - `db.get_file_usage_stats()` (line 794)
     - `db.update_file()` (line 1167)

2. **Attachment Router** (`tripsage/api/routers/attachments.py`):
   - Fully implemented endpoints for:
     - POST `/upload` - Single file upload
     - POST `/upload/batch` - Batch file upload
     - GET `/files/{file_id}` - Get file metadata
     - DELETE `/files/{file_id}` - Delete file
     - GET `/files` - List user files
   - All endpoints rely on non-existent infrastructure

### 2. Missing Database Schema

#### Required Tables Not Found:
```sql
-- Missing: file_attachments table
CREATE TABLE IF NOT EXISTS file_attachments (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trip_id BIGINT REFERENCES trips(id) ON DELETE SET NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_type TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    storage_provider TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    storage_url TEXT,
    processing_status TEXT NOT NULL,
    upload_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_timestamp TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    analysis_result JSONB,
    visibility TEXT DEFAULT 'private',
    shared_with UUID[],
    tags TEXT[],
    version INT DEFAULT 1,
    parent_file_id TEXT,
    download_count INT DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. Storage Configuration Status

#### Supabase config.toml Settings:
- ✅ Storage enabled: `enabled = true` (line 42)
- ✅ Storage port configured: `port = 54328` (line 43)
- ✅ File size limit set: `file_size_limit = "50MiB"` (line 44)
- ✅ Image transformation enabled: `image_transformation = { enabled = true }` (line 45)
- ❌ No bucket configurations found
- ❌ No storage policies defined

### 4. Edge Functions Status

#### Edge Runtime Configuration:
- ✅ Edge runtime enabled: `enabled = true` (line 75 in config.toml)
- ✅ Port configured: `port = 54330` (line 76)
- ✅ Inspector port: `inspector_port = 54331` (line 77)
- ❌ No edge functions deployed
- ❌ No functions directory structure

#### Missing Edge Functions:
1. No `/supabase/functions` directory
2. No edge function implementations found
3. Document analyzer service references external AI but no edge function

### 5. External Service Integration Gaps

#### Document Analyzer Service:
- Referenced in `file_processing_service.py` (lines 302-310)
- Import path: `tripsage_core.services.external_apis.document_analyzer`
- ✅ Service exists: `document_analyzer.py`
- ❌ No Supabase edge function wrapper

#### Virus Scanner Service:
- Referenced in `file_processing_service.py` (lines 312-321)
- Import path: `tripsage_core.services.external_apis.virus_scanner`
- ❌ Service doesn't exist
- ❌ No implementation found

### 6. Security & Policy Gaps

#### Missing Storage Policies:
1. No RLS policies for storage buckets
2. No file access control policies
3. No virus scanning integration
4. No file type validation at storage level

### 7. Implementation Priorities

#### Critical (P0) - Block Production:
1. Create `file_attachments` table in database schema
2. Implement database methods in `DatabaseService`
3. Create storage buckets via Supabase dashboard/CLI
4. Implement storage RLS policies

#### High (P1) - Core Functionality:
1. Create `StorageService` implementation for Supabase
2. Deploy edge functions for document analysis
3. Implement file deduplication logic
4. Add storage bucket policies

#### Medium (P2) - Enhanced Features:
1. Implement virus scanning service
2. Add image transformation edge functions
3. Create file sharing mechanisms
4. Implement usage analytics

### 8. Recommended Actions

#### Immediate Steps:
1. **Database Migration**: Create new migration file for `file_attachments` table
2. **Storage Buckets**: Create via Supabase CLI:
   ```bash
   supabase storage create trip-attachments
   supabase storage create user-documents
   supabase storage create temp-uploads
   ```

3. **Implement Database Methods**: Add to `database_service.py`:
   - `store_file()`
   - `get_file()`
   - `delete_file()`
   - `get_file_by_hash()`
   - `search_files()`
   - `get_file_usage_stats()`
   - `update_file()`

4. **Create Storage Service**: Implement Supabase storage adapter

5. **Storage Policies**: Create RLS policies for buckets

### 9. Risk Assessment

#### High Risk Items:
- **File uploads fail silently**: Current code falls back to local storage
- **No persistence**: Files stored locally will be lost on deployment
- **Security gap**: No virus scanning or content validation
- **Data loss risk**: No backup mechanism for uploaded files

#### Mitigation Strategy:
1. Disable file upload endpoints until infrastructure ready
2. Implement proper error handling for missing services
3. Add feature flags for file upload functionality
4. Create monitoring for storage usage

### 10. Conclusion

The TripSage application has a well-architected file processing system at the application layer, but lacks the underlying Supabase infrastructure to support it. The code gracefully degrades to local storage, but this is not suitable for production. Immediate action is required to create the necessary database tables, storage buckets, and policies before enabling file upload features in production.

---
**Generated**: 2025-01-11
**Status**: Critical Infrastructure Gaps Identified
**Next Review**: After implementing P0 items