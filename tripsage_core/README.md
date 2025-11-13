# TripSage Core

Shared library providing common components, services, and utilities for the TripSage travel planning platform.

## Overview

`tripsage_core` provides:

- **Configuration Management** - Centralized settings for Supabase, Upstash Redis, and external APIs
- **Exception System** - HTTP status-integrated error handling
- **Data Models** - Supabase-compatible models for users, trips, flights, and chat
- **Business Services** - Core logic for authentication, flights, accommodations, and memory
- **External API Integration** - Direct SDK integrations (Duffel, Google Maps, Weather, etc.)
- **Infrastructure Services** - Database, caching, and Realtime (Supabase) management
- **Utilities** - Common functionality for caching, logging, and error handling

## Architecture

```text
tripsage_core/
├── config.py            # Configuration management
├── exceptions/          # Error handling system
├── models/              # Supabase data models and schemas
├── services/            # Business logic and external integrations
├── infrastructure/      # Database and communication services
├── observability/       # Monitoring and logging
└── utils/               # Shared utilities
```

## Key Components

### Configuration (`config.py`)

Centralized settings for Supabase, Upstash Redis, and external APIs:

```python
from tripsage_core.config import get_app_settings

settings = get_app_settings()
# Access: settings.database_url, settings.upstash_redis_rest_url, etc.
```

### Exception System (`exceptions/`)

HTTP status-integrated error handling for APIs:

```python
from tripsage_core.exceptions import AuthenticationError, ExternalAPIError

raise AuthenticationError("Invalid token")  # Returns 401
raise ExternalAPIError("Flight API unavailable")  # Returns 502
```

### Data Models (`models/`)

Supabase-compatible models and schemas:

```python
from tripsage_core.models.db import User, Trip, Flight
from tripsage_core.models.api import TripCreateRequest
```

**Database Models:**

- `User` - Authentication and profiles
- `Trip` - Travel planning and itineraries
- `Flight` - Flight search and bookings
- `Accommodation` - Hotel and lodging data
- `Chat` - AI conversations and memory
- `APIKey` - BYOK (Bring Your Own Key) management

### Business Services (`services/business/`)

Core business logic with dependency injection:

```python
from tripsage_core.services.business import (
    AuthService,
    FlightService,
    AccommodationService,
    MemoryService
)
```

**Available Services:**

- `AuthService` - JWT and API key authentication
- `FlightService` - Duffel API integration for flights
- `AccommodationService` - Hotel search and booking
- `MemoryService` - Conversation memory and user preferences (Mem0)
- `TripService` - Trip planning and coordination
- `UserService` - User profiles and preferences
- `DestinationService` - Location research and insights
- `ItineraryService` - Trip optimization and scheduling
- `APIKeyService` - BYOK encryption and validation
- `FileProcessingService` - Document analysis
- `UnifiedSearchService` - Multi-provider search orchestration

### External API Services (`services/external_apis/`)

Direct SDK integrations with third-party services:

```python
from tripsage_core.services.external_apis import (
    DuffelProvider,
    PlaywrightService
)
```

**Available Services:**

> [!NOTE]
> Location/POI tooling migrated to Next.js; no Python Google Maps service remains.
> Time-related utilities are no longer exported from Core external_apis; use frontend or direct libs as appropriate.
> Calendar integration handled by frontend AI SDK tools; no Python CalendarService remains.

- `DuffelProvider` - Flight search and booking (direct SDK)
- `WebcrawlService` - Content extraction
- `PlaywrightService` - Browser automation
- `DocumentAnalyzer` - File processing

### Infrastructure Services (`services/infrastructure/`)

Database, caching, and monitoring:

```python
from tripsage_core.services.infrastructure import (
    DatabaseService,
    CacheService,
    KeyMonitoringService,
)
```

**Available Services:**

- `DatabaseService` - Supabase operations and transactions
- `CacheService` - Upstash Redis caching
- `KeyMonitoringService` - API key usage monitoring

Realtime is handled client-side via Supabase Realtime (private channels + RLS).

### Utilities (`utils/`)

Common functionality and helpers:

```python
from tripsage_core.utils.cache_utils import cached
from tripsage_core.utils.logging_utils import get_logger
```

**Available Utilities:**

- `cache_utils` - Caching patterns and TTL management
- `logging_utils` - Structured logging helpers
- `decorator_utils` - Common decorators (retries, validation)
- `file_utils` - File validation and processing
- `connection_utils` - Database URL parsing

## Usage Examples

### Service Usage

```python
from tripsage_core.services.business import FlightService, AuthService
from tripsage_core.config import get_app_settings

settings = get_app_settings()

# Flight search
flight_service = FlightService(settings)
results = await flight_service.search_flights(
    origin="LAX", destination="JFK", departure_date="2024-06-15"
)

# Authentication
auth_service = AuthService(settings)
user = await auth_service.authenticate_user(email="user@example.com")
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

### Caching with Upstash Redis

```python
from tripsage_core.services.infrastructure import CacheService

cache = CacheService()
await cache.set("flight_search:LAX-JFK", flight_data, ttl=3600)
cached_data = await cache.get("flight_search:LAX-JFK")
```

## Security

- **JWT authentication** with refresh tokens
- **API key management** with encryption (BYOK)
- **Supabase RLS** (Row Level Security)
- **Input validation** and sanitization
- **Rate limiting** and abuse protection

## Testing

```bash
# Run core tests
uv run pytest tests/unit/tripsage_core/ --cov=tripsage_core

# Run with coverage
uv run pytest tests/unit/tripsage_core/ --cov=tripsage_core --cov-report=html
```

## Dependencies

- **Supabase** - Database and authentication
- **Upstash Redis** - Serverless caching
- **Mem0** - AI memory and context
- **pgvector** - Vector embeddings
- **Pydantic** - Data validation
- **HTTPX** - Async HTTP client

## Integration

Used by `tripsage/api/`, `tripsage/agents/`, and `frontend/` applications.
