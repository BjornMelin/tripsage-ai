"""OpenAPI configuration for the TripSage API.

This module provides configuration for OpenAPI documentation, including
custom examples, tags, and extensions.
"""

from typing import Any, TypedDict, cast

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from tripsage.api.core.config import get_settings


# API metadata
settings = get_settings()
API_TITLE = "TripSage Unified API"
API_DESCRIPTION = """
# TripSage Unified Travel Planning API

A FastAPI implementation that serves both frontend applications
and AI agents for travel planning.

## Dual Consumer Architecture

This API is designed to serve multiple consumer types with adapted responses:

### Frontend Consumers (Next.js Web Application)
- **User-friendly error messages** - Simplified, actionable descriptions
- **UI metadata** - Display hints, pagination, and user context
- **Standard rate limits** - Optimized for human interaction patterns
- **Sanitized data** - Secure, filtered responses for web display

### AI Agent Consumers (LangGraph-based Agents)
- **Rich context data** - Technical details for decision making
- **Tool integration metadata** - Information for agent tool calling
- **Higher rate limits** - Higher throughput for automated workflows
- **Raw data access** - Unfiltered data for AI processing

## Core Capabilities

### Travel Planning & Management
* **Trip Planning** - Travel itinerary creation and optimization
* **Flight Search & Booking** - Multi-provider flight search with price tracking
* **Accommodation Search** - Hotel and alternative lodging with MCP integration
* **Destination Research** - AI-powered insights and recommendations
* **Itinerary Building** - Intelligent scheduling and route optimization

### AI & Communication
* **Chat System** - Conversation management with AI agents
* **Memory & Context** - Persistent conversation memory and user learning
* **Real-time Communication** - Realtime (Supabase) support for live updates
* **File Processing** - Document analysis and travel document extraction

### Authentication & Security
* **Dual Authentication** - JWT tokens for users, API keys for agents
* **BYOK (Bring Your Own Key)** - Secure user-provided API key management
* **Rate Limiting** - Consumer-aware limits with enhanced principal tracking
* **Data Protection** - AES-256 encryption for sensitive data

## Authentication Methods

### JWT Authentication (Primary for Frontend)
Obtain a token via `/api/v1/auth/token`, then include in the Authorization header:

```
POST /api/v1/auth/token
{
  "username": "user@example.com",
  "password": "secure_password"
}

Authorization: Bearer <jwt_token>
```

### API Key Authentication (Primary for Agents)
Create an API key via `/api/v1/keys`, then use in the X-API-Key header:

```
POST /api/v1/keys (with JWT auth)
{
  "description": "Agent access key"
}

X-API-Key: <api_key>
```

### BYOK (Bring Your Own Key) System
Store encrypted user API keys for external services:

```
POST /api/v1/keys
{
  "service": "duffel",
  "api_key": "user_provided_key",
  "description": "My Duffel API key"
}
```

## Consumer-Specific Response Formats

### Frontend Response Example
```json
{
  "data": [...],
  "meta": {
    "ui_hints": {
      "show_loading": false,
      "suggested_actions": ["book_now", "save_for_later"]
    },
    "pagination": {
      "page": 1,
      "total_pages": 5,
      "has_next": true
    }
  }
}
```

### Agent Response Example
```json
{
  "data": [...],
  "agent_context": {
    "tool_suggestions": ["search_alternatives", "check_price_history"],
    "reasoning_context": "User prefers budget options",
    "confidence_score": 0.95
  }
}
```

## Performance Features

* **Multi-tier Caching** - DragonflyDB with intelligent TTL (25x improvement)
* **Consumer-aware Rate Limiting** - Higher limits for agents vs. frontend
* **Connection Pooling** - Optimized database and external API connections
* **Query Optimization** - Indexed searches and prepared statements

## Rate Limiting

Consumer-aware rate limiting with different limits:

* **Frontend Users**: 100 requests/minute, 1000 requests/hour
* **AI Agents**: 500 requests/minute, 5000 requests/hour
* **Authenticated Users**: 5x multiplier on base limits
* **BYOK Users**: Higher limits when using own API keys

## Error Handling

The API returns consumer-specific error formats:

### Frontend Error Format
```json
{
  "error": {
    "type": "validation_error",
    "message": "Please check your travel dates",
    "field": "departure_date",
    "suggestion": "Departure date must be in the future"
  }
}
```

### Agent Error Format
```json
{
  "error": {
    "type": "external_api_error",
    "service": "duffel",
    "status_code": 429,
    "retry_after": 60,
    "fallback_available": true,
    "technical_details": "Rate limit exceeded for flight search endpoint"
  }
}
```

## Real-time Features

Real-time messaging is provided via Supabase Realtime private channels with RLS
authorization (no custom Realtime (Supabase) endpoints).

## Integration with TripSage Core

This API leverages the `tripsage_core` shared library for:

* **Business Services** - Flight, accommodation, memory, and chat services
* **Infrastructure Services** - Database, caching, and Realtime (Supabase) management
* **External API Integration** - Standardized patterns for third-party services
* **Security & Configuration** - Centralized settings and encryption
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
        "description": "Health check and monitoring endpoints",
    },
    {
        "name": "auth",
        "description": (
            "Authentication endpoints for user registration, login, "
            "and JWT token management. Primary authentication method "
            "for frontend consumers."
        ),
    },
    {
        "name": "api_keys",
        "description": (
            "API key management endpoints (BYOK - Bring Your Own Key). "
            "Supports both system API keys for agents and user-provided "
            "external service keys."
        ),
    },
    {
        "name": "trips",
        "description": (
            "Trip planning and management endpoints. Supports travel "
            "itinerary creation and optimization."
        ),
    },
    {
        "name": "flights",
        "description": (
            "Flight search and booking endpoints with multi-provider support. "
            "Includes price tracking, route optimization, and booking management."
        ),
    },
    {
        "name": "accommodations",
        "description": (
            "Accommodation search and booking endpoints. Supports hotels and "
            "alternative lodging with MCP integration for enhanced search capabilities."
        ),
    },
    {
        "name": "destinations",
        "description": (
            "Destination research endpoints with AI-powered insights. "
            "Provides destination information, weather, "
            "and recommendations."
        ),
    },
    {
        "name": "itineraries",
        "description": (
            "Itinerary building and optimization endpoints. "
            "Intelligent trip scheduling with route optimization "
            "and activity coordination."
        ),
    },
    {
        "name": "chat",
        "description": (
            "Chat and conversation endpoints for AI agent interaction. "
            "Supports session management and conversation history "
            "for both frontend and agent consumers."
        ),
    },
    {
        "name": "memory",
        "description": (
            "Memory and context management endpoints. Provides persistent conversation "
            "memory, user preference learning, and contextual retrieval for AI agents."
        ),
    },
    {
        "name": "attachments",
        "description": (
            "File upload and processing endpoints. Supports travel document analysis, "
            "image processing, and document extraction with AI-powered insights."
        ),
    },
    {
        "name": "frontend",
        "description": (
            "Endpoints optimized for frontend consumers with UI-friendly responses, "
            "pagination, and user experience enhancements."
        ),
    },
    {
        "name": "agents",
        "description": (
            "Endpoints optimized for AI agent consumers with rich context data, "
            "tool integration metadata, and enhanced rate limits."
        ),
    },
]


# Example responses for different endpoints


class OpenAPIExample(TypedDict, total=False):
    """Typed mapping for OpenAPI example entries."""

    summary: str
    description: str
    value: dict[str, Any]


EXAMPLES: dict[str, OpenAPIExample] = {
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


def custom_openapi(app: FastAPI) -> dict[str, Any]:
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

    components = cast(dict[str, Any], openapi_schema["components"])
    examples = cast(dict[str, Any], components.setdefault("examples", {}))
    examples.update(EXAMPLES)

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
