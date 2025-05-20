# TripSage API

This directory contains the FastAPI implementation for the TripSage API.

## Overview

The TripSage API provides endpoints for travel planning, including:

* User authentication and management
* API key management (BYOK - Bring Your Own Key)
* Trip planning and management
* Flight search and booking
* Accommodation search and booking
* Destination research
* Weather information
* Maps and directions

## Architecture

The API follows a clean, modular architecture with:

- **Routers**: Organized by domain (auth, users, trips, flights, etc.)
- **Models**: Pydantic V2 models for request/response validation
- **Services**: Business logic and database operations
- **Middleware**: Cross-cutting concerns (auth, logging, rate limiting)
- **Exceptions**: Custom exceptions and error handling
- **Config**: Application configuration and settings

## Directory Structure

```
tripsage/api/
├── core/            # Core configuration and utilities
│   ├── config.py    # Application settings
│   ├── exceptions.py # Custom exceptions
│   ├── openapi.py   # OpenAPI documentation
│   └── dependencies.py # Dependency injection
├── middlewares/     # Middleware components
│   ├── auth.py      # Authentication middleware
│   ├── logging.py   # Logging middleware
│   └── rate_limit.py # Rate limiting middleware
├── models/          # Pydantic V2 models
│   ├── auth.py      # Authentication models
│   └── api_key.py   # API key models
├── routers/         # API endpoints
│   ├── auth.py      # Authentication endpoints
│   ├── health.py    # Health check endpoints
│   └── keys.py      # API key management endpoints
├── services/        # Business logic
│   ├── auth.py      # Authentication service
│   ├── key.py       # API key service
│   └── user.py      # User service
├── tests/           # API tests
│   ├── conftest.py  # Test fixtures
│   ├── test_auth.py # Authentication tests
│   ├── test_health.py # Health check tests
│   └── test_keys.py # API key tests
├── utils/           # Utility functions
├── main.py          # FastAPI application
└── README.md        # This file
```

## Authentication

The API supports two authentication methods:

1. **JWT Authentication**: For user authentication using OAuth2 with JWT tokens
2. **API Key Authentication**: For service-to-service communication

### JWT Authentication Flow

1. Register a user via `POST /api/auth/register`
2. Login to get an access token via `POST /api/auth/token`
3. Use the access token in the `Authorization` header: `Bearer <token>`
4. Refresh the token when it expires via `POST /api/auth/refresh`

### API Key Authentication Flow

1. Create an API key via `POST /api/user/keys`
2. Use the API key in the `X-API-Key` header

## BYOK (Bring Your Own Key)

The API supports BYOK functionality for user-provided API keys:

1. User submits their API key via `POST /api/user/keys`
2. The API validates the key with the service
3. If valid, the key is stored encrypted in the database
4. When the user accesses a service, their API key is used instead of the default

## Running Tests

To run the API tests:

```bash
pytest tripsage/api/tests
```

## Development

To run the API locally:

```bash
python -m tripsage.api.main
```

The API will be available at http://localhost:8000 with documentation at http://localhost:8000/api/docs or http://localhost:8000/api/redoc.