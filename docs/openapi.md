# OpenAPI Specification

The TripSage AI API is fully documented using the OpenAPI 3.0 specification. This interactive documentation allows you to explore all available endpoints, request/response formats, and authentication requirements.

## Interactive API Explorer

Below is the complete OpenAPI specification for the TripSage AI API. You can:

- View detailed endpoint documentation
- Test API calls directly from your browser
- Download the OpenAPI JSON specification
- Generate client SDKs in various programming languages

!!! note "API Base URL"
All endpoints are relative to the base URL: `https://api.tripsage.ai/v1`

!!! tip "Authentication Required"
Most endpoints require authentication via Bearer token. See the [Authentication guide](auth.md) for details.

## API Specification Details

The OpenAPI specification has been generated and is available for download and exploration. You can use external tools like Swagger UI to view the interactive documentation.

The specification includes all endpoints, request/response schemas, authentication requirements, and examples.

## Download

- [Download OpenAPI JSON](openapi.json) - Raw specification file
- [View in Swagger UI](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/tripsage-ai/tripsage-ai/main/docs/openapi.json) - External Swagger UI viewer

## Code Generation

You can generate client libraries in various languages using the OpenAPI specification:

```bash
# Generate Python client
openapi-generator-cli generate -i docs/openapi.json -g python -o client/python

# Generate TypeScript client
openapi-generator-cli generate -i docs/openapi.json -g typescript-axios -o client/typescript

# Generate Go client
openapi-generator-cli generate -i docs/openapi.json -g go -o client/go
```

## Schema Validation

The API uses JSON Schema validation for all request/response bodies. The OpenAPI spec includes complete schema definitions for:

- Request parameters and bodies
- Response structures
- Error response formats
- Data models and enums

## Versioning

This documentation reflects the current API version (v1). Breaking changes will be communicated in advance and documented in the [changelog](../../CHANGELOG.md).
