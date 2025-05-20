"""OpenAPI configuration for the TripSage API.

This module provides configuration for OpenAPI documentation, including
custom examples, tags, and extensions.
"""

from fastapi.openapi.utils import get_openapi

from tripsage.api.core.config import get_settings

# API metadata
settings = get_settings()
API_TITLE = "TripSage API"
API_DESCRIPTION = """
# TripSage Travel Planning API

This API provides endpoints for travel planning, including:

* User authentication and management
* API key management (BYOK - Bring Your Own Key)
* Trip planning and management
* Flight search and booking
* Accommodation search and booking
* Destination research
* Weather information
* Maps and directions

## Authentication

The API supports two authentication methods:
* OAuth2 with JWT tokens (for user authentication)
* API key authentication (for service-to-service communication)

### JWT Authentication

To authenticate with JWT, obtain a token by making a POST request to `/api/auth/token`
with your email and password. Then include the token in the `Authorization` header of 
subsequent requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwidXNlcl9pZCI6ImFiYzEyMyIsImV4cCI6MTcwOTgxNjQ2Mi44MTk1OTJ9.XXXXXXXXXXXXXXXXXXXXX
```

### API Key Authentication

For service-to-service communication, you can use API keys. Include the API key in the 
`X-API-Key` header of your requests:

```
X-API-Key: YOUR_API_KEY
```

## Rate Limiting

The API implements rate limiting to prevent abuse. By default, clients are limited to
100 requests per minute. If you exceed this limit, you will receive a 429 Too Many
Requests response.

## Error Handling

The API uses standard HTTP status codes and returns error responses in a consistent format:

```json
{
  "status": "error",
  "message": "Error message",
  "error_code": "error_code",
  "details": {}
}
```
"""
API_VERSION = "1.0.0"
API_CONTACT = {
    "name": "TripSage API Team",
    "url": "https://github.com/BjornMelin/tripsage-ai",
    "email": "api@tripsage.example.com",
}
API_LICENSE = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}
API_TERMS = "https://tripsage.example.com/terms/"


# Tags with descriptions for API endpoints
TAG_DESCRIPTIONS = [
    {
        "name": "health",
        "description": "Health check endpoints",
    },
    {
        "name": "auth",
        "description": "Authentication endpoints for user registration, login, and token management",
    },
    {
        "name": "users",
        "description": "User management endpoints",
    },
    {
        "name": "api_keys",
        "description": "API key management endpoints (BYOK - Bring Your Own Key)",
    },
    {
        "name": "trips",
        "description": "Trip planning and management endpoints",
    },
    {
        "name": "flights",
        "description": "Flight search and booking endpoints",
    },
    {
        "name": "accommodations",
        "description": "Accommodation search and booking endpoints",
    },
]


# Example responses for different endpoints
EXAMPLES = {
    "auth_token": {
        "summary": "User authentication response",
        "description": "Response when user authentication is successful",
        "value": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_at": "2023-07-27T12:34:56.789Z",
        },
    },
    "user_response": {
        "summary": "User information",
        "description": "Response with user information",
        "value": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "user@example.com",
            "full_name": "John Doe",
            "created_at": "2023-07-27T12:34:56.789Z",
            "updated_at": "2023-07-27T12:34:56.789Z",
        },
    },
    "api_key_response": {
        "summary": "API key information",
        "description": "Response with API key information",
        "value": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "OpenAI API Key",
            "service": "openai",
            "description": "OpenAI API key for GPT-4",
            "created_at": "2023-07-27T12:34:56.789Z",
            "updated_at": "2023-07-27T12:34:56.789Z",
            "expires_at": "2024-07-27T12:34:56.789Z",
            "is_valid": True,
            "last_used": "2023-07-27T12:34:56.789Z",
        },
    },
    "api_key_validate_response": {
        "summary": "API key validation result",
        "description": "Response with API key validation result",
        "value": {
            "is_valid": True,
            "service": "openai",
            "message": "API key is valid",
        },
    },
    "error_response": {
        "summary": "Error response",
        "description": "Response when an error occurs",
        "value": {
            "status": "error",
            "message": "Error message",
            "error_code": "error_code",
            "details": {},
        },
    },
    "health_response": {
        "summary": "Health check response",
        "description": "Response when the health check is successful",
        "value": {
            "status": "ok",
            "application": "TripSage API",
            "version": "1.0.0",
            "environment": "development",
        },
    },
}


def custom_openapi(app):
    """Create a custom OpenAPI schema for the FastAPI application.
    
    Args:
        app: The FastAPI application
        
    Returns:
        The custom OpenAPI schema
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
        contact=API_CONTACT,
        license_info=API_LICENSE,
        terms_of_service=API_TERMS,
    )
    
    # Add tags with descriptions
    openapi_schema["tags"] = TAG_DESCRIPTIONS
    
    # Add examples to components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}
    
    openapi_schema["components"]["examples"].update(EXAMPLES)
    
    # Add security schemes
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    # Add JWT security scheme
    openapi_schema["components"]["securitySchemes"]["jwt"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT authentication",
    }
    
    # Add API key security scheme
    openapi_schema["components"]["securitySchemes"]["api_key"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key authentication",
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema