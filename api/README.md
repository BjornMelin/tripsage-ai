# TripSage API

This directory contains the FastAPI application for the TripSage platform, providing a clean, maintainable API structure that follows KISS principles.

## Directory Structure

```
/api
├── main.py                    # FastAPI application entry point
├── deps.py                    # Centralized dependency injection
├── README.md                  # This file
├── middlewares/               # Middleware definitions
│   ├── __init__.py
│   ├── authentication.py      # Authentication middleware
│   ├── cors.py                # CORS middleware configuration
│   ├── error_handling.py      # Error handling middleware
│   ├── logging.py             # Request logging middleware
│   └── metrics.py             # Metrics collection middleware
├── core/                      # Core application components
│   ├── __init__.py
│   ├── config.py              # App configuration
│   ├── security.py            # Security utilities
│   ├── logging.py             # Logging configuration
│   └── exceptions.py          # Custom exception definitions
├── models/                    # Pydantic models for API
│   ├── __init__.py
│   ├── requests/              # Request models
│   └── responses/             # Response models
├── routers/                   # API route definitions
│   ├── __init__.py
│   ├── auth.py                # Authentication routes
│   ├── trips.py               # Trip management routes
│   ├── flights.py             # Flight search/booking routes
│   ├── accommodations.py      # Accommodation search/booking routes
│   ├── destinations.py        # Destination research routes
│   ├── itineraries.py         # Itinerary management routes
│   └── keys.py                # API key management (BYOK) routes
└── services/                  # API service implementations
    ├── __init__.py
    ├── auth_service.py        # Authentication service
    ├── trip_service.py        # Trip planning service
    ├── flight_service.py      # Flight service
    ├── accommodation_service.py # Accommodation service
    ├── destination_service.py   # Destination research service
    ├── key_service.py         # API key management service
    └── memory_service.py      # Session memory service
```

## Key Components

### Application Entry Point (main.py)

The application entry point configures the FastAPI application with middleware, routes, and event handlers. It also includes error handling setup and creates the application instance.

### Dependency Injection (deps.py)

Centralizes all FastAPI dependencies, including:
- MCP clients (weather, flights, accommodations, etc.)
- Authentication dependencies
- Storage service
- Session memory

### Middleware

- **Authentication**: Validates JWT tokens and API keys
- **Error Handling**: Catches and processes exceptions
- **Logging**: Logs requests and responses
- **Metrics**: Collects performance metrics
- **CORS**: Configures Cross-Origin Resource Sharing

### Core Components

- **Config**: Extends the application settings for API-specific configuration
- **Exceptions**: Defines custom exceptions with standardized error responses
- **Security**: Provides security utilities (password hashing, token generation)
- **Logging**: Configures logging for the API

### Models

- **Request Models**: Pydantic models for validating incoming requests
- **Response Models**: Pydantic models for structuring API responses

### Routers

Organized by domain:
- **Auth**: User authentication and registration
- **Trips**: Trip creation and management
- **Flights**: Flight search and booking
- **Accommodations**: Accommodation search and booking
- **Destinations**: Destination research
- **Itineraries**: Itinerary management
- **Keys**: API key management (BYOK functionality)

### Services

Implement business logic:
- **Auth Service**: User authentication and registration
- **Trip Service**: Trip planning and management
- **Flight Service**: Flight search and booking
- **Accommodation Service**: Accommodation search
- **Destination Service**: Destination research
- **Key Service**: API key management (BYOK)
- **Memory Service**: Session memory management

## Features

- **JWT Authentication**: Secure authentication using JWT tokens
- **API Key Authentication**: Alternative authentication using API keys
- **BYOK (Bring Your Own Key)**: Allow users to use their own API keys for external services
- **Error Handling**: Standardized error responses
- **Dependency Injection**: Clean separation of concerns
- **Request Validation**: Automatic request validation using Pydantic models
- **Middleware Pipeline**: Configurable middleware pipeline
- **MCP Integration**: Seamless integration with Model Context Protocol (MCP) services

## Usage

To run the API locally:

```bash
# From the project root
python -m api.main
```

Or with uvicorn directly:

```bash
uvicorn api.main:app --reload
```

## Development

When developing:

1. Create new routes in the appropriate router file
2. Define request/response models in the models directory
3. Implement business logic in service classes
4. Use dependency injection for clean separation of concerns
5. Follow KISS principles - prefer simple, straightforward solutions