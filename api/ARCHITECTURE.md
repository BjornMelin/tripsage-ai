# TripSage API Architecture

This document provides a comprehensive overview of the TripSage API architecture, explaining the rationale behind the design choices and how the various components work together.

## Design Principles

The TripSage API is built on the following principles:

1. **KISS (Keep It Simple, Stupid)** - Straightforward solutions over complex abstractions
2. **YAGNI (You Aren't Gonna Need It)** - Only implementing what's explicitly needed
3. **DRY (Don't Repeat Yourself)** - No duplicated logic; factoring into clear helpers
4. **Maintainability** - Code that's clear, well-organized, and easy to understand

## Architecture Overview

The API follows a layered architecture with clear separation of concerns:

1. **Routers** - Handle HTTP requests and responses
2. **Models** - Define request/response data structures using Pydantic
3. **Services** - Implement business logic
4. **Repositories** - Handle data access (implemented via storage services)
5. **Middlewares** - Process requests/responses globally
6. **Dependencies** - Provide reusable components via dependency injection

## Component Breakdown

### 1. Application Entry Point (`main.py`)

The main entry point configures the FastAPI application, including:

- Setting up middleware
- Registering routes
- Configuring error handlers
- Defining startup/shutdown events

The application is created using a factory pattern, allowing for flexibility in configuration.

### 2. Dependency Injection (`deps.py`)

Centralized dependency injection provides:

- Singleton services
- Request-scoped resources
- Authentication dependencies
- Direct SDK client access

This approach ensures:

- Clean separation of concerns
- Testability through mocked dependencies
- Consistent resource management

### 3. Middleware Stack

Middlewares process requests in the following order:

1. **Metrics** - Collects performance metrics
2. **Logging** - Logs request details
3. **Error Handling** - Catches and processes exceptions
4. **Authentication** - Validates JWT tokens and API keys
5. **CORS** - Handles cross-origin requests

Each middleware focuses on a single responsibility, making the code more maintainable.

### 4. Router Organization

Routers are organized by domain:

- **Auth** - User authentication and registration
- **Trips** - Trip creation and management
- **Flights** - Flight search and booking
- **Accommodations** - Accommodation search and booking
- **Destinations** - Destination research
- **Itineraries** - Itinerary management
- **Keys** - API key management (BYOK functionality)

Each router defines endpoints using FastAPI decorators, specifying:

- HTTP method
- Path
- Request/response models
- Dependencies
- Status codes

### 5. Model Organization

Models are divided into:

- **Request Models** - Validate incoming data
- **Response Models** - Structure outgoing data

Each model uses Pydantic's validation features:

- Type checking
- Field constraints
- Custom validators
- Documentation via Field descriptions

### 6. Service Layer

Services implement business logic and are organized by domain:

- **AuthService** - Authentication and user management
- **TripService** - Trip planning and management
- **FlightService** - Flight search and booking
- **AccommodationService** - Accommodation search
- **DestinationService** - Destination research
- **KeyService** - API key management (BYOK)
- **MemoryService** - Session memory management

Services interact with:

- Storage services for data persistence
- Direct SDK clients for external integrations (Duffel, Google Maps, etc.)
- Airbnb MCP client (the only remaining MCP integration)
- Other services for cross-domain functionality

### 7. Authentication System

The authentication system supports:

- **JWT-based authentication** - Using access and refresh tokens
- **API key authentication** - For programmatic access
- **BYOK (Bring Your Own Key)** - For user-provided external API keys

Security features include:

- HTTP-only cookies for refresh tokens
- Password hashing with bcrypt
- Token expiration and refresh
- Role-based access control

### 8. Error Handling

The error handling strategy includes:

- **Custom exceptions** - For domain-specific errors
- **Global exception handlers** - For standardized error responses
- **Middleware-based error catching** - For unexpected exceptions

All errors follow a consistent structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "additional": "error details"
  }
}
```

### 9. Logging and Monitoring

The application includes:

- **Request logging** - For debugging and audit trails
- **Error logging** - For monitoring and alerting
- **Performance metrics** - For monitoring response times
- **OpenTelemetry integration** - For distributed tracing

## Data Flow

1. **Request** - Client sends HTTP request to API
2. **Middleware** - Request passes through middleware stack
3. **Router** - Endpoint handler is called with dependencies
4. **Service** - Business logic is executed
5. **Storage** - Data is retrieved or updated
6. **Response** - Result is returned to client

## External Integrations

The API integrates with:

- **Direct SDK Clients** - For most external services (Duffel Flights, Google Maps, Google Calendar, OpenWeatherMap, Crawl4AI)
- **Airbnb MCP Client** - The only remaining MCP integration (no official Airbnb SDK available)
- **DualStorageService** - For data persistence (SQL + Neo4j)
- **SessionMemory** - For maintaining context across requests

## Security Considerations

Security features include:

- **Authentication** - JWT tokens and API keys
- **Authorization** - Role-based access control
- **Input validation** - Pydantic models
- **Error handling** - Standardized error responses
- **CORS** - Restricted cross-origin access
- **Rate limiting** - Protection against abuse
- **Secure cookies** - HTTP-only, secure, SameSite

## Performance Optimizations

Performance considerations include:

- **Async/await** - Non-blocking I/O
- **Connection pooling** - For database connections
- **Caching** - For expensive operations
- **Pagination** - For large result sets
- **Dependency optimization** - Reusing dependencies
- **Middleware efficiency** - Minimal overhead

## Deployment Considerations

The application is designed for:

- **Containerization** - Using Docker
- **Horizontal scaling** - Stateless design
- **Environment-specific configuration** - Using environment variables
- **Health checks** - For monitoring and auto-healing

## Configuration Management

Configuration is handled through:

- **Environment variables** - For production settings
- **.env files** - For development settings
- **Pydantic settings** - For validation and defaults
- **Environment-specific logic** - For different deployment environments

## Conclusion

The TripSage API architecture follows best practices for FastAPI applications while adhering to the project's KISS principles. The design emphasizes maintainability, security, and performance, providing a solid foundation for the travel planning platform.