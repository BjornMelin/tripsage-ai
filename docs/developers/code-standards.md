# 📝 Coding Standards

> **Code Quality Guidelines for TripSage AI**  
> Consistent coding standards for Python, TypeScript, and documentation

## Table of Contents

- [Python Standards](#python-standards)
- [TypeScript Standards](#typescript-standards)
- [Documentation Standards](#documentation-standards)
- [Code Formatting](#code-formatting)
- [Architecture Patterns](#architecture-patterns)
- [Security Guidelines](#security-guidelines)
- [Performance Guidelines](#performance-guidelines)
- [Code Review Checklist](#code-review-checklist)

---

## Python Standards

### **Type Hints**

All functions must include complete type hints:

```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class TripRequest(BaseModel):
    name: str
    destinations: List[str]
    budget: Optional[float] = None
    
async def create_trip(
    request: TripRequest,
    user_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """Create a new trip with validation."""
    ...
```

### **Error Handling**

Use custom exception classes:

```python
from tripsage_core.exceptions import CoreTripSageError

class TripNotFoundError(CoreTripSageError):
    """Raised when trip is not found."""
    def __init__(self, trip_id: str):
        super().__init__(
            message=f"Trip {trip_id} not found",
            code="TRIP_NOT_FOUND",
            status_code=404
        )
```

### **Async/Await Pattern**

Use async/await throughout:

```python
async def get_flight_options(
    search_params: FlightSearchParams
) -> List[FlightOption]:
    """Get flight options from Duffel API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.duffel.com/air/offer_requests",
            json=search_params.model_dump(),
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return [FlightOption.model_validate(item) for item in response.json()]
```

### **Docstrings**

Use Google-style docstrings:

```python
async def search_accommodations(
    location: str,
    check_in: date,
    check_out: date,
    guests: int = 1
) -> List[AccommodationOption]:
    """Search for accommodation options.
    
    Args:
        location: Destination city or address
        check_in: Check-in date
        check_out: Check-out date
        guests: Number of guests
        
    Returns:
        List of accommodation options with pricing and availability
        
    Raises:
        ExternalAPIError: When accommodation service is unavailable
        ValidationError: When search parameters are invalid
    """
    ...
```

### **Pydantic Models**

Use Pydantic v2 with proper validation:

```python
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

class TripStatus(str, Enum):
    """Trip status enumeration."""
    PLANNING = "planning"
    BOOKED = "booked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TripCreate(BaseModel):
    """Trip creation model with validation."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    destinations: List[str] = Field(..., min_items=1, max_items=10)
    start_date: date = Field(...)
    end_date: date = Field(...)
    budget: Optional[float] = Field(None, gt=0, le=1000000)
    travelers: int = Field(1, ge=1, le=20)
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        """Validate end date is after start date."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('start_date')
    def start_date_not_in_past(cls, v):
        """Validate start date is not in the past."""
        if v < date.today():
            raise ValueError('Start date cannot be in the past')
        return v

class TripResponse(BaseModel):
    """Trip response model."""
    id: str
    name: str
    description: Optional[str]
    destinations: List[str]
    start_date: date
    end_date: date
    budget: Optional[float]
    travelers: int
    status: TripStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy models
```

---

## TypeScript Standards

### **Interface Definitions**

Use interfaces for type safety:

```typescript
interface TripSearchParams {
  destination: string;
  startDate: Date;
  endDate: Date;
  travelers: number;
  budget?: number;
}

interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
  timestamp: string;
}
```

### **React Components**

Use TypeScript with React 19 patterns:

```typescript
'use client';

import { useState, useCallback } from 'react';
import { useTripSearch } from '@/hooks/use-trip-search';

interface TripSearchFormProps {
  onResults: (results: TripSearchResult[]) => void;
  initialParams?: Partial<TripSearchParams>;
}

export function TripSearchForm({ onResults, initialParams }: TripSearchFormProps) {
  const [params, setParams] = useState<TripSearchParams>({
    destination: '',
    startDate: new Date(),
    endDate: new Date(),
    travelers: 1,
    ...initialParams
  });
  
  const { search, isLoading, error } = useTripSearch();
  
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const results = await search(params);
    onResults(results);
  }, [params, search, onResults]);
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Form implementation */}
    </form>
  );
}
```

### **Custom Hooks**

Create reusable hooks with proper TypeScript:

```typescript
import { useState, useCallback, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  staleTime?: number;
  cacheTime?: number;
}

/**
 * Generic API hook with error handling and caching
 */
export function useApi<T>(
  key: string[],
  fetcher: () => Promise<T>,
  options: UseApiOptions<T> = {}
) {
  const queryClient = useQueryClient();
  
  const query = useQuery({
    queryKey: key,
    queryFn: fetcher,
    enabled: options.enabled !== false,
    staleTime: options.staleTime ?? 5 * 60 * 1000, // 5 minutes
    cacheTime: options.cacheTime ?? 10 * 60 * 1000, // 10 minutes
    onSuccess: options.onSuccess,
    onError: options.onError,
  });
  
  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: key });
  }, [queryClient, key]);
  
  const refetch = useCallback(() => {
    return query.refetch();
  }, [query]);
  
  return {
    ...query,
    invalidate,
    refetch,
  };
}

/**
 * Mutation hook with optimistic updates
 */
export function useMutationApi<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: {
    onSuccess?: (data: TData, variables: TVariables) => void;
    onError?: (error: Error, variables: TVariables) => void;
    invalidateQueries?: string[][];
    optimisticUpdate?: (variables: TVariables) => void;
  } = {}
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      if (options.invalidateQueries) {
        await Promise.all(
          options.invalidateQueries.map(queryKey =>
            queryClient.cancelQueries({ queryKey })
          )
        );
      }
      
      // Apply optimistic update
      options.optimisticUpdate?.(variables);
    },
    onSuccess: (data, variables) => {
      // Invalidate related queries
      if (options.invalidateQueries) {
        options.invalidateQueries.forEach(queryKey => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      
      options.onSuccess?.(data, variables);
    },
    onError: (error, variables, context) => {
      // Rollback optimistic updates if needed
      if (options.invalidateQueries) {
        options.invalidateQueries.forEach(queryKey => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      
      options.onError?.(error, variables);
    },
  });
}
```

---

## Documentation Standards

### **Code Comments**

Write clear, helpful comments:

```python
# Good: Explains why, not what
# Cache flight results for 5 minutes to reduce API calls
# and improve response times for repeated searches
@cache(expire=300)
async def search_flights(params: FlightSearchParams) -> List[FlightOption]:
    ...

# Bad: Explains what the code does (obvious)
# Get flights from API
async def search_flights(params: FlightSearchParams) -> List[FlightOption]:
    ...

# Good: Complex business logic explanation
# Apply dynamic pricing based on demand patterns:
# - High demand (>80% capacity): +15% markup
# - Medium demand (50-80%): +5% markup  
# - Low demand (<50%): No markup
def calculate_dynamic_pricing(base_price: float, demand_ratio: float) -> float:
    if demand_ratio > 0.8:
        return base_price * 1.15
    elif demand_ratio > 0.5:
        return base_price * 1.05
    return base_price
```

### **README Files**

Structure README files consistently:

```markdown
# Component/Module Name

> Brief description of what this component does

## Purpose

Detailed explanation of the component's role in the system.

## Usage

    ```python
    # Basic usage example
    from module import Component

    component = Component(config)
    result = await component.process(data)
    ```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout` | `int` | `30` | Request timeout in seconds |
| `retries` | `int` | `3` | Number of retry attempts |

## Error Handling

- `ComponentError`: Raised when component fails
- `ConfigurationError`: Raised when configuration is invalid

## Testing

    ```bash
    pytest tests/test_component.py -v
    ```

## Related

- [Related Component](../related/README.md)
- [Documentation](../../docs/component.md)

```

---

## Code Formatting

### **Python with Ruff**

```bash
# Format code
ruff format .

# Check and fix linting issues
ruff check . --fix

# Configuration in pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py312"
```

### **TypeScript with Biome**

```bash
# Format code
npx biome format . --write

# Lint and fix issues
npx biome lint --apply .

# Configuration in biome.json
{
  "formatter": {
    "lineWidth": 88,
    "indentStyle": "space"
  }
}
```

---

## Architecture Patterns

### **Service Layer Pattern**

Separate business logic from API endpoints:

```python
# services/trip_service.py
class TripService:
    """Business logic for trip management."""
    
    def __init__(self, db: AsyncSession, cache: CacheService):
        self.db = db
        self.cache = cache
    
    async def create_trip(
        self, 
        trip_data: TripCreate, 
        user_id: str
    ) -> TripResponse:
        """Create a new trip with validation and caching."""
        # Business logic here
        ...
```

### **Repository Pattern**

Abstract data access:

```python
# repositories/trip_repository.py
class TripRepository:
    """Data access layer for trips."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, trip_id: str) -> Optional[Trip]:
        """Get trip by ID."""
        return await self.db.get(Trip, trip_id)
```

---

## Security Guidelines

### **Input Validation**

Always validate and sanitize inputs:

```python
from pydantic import validator, Field

class UserInput(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    name: str = Field(..., min_length=1, max_length=100)
    
    @validator('name')
    def sanitize_name(cls, v):
        """Remove potentially dangerous characters."""
        return re.sub(r'[^a-zA-Z0-9\s\-\']', '', v).strip()
```

### **Authentication & Authorization**

Implement proper auth patterns:

```python
async def get_current_user(token: str = Depends(security)) -> User:
    """Get current user from JWT token."""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return await get_user_by_id(user_id)
```

---

## Performance Guidelines

### **Database Optimization**

Use efficient queries and caching:

```python
# Good: Efficient query with joins
async def get_trip_with_bookings(trip_id: str) -> Trip:
    """Get trip with related bookings in single query."""
    query = (
        select(Trip)
        .options(selectinload(Trip.bookings))
        .where(Trip.id == trip_id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

# Bad: N+1 query problem
async def get_trip_with_bookings_bad(trip_id: str) -> Trip:
    """Inefficient: causes N+1 queries."""
    trip = await db.get(Trip, trip_id)
    # This will cause separate query for each booking
    for booking in trip.bookings:
        print(booking.details)
    return trip

# Caching pattern
@cache(expire=300)  # 5 minutes
async def get_popular_destinations() -> List[str]:
    """Get popular destinations with caching."""
    query = (
        select(Trip.destination, func.count(Trip.id).label('count'))
        .group_by(Trip.destination)
        .order_by(func.count(Trip.id).desc())
        .limit(10)
    )
    result = await db.execute(query)
    return [row.destination for row in result]
```

### **Async Best Practices**

Use async/await efficiently:

```python
import asyncio
from typing import List

# Good: Concurrent execution
async def search_all_providers(params: SearchParams) -> List[SearchResult]:
    """Search multiple providers concurrently."""
    tasks = [
        search_flights(params),
        search_hotels(params),
        search_activities(params)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions gracefully
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.exception(f"Provider search failed: {result}")
        else:
            valid_results.extend(result)
    
    return valid_results

# Bad: Sequential execution
async def search_all_providers_bad(params: SearchParams) -> List[SearchResult]:
    """Inefficient sequential searches."""
    results = []
    results.extend(await search_flights(params))    # Wait for flights
    results.extend(await search_hotels(params))     # Then wait for hotels
    results.extend(await search_activities(params)) # Then wait for activities
    return results
```

---

## Code Review Checklist

### **Before Submitting PR**

- [ ] All tests pass (`pytest` and `pnpm test`)
- [ ] Code is formatted (`ruff format` and `biome format`)
- [ ] No linting errors (`ruff check` and `biome lint`)
- [ ] Type hints are complete
- [ ] Docstrings are added for public functions
- [ ] Error handling is implemented
- [ ] Security considerations are addressed
- [ ] Performance implications are considered

### **During Code Review**

- [ ] Code follows established patterns
- [ ] Business logic is in service layer
- [ ] Database queries are efficient
- [ ] Error messages are helpful
- [ ] Tests cover edge cases
- [ ] Documentation is updated
- [ ] Breaking changes are documented

---

### Quality Gates

- **Python**: PEP-8 compliant with ruff formatting (≤88 char lines)
- **TypeScript**: Biome for linting and formatting
- **Type Safety**: Full type hints for Python, strict TypeScript
- **Documentation**: Google-style docstrings for all public APIs

---

> **Following these coding standards ensures consistency, maintainability, and quality across the TripSage codebase.**
>
> *Last updated: October 21, 2025*
