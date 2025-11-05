# Development Guide

TripSage development patterns, architecture, and implementation details.

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI with async support
- **Language**: Python 3.13+ with full type hints
- **Database**: Supabase PostgreSQL with pgvector
- **Cache**: Upstash Redis (HTTP REST API)
- **Authentication**: Supabase JWT with middleware
- **Validation**: Pydantic models throughout

### Project Structure

```text
tripsage/
├── api/
│   ├── main.py                 # FastAPI app entry point
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   ├── dependencies.py    # DI and auth helpers
│   │   └── openapi.py         # API documentation
│   ├── routers/               # HTTP endpoints
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── trips.py
│   │   └── ...
│   ├── schemas/               # Pydantic models
│   └── middlewares/           # Custom middleware
└── app_state.py               # Service container

tripsage_core/
├── config.py                  # Settings management
├── exceptions/                # Custom exceptions
├── services/                  # Business logic
│   ├── business/             # Domain services
│   └── infrastructure/       # External integrations
└── observability/            # Logging and metrics
```

### FastAPI Application Setup

```python
# tripsage/api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from tripsage.api.core.config import get_settings
from tripsage.api.routers import (
    auth, trips, flights, accommodations, chat, users, health
)
from tripsage.api.middlewares.authentication import AuthenticationMiddleware
from tripsage.api.middlewares import install_rate_limiting
from tripsage.app_state import initialise_app_state, shutdown_app_state

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await initialise_app_state()
    yield
    await shutdown_app_state()

app = FastAPI(
    title="TripSage API",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(AuthenticationMiddleware)
install_rate_limiting(app)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
# ... other routers
```

### Authentication & Authorization

#### JWT Token Validation

```python
# tripsage/api/middlewares/authentication.py
class Principal(BaseModel):
    id: str
    type: str  # "user" or "agent"
    email: str | None = None
    scopes: list[str] = []

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Extract JWT from Authorization header
        # Validate with Supabase
        # Set request.state.principal
        return await call_next(request)
```

#### Protected Endpoints

```python
from tripsage.api.core.dependencies import RequiredPrincipalDep

@router.get("/protected")
async def protected_endpoint(principal: RequiredPrincipalDep):
    """Requires authenticated user."""
    return {"user_id": principal.id}

@router.get("/admin")
async def admin_endpoint(principal: AdminPrincipalDep):
    """Requires admin privileges."""
    return {"admin_access": True}
```

### Data Models & Validation

#### Pydantic Models

```python
# tripsage/api/schemas/trips.py
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class TripCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    destinations: List[str] = Field(..., min_items=1)
    start_date: str
    budget: Optional[float] = None

class TripResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    destinations: List[str]
    status: str  # 'planning', 'booked', 'completed'
    created_at: datetime
    updated_at: datetime
```

#### Database Schema

Core entities with relationships:

- **users**: Authentication and profile data
- **trips**: Travel plans with destinations and dates
- **flights**: Flight booking details
- **accommodations**: Hotel/car rental bookings
- **conversations**: AI chat history with embeddings
- **api_keys**: User-provided external service keys

### Database Operations

#### Supabase Integration

```python
# tripsage_core/services/infrastructure/supabase_client.py
from supabase import create_client, Client

def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(
        str(settings.database_url),
        settings.database_service_key.get_secret_value()
    )
```

#### Vector Search with pgvector

```python
# tripsage_core/services/infrastructure/vector_service.py
async def search_similar_conversations(query_embedding: list[float], limit: int = 5):
    """Find similar conversations using vector similarity."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Conversation)
            .order_by(Conversation.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        return result.scalars().all()
```

### External API Integrations

#### Service Layer Pattern

```python
# tripsage_core/services/business/flight_service.py
class FlightService:
    def __init__(self, duffel_client: DuffelClient, cache: CacheService):
        self.duffel = duffel_client
        self.cache = cache

    async def search_flights(self, origin: str, destination: str, date: str) -> List[Flight]:
        """Search for flights with caching."""
        cache_key = f"flights:{origin}:{destination}:{date}"

        # Check cache first
        if cached := await self.cache.get(cache_key):
            return cached

        # Fetch from Duffel API
        flights = await self.duffel.search_flights(origin, destination, date)

        # Cache results
        await self.cache.set(cache_key, flights, ttl=300)

        return flights
```

#### Dependency Injection

```python
# tripsage/api/core/dependencies.py
def get_flight_service(request: Request) -> FlightService:
    """Get injected flight service."""
    return _get_required_service(
        request, "flight_service", FlightService
    )

# Usage in router
@router.get("/flights")
async def search_flights(
    origin: str, destination: str, date: str,
    service: FlightService = Depends(get_flight_service)
):
    return await service.search_flights(origin, destination, date)
```

## Frontend Architecture

### Frontend Technology Stack

- **Framework**: Next.js 15 with App Router
- **React**: React 19 with concurrent features
- **Language**: TypeScript with strict mode
- **Styling**: Tailwind CSS
- **State**: Zustand for client state
- **Data**: TanStack Query for server state
- **Forms**: React Hook Form with Zod validation

### Frontend Project Structure

```text
frontend/src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Auth routes
│   ├── (dashboard)/       # Protected routes
│   └── api/               # Route handlers
├── components/            # Reusable UI components
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities and configurations
├── stores/                # Zustand state management
├── schemas/               # Zod validation schemas
└── types/                 # TypeScript definitions
```

### Data Fetching

#### TanStack Query Integration

```typescript
// lib/hooks/use-trips.ts
import { useQuery, useMutation } from "@tanstack/react-query";

export function useTrips() {
  return useQuery({
    queryKey: ["trips"],
    queryFn: async () => {
      const response = await fetch("/api/trips");
      if (!response.ok) throw new Error("Failed to fetch trips");
      return response.json();
    },
  });
}

export function useCreateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripData: TripCreate) => {
      const response = await fetch("/api/trips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tripData),
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
    },
  });
}
```

### State Management

#### Zustand Stores

```typescript
// stores/auth-store.ts
import { create } from "zustand";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: false,

  signIn: async (email, password) => {
    set({ isLoading: true });
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) throw new Error("Login failed");

      const user = await response.json();
      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  signOut: async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    set({ user: null });
  },
}));
```

### API Integration

#### Route Handlers

```typescript
// app/api/trips/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const supabase = await createServerSupabase();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: trips } = await supabase
    .from("trips")
    .select("*")
    .eq("user_id", user.id);

  return NextResponse.json(trips);
}

export async function POST(request: NextRequest) {
  const supabase = await createServerSupabase();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  const { data: trip } = await supabase
    .from("trips")
    .insert({ ...body, user_id: user.id })
    .select()
    .single();

  return NextResponse.json(trip);
}
```

### Component Patterns

#### Server Components

```typescript
// app/(dashboard)/trips/page.tsx
import { createServerSupabase } from "@/lib/supabase/server";

export default async function TripsPage() {
  const supabase = await createServerSupabase();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: trips } = await supabase
    .from("trips")
    .select("*")
    .eq("user_id", user.id);

  return (
    <div>
      <h1>My Trips</h1>
      {trips?.map((trip) => (
        <TripCard key={trip.id} trip={trip} />
      ))}
    </div>
  );
}
```

#### Client Components

```typescript
// components/trip-card.tsx
"use client";

import { useRouter } from "next/navigation";

interface TripCardProps {
  trip: Trip;
}

export function TripCard({ trip }: TripCardProps) {
  const router = useRouter();

  const handleEdit = () => {
    router.push(`/trips/${trip.id}/edit`);
  };

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold">{trip.name}</h3>
      <p className="text-sm text-gray-600">
        {trip.destinations.join(", ")}
      </p>
      <button
        onClick={handleEdit}
        className="mt-2 px-3 py-1 bg-blue-500 text-white rounded"
      >
        Edit Trip
      </button>
    </div>
  );
}
```

## Database Design

### Supabase PostgreSQL

#### Why Supabase

- Managed PostgreSQL service
- Built-in authentication and RLS
- Real-time subscriptions
- Extension ecosystem including pgvector

#### Core Tables

```sql
-- Users (managed by Supabase Auth)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Trips
CREATE TABLE trips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  destinations TEXT[] NOT NULL,
  start_date DATE,
  budget DECIMAL,
  status TEXT DEFAULT 'planning',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations with embeddings
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  message TEXT NOT NULL,
  embedding VECTOR(1536), -- OpenAI ada-002 dimensions
  created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys (encrypted)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  service TEXT NOT NULL,
  encrypted_key TEXT NOT NULL,
  is_valid BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Vector Search

#### pgvector Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create vector column
ALTER TABLE conversations ADD COLUMN embedding VECTOR(1536);

-- Create vector index for similarity search
CREATE INDEX ON conversations USING ivfflat (embedding vector_cosine_ops);
```

#### Similarity Search

```python
# tripsage_core/services/business/memory_service.py
async def find_similar_conversations(query: str, limit: int = 5) -> List[Conversation]:
    """Find conversations similar to query using vector search."""
    # Generate embedding for query
    embedding = await self.openai_client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    )

    # Search for similar conversations
    async with get_db_session() as session:
        result = await session.execute(
            select(Conversation)
            .order_by(Conversation.embedding.cosine_distance(embedding.data[0].embedding))
            .limit(limit)
        )
        return result.scalars().all()
```

## API Development Patterns

### Endpoint Structure

```python
# tripsage/api/routers/trips.py
from fastapi import APIRouter, Depends, HTTPException
from tripsage.api.schemas.trips import TripCreate, TripResponse
from tripsage.api.core.dependencies import RequiredPrincipalDep, get_trip_service

router = APIRouter(prefix="/trips", tags=["trips"])

@router.get("/", response_model=List[TripResponse])
async def list_trips(
    principal: RequiredPrincipalDep,
    service: TripService = Depends(get_trip_service)
):
    """List user's trips."""
    return await service.get_user_trips(principal.id)

@router.post("/", response_model=TripResponse, status_code=201)
async def create_trip(
    trip_data: TripCreate,
    principal: RequiredPrincipalDep,
    service: TripService = Depends(get_trip_service)
):
    """Create a new trip."""
    return await service.create_trip(principal.id, trip_data)
```

### Error Handling

```python
# tripsage_core/exceptions/exceptions.py
from pydantic import BaseModel

class CoreTripSageError(Exception):
    """Base exception for TripSage errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str | None = None,
        details: dict | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or self.__class__.__name__
        self.details = details or {}

# Usage
raise CoreTripSageError(
    "Trip not found",
    status_code=404,
    code="TRIP_NOT_FOUND"
)
```

### Streaming Responses

```python
# tripsage/api/routers/chat.py
from fastapi.responses import StreamingResponse

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    principal: RequiredPrincipalDep,
    service: ChatService = Depends(get_chat_service)
):
    """Stream chat responses."""
    async def generate():
        async for chunk in service.stream_chat(request.message, principal.id):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
```

## Observability

### Structured Logging

The project uses OpenTelemetry trace correlation to inject `trace_id` and `span_id` into Python log records for correlating logs with traces in observability backends.

#### Enable Trace Correlation

The application automatically installs trace correlation at startup in `tripsage/api/main.py`. For custom services, call:

```python
from tripsage_core.observability.log_correlation import install_trace_log_correlation
install_trace_log_correlation()  # Applies to root logger
```

#### Logging Formatter Configuration

Configure your logging format to include trace correlation fields:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s %(levelname)s %(trace_id)s %(span_id)s "
        "%(name)s: %(message)s"
    ),
)
```

This produces log lines like:

```text
2025-10-22 10:14:32,123 INFO f1ab... 9cde... tripsage.api.routers.trips: Creating trip for user: 123
```

If no span is active, the `trace_id` and `span_id` fields are empty strings.

#### Notes

- The filter is safe: if OpenTelemetry isn't installed or no span is active, logging continues normally
- Prefer a single OTEL pipeline (OTLP) and avoid enabling multiple exporters in the same process

### Metrics Collection

The API emits duration metrics via OpenTelemetry, including request and operation histograms. Duration histogram bucket boundaries can be tuned at runtime using the `TRIPSAGE_DURATION_BUCKETS` environment variable.

#### Duration Histogram Buckets

The application reads `TRIPSAGE_DURATION_BUCKETS` during OTEL setup in `tripsage_core/observability/otel.py`. If set, the value is parsed as a comma-separated list of bucket boundaries in seconds.

**Default buckets:**

```text
0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
```

**Override buckets via environment variable:**

```bash
export TRIPSAGE_DURATION_BUCKETS=0.01,0.02,0.05,0.1,0.25,0.5,1,2,5
# Restart the service so OTEL setup re-runs with new buckets
```

**Docker Compose:**

```yaml
services:
  api:
    environment:
      TRIPSAGE_DURATION_BUCKETS: "0.01,0.02,0.05,0.1,0.25,0.5,1,2,5"
```

#### Metrics Middleware Example

```python
# tripsage/api/middlewares/metrics.py
from tripsage_core.observability.otel import record_histogram

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        record_histogram(
            "api.request.duration",
            duration,
            attributes={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code
            }
        )

        return response
```

#### Duration Histogram Considerations

- Buckets are global for the process; keep them consistent across services for simpler dashboards and SLOs
- Avoid excessive bucket counts; they increase exporter payload size and cardinality
- Start with ≤ 10-12 buckets and adjust based on latency profiles
- If the OTEL SDK doesn't expose the optional view API, the application falls back to provider defaults

## Performance Optimization

### Database Query Optimization

- Use select() with specific columns
- Implement proper indexing
- Use connection pooling
- Cache frequently accessed data

### Caching Strategy

```python
# tripsage_core/services/infrastructure/cache_service.py
class CacheService:
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        # Upstash Redis implementation
        pass

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        # Upstash Redis implementation
        pass
```

### Async Best Practices

- Use async/await for all I/O operations
- Implement proper connection pooling
- Use streaming for large responses
- Handle backpressure appropriately

## Security Considerations

### Input Validation

```python
# tripsage/api/schemas/common.py
from pydantic import BaseModel, Field, validator
import re

class SanitizedString(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("String required")
        # Basic XSS prevention
        v = re.sub(r'<[^>]*>', '', v)
        return cls(v)

class SecureInput(BaseModel):
    user_input: SanitizedString = Field(..., max_length=1000)
```

### Rate Limiting

```python
# tripsage/api/limiting.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to routes
@router.get("/search")
@limiter.limit("10/minute")
async def search_endpoint():
    pass
```

### Row Level Security

```sql
-- Enable RLS on trips table
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own trips
CREATE POLICY "Users can view own trips" ON trips
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can only modify their own trips
CREATE POLICY "Users can modify own trips" ON trips
    FOR ALL USING (auth.uid() = user_id);
```
