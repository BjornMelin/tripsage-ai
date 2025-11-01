# Code Standards

Coding guidelines and conventions for TripSage development.

## Python Standards

### Type Hints

Use complete type hints for all function parameters and return values:

```python
from typing import List, Optional, Dict

def create_trip(name: str, destinations: List[str], budget: Optional[float] = None) -> Dict[str, str]:
    # Implementation
    pass
```

### Error Handling

Use custom exception classes derived from `CoreTripSageError`:

```python
from tripsage_core.exceptions import CoreTripSageError

class TripNotFoundError(CoreTripSageError):
    pass

# Usage
raise TripNotFoundError("Trip not found", status_code=404)
```

### Async Operations

Use async/await for all I/O operations:

```python
async def get_trip(trip_id: str) -> Trip:
    async with db_session() as session:
        result = await session.execute(select(Trip).where(Trip.id == trip_id))
        return result.scalar_one()
```

### Docstrings

Use Google-style docstrings:

```python
def create_trip(name: str, destinations: List[str]) -> Trip:
    """Create a new trip with destinations.

    Args:
        name: Trip name
        destinations: List of destination names

    Returns:
        Created trip instance

    Raises:
        ValidationError: If trip data is invalid
    """
    pass
```

## TypeScript Standards

### Type Definitions

Use explicit types for all variables and function parameters:

```typescript
interface Trip {
  id: string;
  name: string;
  destinations: string[];
  status: 'planning' | 'booked' | 'completed';
}

function createTrip(tripData: Omit<Trip, 'id'>): Promise<Trip> {
  // Implementation
}
```

### React Components

Use functional components with proper typing:

```typescript
interface TripCardProps {
  trip: Trip;
  onEdit: (tripId: string) => void;
}

export function TripCard({ trip, onEdit }: TripCardProps) {
  return (
    <div>
      <h3>{trip.name}</h3>
      <button onClick={() => onEdit(trip.id)}>Edit</button>
    </div>
  );
}
```

### Custom Hooks

Follow the `use*` naming convention:

```typescript
function useTrips() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTrips = async () => {
    setLoading(true);
    try {
      const response = await api.getTrips();
      setTrips(response.data);
    } finally {
      setLoading(false);
    }
  };

  return { trips, loading, fetchTrips };
}
```

## Code Formatting

### Python (Ruff)

```bash
# Lint and fix issues
ruff check . --fix

# Format code
ruff format .
```

### TypeScript (Biome)

```bash
# Lint and fix issues
npx biome lint --apply .

# Format code
npx biome format . --write
```

## Architecture Patterns

### Service Layer

Keep business logic in dedicated service classes:

```python
class TripService:
    def __init__(self, db, cache, external_api):
        self.db = db
        self.cache = cache
        self.external_api = external_api

    async def create_trip(self, trip_data, user_id):
        # Business logic here
        pass
```

### Repository Pattern

Abstract data access behind repository interfaces:

```python
class TripRepository:
    async def get_by_id(self, trip_id: str) -> Trip:
        # Database query
        pass

    async def create(self, trip: Trip) -> Trip:
        # Insert operation
        pass
```

## Security Guidelines

### Input Validation

Validate all inputs using Pydantic models:

```python
from pydantic import BaseModel, Field

class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    destinations: List[str] = Field(min_items=1)
```

### Authentication

Use JWT tokens for API authentication:

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validate token
    pass
```

## Performance Guidelines

### Database Optimization

- Use indexes on frequently queried columns
- Avoid N+1 queries with eager loading
- Use connection pooling

### Caching Strategy

- Cache expensive operations
- Use appropriate TTL values
- Invalidate cache on data changes

### Async Best Practices

- Use async/await for all I/O operations
- Avoid blocking calls in async functions
- Use async context managers for resource management

## Code Review Checklist

### Before Submitting

- [ ] Tests pass with >90% coverage
- [ ] Code is properly typed
- [ ] Linting passes without errors
- [ ] Documentation updated
- [ ] Security review completed

### During Review

- [ ] Code follows established patterns
- [ ] Error handling is appropriate
- [ ] Performance considerations addressed
- [ ] Security vulnerabilities checked
- [ ] Tests are comprehensive and meaningful
