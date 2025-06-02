# TripSage Core Architecture

This document provides a comprehensive architectural overview of the `tripsage_core` package, the foundational library providing core business logic, domain models, and infrastructure services for travel planning operations.

## Core Principles

`tripsage_core` is designed as a **self-contained library** that:
- Has **NO dependencies** on the `tripsage` package
- Provides pure business logic and domain models
- Is framework-agnostic (can be used with any Python web framework)
- Maintains clear separation between business, infrastructure, and external concerns

## Package Structure

```
tripsage_core/
├── config/                    # Configuration management
│   └── base_app_settings.py  # Environment-based settings
│
├── exceptions/               # Centralized exception hierarchy
│   └── exceptions.py         # All core exceptions
│
├── models/                   # Data models and schemas
│   ├── base_core_model.py   # Base model classes
│   ├── db/                  # Database/persistence models
│   ├── domain/              # Business domain entities
│   └── schemas_common/      # Shared schemas and enums
│
├── services/                 # Service layer
│   ├── business/            # Core business logic services
│   ├── external_apis/       # Third-party API clients
│   └── infrastructure/      # Infrastructure services
│
└── utils/                    # Cross-cutting utilities
    ├── cache_utils.py       # Caching helpers
    ├── database_utils.py    # DB helpers
    ├── decorator_utils.py   # Common decorators
    ├── error_handling_utils.py  # Error handling
    ├── file_utils.py        # File operations
    ├── logging_utils.py     # Structured logging
    └── session_utils.py     # Session management
```

## Layer Architecture

### 1. Foundation Layer

#### Configuration (`config/`)
- **Purpose**: Centralized configuration management
- **Key Components**:
  - `BaseAppSettings`: Pydantic settings with environment validation
  - Environment-specific overrides
  - Feature flags and service credentials

#### Exceptions (`exceptions/`)
- **Purpose**: Hierarchical exception system with HTTP status mapping
- **Hierarchy**:
  ```
  CoreTripSageError (500)
  ├── CoreAuthenticationError (401)
  ├── CoreAuthorizationError (403)
  ├── CoreValidationError (422)
  ├── CoreResourceNotFoundError (404)
  ├── CoreServiceError (500)
  ├── CoreDatabaseError (500)
  ├── CoreExternalAPIError (502)
  └── CoreRateLimitError (429)
  ```

#### Utilities (`utils/`)
- **Purpose**: Reusable cross-cutting concerns
- **Key Utilities**:
  - **cache_utils**: TTL management, key generation
  - **database_utils**: Connection management, transactions
  - **decorator_utils**: `@with_error_handling`, `@with_retry`
  - **error_handling_utils**: Retry logic, error recovery
  - **logging_utils**: Structured logging with context
  - **session_utils**: Session generation and validation

### 2. Model Layer

#### Base Models (`models/base_core_model.py`)
```python
TripSageModel         # Base for all models
├── TripSageDomainModel   # Business entities
├── TripSageDBModel       # Database models
└── TripSageSchemaModel   # API schemas
```

#### Model Categories

**Database Models (`models/db/`)**
- SQLAlchemy-compatible models for persistence
- Examples: `User`, `Trip`, `Flight`, `Accommodation`, `ApiKeyDB`
- Include relationships and database-specific validations

**Domain Models (`models/domain/`)**
- Pure business entities with rich behavior
- Examples: `FlightOffer`, `AccommodationListing`, `Entity`, `Relation`
- Contain business logic and invariants

**Common Schemas (`models/schemas_common/`)**
- Shared enums and value objects
- Examples: `CabinClass`, `BookingStatus`, `CurrencyCode`
- Validation patterns and common types

### 3. Service Layer

#### Business Services (`services/business/`)
**Purpose**: Core business logic implementation

**Key Services**:
- **AuthService**: Authentication, authorization, token management
- **MemoryService**: Context management, conversation memory
- **FlightService**: Flight search, booking, price tracking
- **AccommodationService**: Hotel/lodging search and booking
- **TripService**: Trip planning and management
- **ChatService**: Conversation management
- **DestinationService**: Destination research and insights
- **KeyManagementService**: API key management for BYOK
- **ChatOrchestrationService**: Chat flow orchestration
- **ToolCallingService**: Tool/function calling patterns
- **ErrorHandlingService**: Error recovery strategies
- **LocationService**: Geographic operations

**Service Pattern**:
```python
class BaseBusinessService:
    def __init__(self, settings: BaseAppSettings):
        self.settings = settings
        self.db = self._get_db_service()
        self.cache = self._get_cache_service()
```

#### External API Services (`services/external_apis/`)
**Purpose**: Third-party API integrations

**Key Services**:
- **GoogleMapsService**: Location, geocoding, directions
- **WeatherService**: Weather data and forecasts
- **CalendarService**: Calendar integration
- **DuffelHttpClient**: Flight booking API
- **DocumentAnalyzer**: Document processing
- **TimeService**: Timezone operations
- **WebcrawlService**: Web scraping
- **PlaywrightService**: Browser automation

**Integration Pattern**:
```python
class ExternalAPIService:
    async def _make_request(self, endpoint: str, **kwargs):
        # Standardized request handling
        # Retry logic
        # Error mapping
        # Response validation
```

#### Infrastructure Services (`services/infrastructure/`)
**Purpose**: Low-level infrastructure management

**Key Services**:
- **DatabaseService**: Connection pooling, transactions
- **CacheService**: Redis/DragonflyDB caching
- **WebSocketManager**: Real-time connection management
- **WebSocketBroadcaster**: Event broadcasting
- **KeyMonitoringService**: API key usage tracking

## Key Design Patterns

### 1. Dependency Injection
```python
# Services receive dependencies, don't create them
class FlightService:
    def __init__(self, db_service: DatabaseService, cache_service: CacheService):
        self.db = db_service
        self.cache = cache_service
```

### 2. Repository Pattern
```python
# Data access abstraction
class TripRepository:
    async def get_user_trips(self, user_id: str) -> List[Trip]:
        async with self.db as conn:
            return await conn.query(Trip).filter_by(user_id=user_id).all()
```

### 3. Service Registry Pattern
```python
# Centralized service management
class ServiceRegistry:
    def get_service(self, service_type: Type[T]) -> T:
        if service_type not in self._services:
            self._services[service_type] = service_type(self.settings)
        return self._services[service_type]
```

### 4. Error Handling Pattern
```python
# Consistent error handling with context
@with_error_handling
async def search_flights(self, criteria: FlightSearchCriteria):
    try:
        return await self._search_impl(criteria)
    except ExternalAPIError as e:
        # Map to domain error
        raise FlightSearchError(f"Flight search failed: {e}")
```

## Data Flow

### Typical Request Flow
1. **Input Validation** (Pydantic models)
2. **Business Logic** (Business services)
3. **External Calls** (If needed, via external API services)
4. **Data Persistence** (Via infrastructure services)
5. **Caching** (For performance)
6. **Response Formatting** (Domain models)

### Caching Strategy
```python
TTL_REAL_TIME = 300      # 5 min - prices, availability
TTL_MODERATE = 3600      # 1 hour - search results
TTL_STABLE = 86400       # 24 hours - destination info
TTL_PERSISTENT = 604800  # 7 days - user preferences
```

## Usage Example

```python
from tripsage_core.config import BaseAppSettings
from tripsage_core.services.business import FlightService, ServiceRegistry

# Initialize settings
settings = BaseAppSettings()

# Option 1: Direct service instantiation
flight_service = FlightService(settings)

# Option 2: Using service registry
registry = ServiceRegistry(settings)
flight_service = registry.get_service(FlightService)

# Use the service
results = await flight_service.search_flights(search_criteria)
```

## Key Boundaries

### What tripsage_core DOES:
- ✅ Provides business logic and domain models
- ✅ Manages data persistence and caching
- ✅ Integrates with external APIs
- ✅ Handles authentication and authorization logic
- ✅ Manages business rules and validations

### What tripsage_core DOES NOT:
- ❌ Handle HTTP requests/responses
- ❌ Implement web framework specifics
- ❌ Contain API routing or middleware
- ❌ Include agent or orchestration logic
- ❌ Depend on the `tripsage` package

## Extension Points

### Adding New Services
1. Create service in appropriate directory:
   - `services/business/` for business logic
   - `services/external_apis/` for integrations
   - `services/infrastructure/` for infrastructure

2. Follow the established patterns:
   - Inherit from base service class
   - Use dependency injection
   - Implement error handling
   - Add appropriate logging

### Adding New Models
1. Create models in appropriate directory:
   - `models/domain/` for business entities
   - `models/db/` for persistence models
   - `models/schemas_common/` for shared types

2. Inherit from appropriate base class:
   - `TripSageDomainModel` for domain entities
   - `TripSageDBModel` for database models

## Testing Guidelines

### Unit Testing
- Test business logic in isolation
- Mock external dependencies
- Use fixtures for common test data
- Achieve 80-90% coverage

### Integration Testing
- Test service interactions
- Use test database
- Mock external APIs
- Test error scenarios

## Performance Considerations

### Database Performance
- Connection pooling (20 connections default)
- Query optimization with indexes
- Prepared statements for common queries
- Batch operations where possible

### Caching Performance
- Multi-tier caching strategy
- Appropriate TTLs per data type
- Cache warming for common queries
- Cache invalidation patterns

### Memory Management
- Efficient data structures
- Streaming for large datasets
- Connection cleanup
- Resource pooling

## Security Considerations

### Data Protection
- Encryption for sensitive data
- API key encryption with user salts
- PII field identification
- Audit logging for compliance

### Input Validation
- Pydantic models for all inputs
- SQL injection prevention
- XSS protection in data
- Rate limiting support

### Authentication & Authorization
- JWT token validation
- API key management
- Role-based access control
- Service-to-service auth