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

### Import Paths

Follow the [Import Path Standards](import-paths.md) for all imports:

- Use `@schemas/*` for Zod schemas
- Use `@domain/*` for domain logic
- Use `@ai/*` for AI tooling
- Use `@/*` for generic src-root (lib, components, stores)
- Use relative imports (`./`, `../`) within the same feature directory

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

### Zod Schema Organization

**Co-locate schemas by default**: Keep Zod schemas in the same file where they're primarily used (tool files, route handlers) to maintain context and keep validation logic close to execution.

**Extract to shared schemas when**:

- The same schema is consumed by ≥2 distinct modules (e.g., tool + UI form + route handler)
- You need strong schema versioning and stable import paths across multiple layers
- The schema exceeds ~150 LOC or has multiple discriminated unions that benefit from dedicated file organization

**Type definitions**: Keep derived TypeScript types (`z.infer<typeof Schema>`) in `frontend/src/domain/types/index.ts` for ergonomic imports without pulling Zod at call sites.

**Import paths**: Use `@schemas/*` alias for all schema imports. See [Import Paths](import-paths.md) for details.

**Best practices**:

- Use `.strict()` where inputs are external (user-provided or API responses)
- Prefer `.transform()` for normalization over ad-hoc post-processing
- Use cross-field `.refine`/`.superRefine` for invariants (e.g., checkout after checkin, non-negative price ranges)

Example:

```typescript
// frontend/src/ai/tools/server/accommodations.ts - schema co-located with tool
import { ACCOMMODATION_SEARCH_INPUT_SCHEMA } from "@schemas/accommodations";

const searchSchema = ACCOMMODATION_SEARCH_INPUT_SCHEMA.refine(
  (data) => new Date(data.checkout) > new Date(data.checkin), 
  "checkout must be after checkin"
);

// frontend/src/domain/types/index.ts - types for ergonomic imports
export type AccommodationSearchParams = z.infer<typeof ACCOMMODATION_SEARCH_INPUT_SCHEMA>;
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
