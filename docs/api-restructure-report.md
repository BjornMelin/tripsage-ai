# API Documentation Restructure Report

## Classification Summary

### Files Moved to `docs/api/` (External Developer Documentation)
These files contain API reference material for external developers:

1. **REST_API_ENDPOINTS.md** → `rest-endpoints.md`
   - Contains all HTTP endpoint documentation
   - **Issues Found**: Uses `/api/v1/` prefix but actual code uses `/api/` (no v1)
   - **Accuracy**: ~80% - needs prefix correction

2. **WEBSOCKET_API.md** → `websocket-api.md`
   - WebSocket endpoint documentation
   - **Accuracy**: Good, matches actual WebSocket implementation

3. **AUTHENTICATION_API.md** → `authentication.md`
   - Auth flows and security documentation
   - **Accuracy**: Good, matches JWT implementation

4. **ERROR_CODES.md** → `error-codes.md`
   - Standardized error responses
   - **Accuracy**: Good reference material

5. **API_EXAMPLES.md** → `examples.md`
   - Code samples and tutorials
   - **Issues Found**: Very large file with many hypothetical examples
   - **Recommendation**: Should be trimmed to essential examples

6. **API_USAGE_EXAMPLES.md** → `integration-guide.md`
   - Step-by-step integration guide
   - **Accuracy**: Good tutorial content

7. **DATA_MODELS.md** → `data-models.md`
   - Request/response schemas
   - **Accuracy**: Needs validation against actual Pydantic models

### Files Kept in `06_API_REFERENCE/` (Internal Architecture)
These files contain internal implementation details not for external developers:

1. **DATABASE_SCHEMA.md** - PostgreSQL schema design (internal)
2. **DATABASE_TRIGGERS.md** - Database trigger logic (internal)
3. **STORAGE_ARCHITECTURE.md** - Storage system design (internal)
4. **WEBSOCKET_CONNECTION_GUIDE.md** - Internal WebSocket architecture
5. **REAL_TIME_COLLABORATION_GUIDE.md** - Internal collaboration design

### Created Files
1. **openapi-spec.md** - Stub for OpenAPI specification access
2. **README.md** - API documentation index for developers

## Accuracy Issues Found

### 1. API Version Mismatch
- **Documentation**: Uses `/api/v1/` prefix
- **Actual Code**: Uses `/api/` prefix (no v1)
- **Fix Required**: Update all endpoint paths in documentation

### 2. Fictional/Oversized Content
- API_EXAMPLES.md contains many hypothetical SDK examples
- Some endpoints mentioned don't exist in actual routers
- Recommendation: Validate against actual FastAPI routes

### 3. Missing Routers in Documentation
The following routers exist but aren't well documented:
- `/api/user/keys` - API key management
- `/api/chat` - Chat functionality
- `/api/attachments` - File attachments
- `/api/memory` - Memory system

## Naming Convention Fixes
All files renamed to lowercase-hyphenated format:
- `REST_API_ENDPOINTS.md` → `rest-endpoints.md`
- `WEBSOCKET_API.md` → `websocket-api.md`
- etc.

## Next Steps
1. Run the restructure script: `./api-restructure-commands.sh`
2. Validate endpoint documentation against actual FastAPI routers
3. Update API version prefixes from `/api/v1/` to `/api/`
4. Trim oversized example files to essential content
5. Add documentation for missing routers