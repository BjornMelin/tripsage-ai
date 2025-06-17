#!/bin/bash
# API Documentation Restructure - Move external developer docs to docs/api/

# Create the API documentation directory
mkdir -p docs/api

# Move API reference files for external developers
# Fix naming to lowercase-hyphenated format
mv 06_API_REFERENCE/REST_API_ENDPOINTS.md docs/api/rest-endpoints.md
mv 06_API_REFERENCE/WEBSOCKET_API.md docs/api/websocket-api.md
mv 06_API_REFERENCE/AUTHENTICATION_API.md docs/api/authentication.md
mv 06_API_REFERENCE/ERROR_CODES.md docs/api/error-codes.md
mv 06_API_REFERENCE/API_EXAMPLES.md docs/api/examples.md
mv 08_USER_GUIDES/API_USAGE_EXAMPLES.md docs/api/integration-guide.md

# Move data models (needed for API reference)
mv 06_API_REFERENCE/DATA_MODELS.md docs/api/data-models.md

# Create missing OpenAPI spec stub
cat > docs/api/openapi-spec.md << 'EOF'
# OpenAPI Specification

> **Status**: 🚧 Under Construction  
> **Version**: OpenAPI 3.0.3

## Overview

The TripSage API OpenAPI specification provides a machine-readable description of all API endpoints, request/response schemas, and authentication requirements.

## Access Methods

### 1. Interactive Documentation
- **Development**: http://localhost:8000/docs (Swagger UI)
- **Production**: https://api.tripsage.ai/docs

### 2. OpenAPI JSON
- **Development**: http://localhost:8000/openapi.json
- **Production**: https://api.tripsage.ai/openapi.json

### 3. ReDoc Documentation
- **Development**: http://localhost:8000/redoc
- **Production**: https://api.tripsage.ai/redoc

## Generating Client SDKs

Use the OpenAPI specification to generate client libraries:

```bash
# JavaScript/TypeScript
npx @openapitools/openapi-generator-cli generate \
  -i https://api.tripsage.ai/openapi.json \
  -g typescript-axios \
  -o ./generated/typescript-client

# Python
openapi-generator generate \
  -i https://api.tripsage.ai/openapi.json \
  -g python \
  -o ./generated/python-client
```

## API Versioning

- Current version: v1
- Base path: `/api`
- Full base URL: `https://api.tripsage.ai/api`

EOF

# Create API index/README
cat > docs/api/README.md << 'EOF'
# TripSage API Documentation

> **For External Developers**  
> Complete API reference for integrating with TripSage

## Quick Links

- [REST API Endpoints](./rest-endpoints.md) - All HTTP endpoints
- [WebSocket API](./websocket-api.md) - Real-time communication
- [Authentication](./authentication.md) - Auth flows and security
- [Data Models](./data-models.md) - Request/response schemas
- [Error Codes](./error-codes.md) - Error handling reference
- [Examples](./examples.md) - Code samples and tutorials
- [Integration Guide](./integration-guide.md) - Step-by-step integration
- [OpenAPI Spec](./openapi-spec.md) - Machine-readable API definition

## Base Configuration

- **Base URL**: `https://api.tripsage.ai/api`
- **Version**: v1
- **Authentication**: Bearer JWT tokens
- **Content-Type**: `application/json`

## Getting Started

1. [Register for API access](./authentication.md#api-registration)
2. [Authenticate and get JWT token](./authentication.md#jwt-authentication)
3. [Make your first API call](./examples.md#quick-start)

## Rate Limits

- Standard tier: 1000 requests/hour
- Premium tier: 10000 requests/hour
- Enterprise: Custom limits

## Support

- API Status: https://status.tripsage.ai
- Developer Portal: https://developers.tripsage.ai
- Support: api-support@tripsage.ai

EOF

# Files to keep in 06_API_REFERENCE (internal/architecture docs)
echo "Files remaining in 06_API_REFERENCE (internal architecture):"
echo "- DATABASE_SCHEMA.md (internal database architecture)"
echo "- DATABASE_TRIGGERS.md (internal database logic)"
echo "- STORAGE_ARCHITECTURE.md (internal storage design)"
echo "- WEBSOCKET_CONNECTION_GUIDE.md (internal WebSocket architecture)"
echo "- REAL_TIME_COLLABORATION_GUIDE.md (internal collaboration design)"

# Clean up empty directories if needed
rmdir 08_USER_GUIDES 2>/dev/null || true

echo "API documentation restructure complete!"