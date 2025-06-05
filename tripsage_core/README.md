# TripSage Core

The foundational shared library for the TripSage AI travel planning platform. This package provides common components, services, models, and utilities used across the entire TripSage ecosystem.

## Overview

`tripsage_core` serves as the centralized foundation layer that provides:

- **Shared Configuration Management** - Centralized settings with environment-specific configurations
- **Exception System** - Comprehensive error handling with HTTP status integration
- **Data Models** - Base classes and shared schemas for database, domain, and API operations
- **Business Services** - Core business logic services with clean dependency injection
- **External API Integration** - Standardized patterns for third-party service integration
- **Infrastructure Services** - Database, caching, and communication management
- **Utilities** - Common functionality for caching, logging, error handling, and more

## Architecture

The core follows a clean architecture pattern with clear separation of concerns:

```
tripsage_core/
├── config/              # Configuration management
├── exceptions/          # Error handling system
├── models/              # Data models and schemas
├── services/            # Business logic and integrations
└── utils/               # Shared utilities
```

## Key Components

### Configuration System (`config/`)

Centralized configuration management with support for multiple environments:

```python
from tripsage_core.config import get_app_settings

settings = get_app_settings()
```

**Features:**
- Environment-specific configurations (dev, test, staging, prod)
- Validation for critical settings
- Integration with Supabase, DragonflyDB, Mem0, LangGraph
- Feature flags and performance settings
- OpenTelemetry configuration

### Exception System (`exceptions/`)

Comprehensive error handling with FastAPI integration:

```python
from tripsage_core.exceptions import (
    AuthenticationError,
    ValidationError,
    ExternalAPIError
)

# HTTP status codes automatically mapped
raise AuthenticationError("Invalid token")  # Returns 401
```

**Features:**
- Hierarchical exception structure
- HTTP status code integration
- Structured error details with Pydantic validation
- Consumer-aware error formatting (agents vs. frontend)

### Models (`models/`)

Three-tier model architecture:

#### Base Models (`base_core_model.py`)
```python
from tripsage_core.models.base_core_model import (
    TripSageModel,           # API/Schema models
    TripSageDomainModel,     # Business domain entities
    TripSageDBModel          # Database models
)
```

#### Database Models (`db/`)
SQLAlchemy-compatible models for:
- User management and authentication
- Trip planning and itineraries
- Flight and accommodation data
- Memory and chat sessions
- API key management
- Search parameters and history

#### Domain Models (`domain/`)
Business entities for:
- Accommodation booking and search
- Flight operations and pricing
- Memory and context management

#### Shared Schemas (`schemas_common/`)
Common validation and data structures:
- Base models and enums
- Geographic and temporal types
- Financial and travel-specific schemas
- Validation utilities

### Services (`services/`)

Three-tier service architecture providing clean separation:

#### Business Services (`business/`)

Core business logic services with dependency injection:

```python
from tripsage_core.services.business import (
    AuthService,
    MemoryService,
    ChatService,
    FlightService,
    AccommodationService
)
```

**Available Services:**
- **AuthService** - Authentication and authorization
- **MemoryService** - Context and conversation memory
- **ChatService** - Chat session management
- **FlightService** - Flight search and booking operations
- **AccommodationService** - Hotel and lodging operations
- **DestinationService** - Travel destination research
- **ItineraryService** - Trip planning and optimization
- **TripService** - Trip management and coordination
- **UserService** - User profile and preferences
- **KeyManagementService** - BYOK (Bring Your Own Key) operations
- **FileProcessingService** - Document analysis and processing

#### External API Services (`external_apis/`)

Standardized integrations with third-party services:

```python
from tripsage_core.services.external_apis import (
    GoogleMapsService,
    WeatherService,
    CalendarService,
    WebcrawlService
)
```

**Available Services:**
- **GoogleMapsService** - Location and mapping operations
- **WeatherService** - Weather data and forecasting
- **CalendarService** - Calendar integration and scheduling
- **DocumentAnalyzer** - Document processing and analysis
- **WebcrawlService** - Web scraping and content extraction
- **PlaywrightService** - Browser automation
- **TimeService** - Time zone and scheduling utilities

#### Infrastructure Services (`infrastructure/`)

Core infrastructure management:

```python
from tripsage_core.services.infrastructure import (
    DatabaseService,
    CacheService,
    WebSocketManager,
    KeyMonitoringService
)
```

**Available Services:**
- **DatabaseService** - Database operations and transactions
- **CacheService** - High-performance caching with DragonflyDB
- **WebSocketManager** - Real-time communication management
- **WebSocketBroadcaster** - Message broadcasting
- **KeyMonitoringService** - API key usage and security monitoring

### Utilities (`utils/`)

Common functionality used throughout the application:

```python
from tripsage_core.utils import (
    cache_utils,
    error_handling_utils,
    logging_utils,
    database_utils
)
```

**Available Utilities:**
- **cache_utils** - Caching patterns and TTL management
- **error_handling_utils** - Error recovery and retry logic
- **logging_utils** - Structured logging and observability
- **database_utils** - Database connection and transaction helpers
- **file_utils** - File processing and validation
- **session_utils** - Session management and security
- **decorator_utils** - Common decorators for cross-cutting concerns

## Performance Optimizations

### DragonflyDB Integration
- **25x performance improvement** over Redis
- Multi-tier TTL strategy for different data types
- Redis-compatible interface with enhanced features

### Memory System
- **Mem0 integration** with pgvector backend
- **91% faster performance** than traditional approaches
- Vector similarity search for contextual retrieval
- Automatic conversation context preservation

## Security Features

### Authentication & Authorization
- JWT token management with refresh capabilities
- API key authentication for service-to-service communication
- BYOK (Bring Your Own Key) with encryption for user-provided credentials
- Row Level Security (RLS) in database operations

### Data Protection
- Automatic encryption of sensitive data
- Secure key storage and rotation
- Rate limiting and abuse protection
- Input validation and sanitization

## Usage Examples

### Basic Service Usage
```python
from tripsage_core.services.business import FlightService
from tripsage_core.config import get_app_settings

settings = get_app_settings()
flight_service = FlightService(settings)

# Search for flights
results = await flight_service.search_flights(
    origin="LAX",
    destination="JFK",
    departure_date="2024-06-15"
)
```

### Database Operations
```python
from tripsage_core.services.infrastructure import DatabaseService
from tripsage_core.models.db import Trip

async with DatabaseService() as db:
    trip = await db.create(Trip(
        user_id=user_id,
        title="Summer Vacation",
        destination="Paris"
    ))
```

### Caching
```python
from tripsage_core.services.infrastructure import CacheService
from tripsage_core.utils.cache_utils import cache_key

cache = CacheService()
key = cache_key("flights", origin="LAX", destination="JFK")

# Cache with TTL
await cache.set(key, flight_data, ttl=3600)
cached_data = await cache.get(key)
```

### Error Handling
```python
from tripsage_core.exceptions import ExternalAPIError
from tripsage_core.utils.error_handling_utils import with_retry

@with_retry(max_attempts=3, backoff_factor=2)
async def external_api_call():
    try:
        return await some_external_service()
    except Exception as e:
        raise ExternalAPIError(f"API call failed: {e}")
```

## Testing

The core is designed with testability in mind:

- **Dependency injection** for easy mocking
- **Isolated database operations** with test fixtures
- **Comprehensive test coverage** (>90% target)
- **Mock external service integrations**

```bash
# Run tests
uv run pytest tests/unit/tripsage_core/ --cov=tripsage_core

# Run with coverage report
uv run pytest tests/unit/tripsage_core/ --cov=tripsage_core --cov-report=html
```

## Dependencies

Key dependencies include:

- **FastAPI** - Web framework and validation
- **Pydantic v2** - Data validation and serialization
- **SQLAlchemy** - Database ORM
- **Supabase** - Primary database and authentication
- **DragonflyDB** - High-performance caching
- **Mem0** - AI memory and context management
- **pgvector** - Vector similarity search
- **HTTPX** - Async HTTP client
- **Polars** - High-performance data manipulation

## Integration with TripSage Application

`tripsage_core` is used by:

- **`tripsage/api/`** - FastAPI application serving both frontend and agents
- **`tripsage/agents/`** - LangGraph-based AI agents for travel planning
- **`frontend/`** - Next.js application for user interface
- **Tests** - Comprehensive test suites for all components

## Contributing

When extending `tripsage_core`:

1. **Follow clean architecture principles** - Keep concerns separated
2. **Use dependency injection** - Make components testable
3. **Add comprehensive tests** - Maintain high coverage
4. **Document new features** - Update this README and add docstrings
5. **Validate configurations** - Ensure proper settings validation
6. **Handle errors properly** - Use the exception system consistently

## Performance Considerations

- **Async/await patterns** - Use throughout for scalability
- **Connection pooling** - Database and external API connections
- **Caching strategies** - Implement appropriate TTL for different data types
- **Memory management** - Avoid memory leaks in long-running services
- **Monitoring integration** - Use OpenTelemetry for observability