# TripSage AI Developer Guide

> **Complete Developer Documentation for TripSage AI**  
> Modern FastAPI + Next.js architecture with AI agents, real-time collaboration, and enterprise-grade performance

## Table of Contents

- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Code Standards](#code-standards)
- [Testing Framework](#testing-framework)
- [Development Workflow](#development-workflow)
- [API Development](#api-development)
- [Frontend Development](#frontend-development)
- [Database Development](#database-development)
- [AI Agent Development](#ai-agent-development)
- [Performance Optimization](#performance-optimization)
- [Security Guidelines](#security-guidelines)
- [Deployment Process](#deployment-process)

---

## Development Setup

### Prerequisites

- **Python 3.12+** with `uv` package manager
- **Node.js 18+** with `pnpm`
- **Docker** for local services
- **Git** for version control
- **VS Code** with recommended extensions

### Quick Start

```bash
# Clone and setup backend
git clone https://github.com/your-org/tripsage-ai.git
cd tripsage-ai

# Install Python dependencies with uv
uv sync

# Setup frontend
cd frontend
pnpm install
cd ..

# Start local services
docker-compose up -d

# Run database migrations
uv run python scripts/database/run_migrations.py

# Start development servers
uv run python -m tripsage.api.main &  # Backend on :8001
cd frontend && pnpm dev               # Frontend on :3000
```

### Environment Configuration

Create `.env` file with development settings:

```env
# Development Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database (Local Supabase)
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
DATABASE_PUBLIC_KEY=your_supabase_public_key
DATABASE_SERVICE_KEY=your_supabase_service_key

# Cache (Local DragonflyDB)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=development_password

# AI Services (Development Keys)
OPENAI_API_KEY=sk-dev-your-openai-key
OPENAI_MODEL=gpt-4o-mini  # Cost-effective for development

# External APIs (Development/Test Keys)
DUFFEL_API_KEY=duffel_test_your_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
OPENWEATHER_API_KEY=your_openweather_key

# Development Settings
API_TITLE=TripSage Dev API
API_VERSION=1.0.0-dev
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
RATE_LIMIT_REQUESTS=1000  # Higher limits for development
```

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode.vscode-json",
    "ms-vscode.docker",
    "GitHub.copilot"
  ]
}
```

---

## Architecture Overview

### System Architecture

```mermaid
graph TB
    A[Next.js Frontend] --> B[FastAPI Backend]
    B --> C[Supabase PostgreSQL]
    B --> D[DragonflyDB Cache]
    B --> E[Mem0 Memory System]
    B --> F[LangGraph Agents]
    F --> G[External APIs]
    
    subgraph "External Services"
        G1[Duffel - Flights]
        G2[Google Maps]
        G3[OpenWeather]
        G4[Crawl4AI]
    end
    
    G --> G1
    G --> G2
    G --> G3
    G --> G4
```

### Technology Stack

#### Backend (Python)
- **FastAPI**: Modern async web framework
- **Pydantic v2**: Type-safe data validation
- **LangGraph**: AI agent orchestration
- **Asyncio**: Concurrent programming
- **Pytest**: Testing framework
- **Ruff**: Linting and formatting

#### Frontend (TypeScript)
- **Next.js 15**: React framework with App Router
- **React 19**: Latest React with concurrent features
- **TypeScript 5.5+**: Type safety
- **Tailwind CSS v4**: Utility-first styling
- **Vitest**: Fast testing framework
- **Biome**: Fast linting and formatting

#### Data Layer
- **Supabase**: PostgreSQL with real-time features
- **pgvector**: Vector embeddings for AI
- **DragonflyDB**: High-performance caching
- **Mem0**: Intelligent AI memory management

### Project Structure

```
tripsage-ai/
├── tripsage/                    # API package
│   ├── api/                     # FastAPI application
│   │   ├── core/               # Core configuration
│   │   ├── middlewares/        # Custom middleware
│   │   ├── routers/            # API endpoints
│   │   └── schemas/            # Pydantic models
│   ├── agents/                 # AI agent nodes
│   ├── orchestration/          # LangGraph orchestration
│   └── tools/                  # Agent tools
├── tripsage_core/              # Core business logic
│   ├── services/               # Business services
│   ├── models/                 # Database models
│   ├── utils/                  # Utility functions
│   └── config.py              # Configuration management
├── frontend/                   # Next.js application
│   ├── src/app/               # App Router pages
│   ├── src/components/        # React components
│   ├── src/hooks/             # Custom hooks
│   └── src/stores/            # State management
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── scripts/                   # Development scripts
└── docs/                      # Documentation
```

---

## Code Standards

### Python Code Standards

#### Type Hints
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

#### Error Handling
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

#### Async/Await Pattern
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

#### Docstrings
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

### TypeScript Code Standards

#### Interface Definitions
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

#### React Components
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

### Code Formatting

#### Python with Ruff
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

#### TypeScript with Biome
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

## Testing Framework

### Python Testing with Pytest

#### Test Structure
```
tests/
├── unit/                      # Fast, isolated tests
│   ├── services/             # Service layer tests
│   ├── models/               # Model validation tests
│   └── utils/                # Utility function tests
├── integration/              # Service integration tests
│   ├── api/                  # API endpoint tests
│   ├── database/             # Database integration
│   └── external/             # External API integration
├── e2e/                      # End-to-end scenarios
└── conftest.py              # Shared fixtures
```

#### Example Unit Test
```python
import pytest
from unittest.mock import AsyncMock, patch
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.models.schemas_common.travel import FlightSearchParams

@pytest.mark.asyncio
class TestFlightService:
    async def test_search_flights_success(self, flight_service: FlightService):
        """Test successful flight search."""
        # Arrange
        search_params = FlightSearchParams(
            origin="NYC",
            destination="LAX",
            departure_date="2025-06-01",
            passengers=1
        )
        
        # Act
        results = await flight_service.search_flights(search_params)
        
        # Assert
        assert len(results) > 0
        assert all(flight.origin == "NYC" for flight in results)
        assert all(flight.destination == "LAX" for flight in results)
    
    async def test_search_flights_external_api_error(
        self, flight_service: FlightService
    ):
        """Test handling of external API errors."""
        with patch.object(flight_service.duffel_client, 'search_flights') as mock_search:
            mock_search.side_effect = ExternalAPIError("Duffel API unavailable")
            
            search_params = FlightSearchParams(
                origin="NYC",
                destination="LAX",
                departure_date="2025-06-01",
                passengers=1
            )
            
            with pytest.raises(ExternalAPIError):
                await flight_service.search_flights(search_params)
```

#### Example Integration Test
```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestTripAPI:
    async def test_create_trip_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test trip creation through API."""
        trip_data = {
            "name": "European Adventure",
            "destinations": ["Paris", "Rome"],
            "start_date": "2025-06-01",
            "end_date": "2025-06-14",
            "budget": 5000
        }
        
        response = await client.post(
            "/api/trips",
            json=trip_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == trip_data["name"]
        assert "id" in data
```

#### Running Tests
```bash
# Run all tests with coverage
uv run pytest

# Run specific test categories
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m e2e

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/unit/services/test_flight_service.py

# Run with coverage report
uv run pytest --cov=tripsage --cov-report=html
```

### Frontend Testing with Vitest

#### Component Tests
```typescript
import { render, screen, userEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TripSearchForm } from '@/components/search/trip-search-form';

describe('TripSearchForm', () => {
  it('should submit search with correct parameters', async () => {
    const mockOnResults = vi.fn();
    const user = userEvent.setup();
    
    render(<TripSearchForm onResults={mockOnResults} />);
    
    // Fill form
    await user.type(screen.getByLabelText(/destination/i), 'Paris');
    await user.selectOptions(screen.getByLabelText(/travelers/i), '2');
    
    // Submit
    await user.click(screen.getByRole('button', { name: /search/i }));
    
    expect(mockOnResults).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          destination: 'Paris',
          travelers: 2
        })
      ])
    );
  });
});
```

#### Hook Tests
```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useTripSearch } from '@/hooks/use-trip-search';

describe('useTripSearch', () => {
  it('should return search results', async () => {
    const { result } = renderHook(() => useTripSearch());
    
    const searchParams = {
      destination: 'Tokyo',
      startDate: new Date('2025-06-01'),
      endDate: new Date('2025-06-14'),
      travelers: 2
    };
    
    await result.current.search(searchParams);
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.results).toHaveLength(2);
    });
  });
});
```

---

## Development Workflow

### Git Workflow

#### Branch Naming
- `feature/trip-search-enhancement`
- `bugfix/memory-leak-fix`
- `docs/api-documentation-update`
- `refactor/service-layer-cleanup`

#### Commit Messages
Follow conventional commits:

```bash
git commit -m "feat: add flight search with budget filtering

- Implement budget-based flight filtering
- Add price range validation
- Update flight search API endpoint
- Include comprehensive test coverage

Closes #123"
```

#### Pull Request Process
1. Create feature branch from `main`
2. Implement changes with tests
3. Run linting and formatting
4. Create pull request with description
5. Address review feedback
6. Merge with squash commit

### Code Review Guidelines

#### Checklist for Reviewers
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] Error handling is comprehensive

#### Review Template
```markdown
## Summary
Brief description of changes

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Performance
- [ ] No performance regressions
- [ ] Efficient database queries
- [ ] Appropriate caching used

## Security
- [ ] Input validation added
- [ ] Authentication/authorization checked
- [ ] No sensitive data exposed
```

### Development Commands

#### Backend Development
```bash
# Start API server with auto-reload
uv run python -m tripsage.api.main

# Run database migrations
uv run python scripts/database/run_migrations.py

# Run specific test suite
uv run pytest tests/unit/services/ -v

# Generate migration
uv run python scripts/database/create_migration.py "add_user_preferences"

# Format and lint code
ruff format . && ruff check . --fix

# Type checking
uv run mypy tripsage/ tripsage_core/

# Start development with debug
DEBUG=true uv run python -m tripsage.api.main
```

#### Frontend Development
```bash
# Start Next.js development server
pnpm dev

# Run tests in watch mode
pnpm test

# Run tests with coverage
pnpm test:coverage

# Format and lint code
pnpm lint:fix && pnpm format

# Type checking
pnpm type-check

# Build for production
pnpm build

# Analyze bundle size
pnpm analyze
```

#### Docker Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f frontend

# Rebuild specific service
docker-compose build api

# Run tests in container
docker-compose run --rm api pytest

# Access database
docker-compose exec postgres psql -U postgres
```

---

## API Development

### Endpoint Development

#### Router Structure
```python
from fastapi import APIRouter, Depends, HTTPException, status
from tripsage.api.core.dependencies import get_current_user, get_db
from tripsage.api.schemas.trips import TripCreate, TripResponse
from tripsage_core.services.business.trip_service import TripService

router = APIRouter()

@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_data: TripCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    trip_service: TripService = Depends()
) -> TripResponse:
    """Create a new trip.
    
    Creates a new trip for the authenticated user with the provided details.
    The trip will be initialized with default settings and can be customized later.
    """
    try:
        trip = await trip_service.create_trip(
            trip_data=trip_data,
            user_id=current_user.id,
            db=db
        )
        return TripResponse.model_validate(trip)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trip data: {e}"
        ) from e
```

#### Schema Definitions
```python
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from tripsage_core.models.schemas_common.enums import TripStatus

class TripCreate(BaseModel):
    """Schema for creating a new trip."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget: Optional[float] = Field(None, gt=0, description="Trip budget in USD")
    destinations: List[str] = Field(..., min_items=1, max_items=10)
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: date, info) -> date:
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('End date must be after start date')
        return v

class TripResponse(BaseModel):
    """Schema for trip response."""
    id: str
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    budget: Optional[float]
    destinations: List[str]
    status: TripStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Middleware Development

#### Custom Middleware
```python
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Add request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        # Log slow requests
        if duration > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {duration:.3f}s",
                extra={"request_id": request_id, "duration": duration}
            )
        
        return response
```

### WebSocket Development

#### WebSocket Handler
```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from tripsage_core.services.infrastructure.websocket_manager import WebSocketManager

@router.websocket("/chat/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str,
    websocket_manager: WebSocketManager = Depends()
):
    """WebSocket endpoint for real-time chat."""
    user = await authenticate_websocket_token(token)
    await websocket_manager.connect(websocket, user.id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "user_message":
                # Process user message through AI agents
                response = await process_user_message(
                    message=data["content"],
                    user_id=user.id,
                    session_id=data.get("session_id")
                )
                
                # Broadcast response
                await websocket_manager.send_message(
                    user_id=user.id,
                    message={
                        "type": "ai_response",
                        "content": response.content,
                        "session_id": data["session_id"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, user.id)
```

---

## Frontend Development

### Component Development

#### Component Structure
```typescript
'use client';

import { forwardRef, memo } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, children, ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-primary text-primary-foreground hover:bg-primary/90': variant === 'primary',
            'bg-secondary text-secondary-foreground hover:bg-secondary/80': variant === 'secondary',
            'border border-input hover:bg-accent hover:text-accent-foreground': variant === 'outline',
            'hover:bg-accent hover:text-accent-foreground': variant === 'ghost',
          },
          {
            'h-9 px-3 text-sm': size === 'sm',
            'h-10 px-4 py-2': size === 'md',
            'h-11 px-8 text-lg': size === 'lg',
          },
          className
        )}
        ref={ref}
        disabled={loading || props.disabled}
        {...props}
      >
        {loading && (
          <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default memo(Button);
```

### State Management

#### Zustand Store
```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface Trip {
  id: string;
  name: string;
  destinations: string[];
  startDate: Date;
  endDate: Date;
  budget?: number;
  status: 'planning' | 'booked' | 'completed';
}

interface TripStore {
  trips: Trip[];
  currentTrip: Trip | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchTrips: () => Promise<void>;
  createTrip: (tripData: Omit<Trip, 'id'>) => Promise<void>;
  updateTrip: (id: string, updates: Partial<Trip>) => Promise<void>;
  deleteTrip: (id: string) => Promise<void>;
  setCurrentTrip: (trip: Trip | null) => void;
  clearError: () => void;
}

export const useTripStore = create<TripStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        trips: [],
        currentTrip: null,
        isLoading: false,
        error: null,
        
        fetchTrips: async () => {
          set((state) => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            const response = await fetch('/api/trips');
            const trips = await response.json();
            
            set((state) => {
              state.trips = trips;
              state.isLoading = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to fetch trips';
              state.isLoading = false;
            });
          }
        },
        
        createTrip: async (tripData) => {
          set((state) => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            const response = await fetch('/api/trips', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(tripData),
            });
            
            const newTrip = await response.json();
            
            set((state) => {
              state.trips.push(newTrip);
              state.isLoading = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to create trip';
              state.isLoading = false;
            });
          }
        },
        
        updateTrip: async (id, updates) => {
          try {
            const response = await fetch(`/api/trips/${id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(updates),
            });
            
            const updatedTrip = await response.json();
            
            set((state) => {
              const index = state.trips.findIndex(trip => trip.id === id);
              if (index !== -1) {
                state.trips[index] = updatedTrip;
              }
              if (state.currentTrip?.id === id) {
                state.currentTrip = updatedTrip;
              }
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to update trip';
            });
          }
        },
        
        deleteTrip: async (id) => {
          try {
            await fetch(`/api/trips/${id}`, { method: 'DELETE' });
            
            set((state) => {
              state.trips = state.trips.filter(trip => trip.id !== id);
              if (state.currentTrip?.id === id) {
                state.currentTrip = null;
              }
            });
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Failed to delete trip';
            });
          }
        },
        
        setCurrentTrip: (trip) => {
          set((state) => {
            state.currentTrip = trip;
          });
        },
        
        clearError: () => {
          set((state) => {
            state.error = null;
          });
        },
      })),
      {
        name: 'trip-store',
        partialize: (state) => ({
          trips: state.trips,
          currentTrip: state.currentTrip,
        }),
      }
    ),
    { name: 'TripStore' }
  )
);
```

### Custom Hooks

#### API Hook with Error Handling
```typescript
import { useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

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

export function useMutationApi<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: {
    onSuccess?: (data: TData, variables: TVariables) => void;
    onError?: (error: Error, variables: TVariables) => void;
    invalidateQueries?: string[][];
  } = {}
) {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn,
    onSuccess: (data, variables) => {
      // Invalidate related queries
      if (options.invalidateQueries) {
        options.invalidateQueries.forEach(queryKey => {
          queryClient.invalidateQueries({ queryKey });
        });
      }
      
      options.onSuccess?.(data, variables);
    },
    onError: options.onError,
  });
}
```

---

## Database Development

### Migration Development

#### Creating Migrations
```python
# scripts/database/create_migration.py
import asyncio
from datetime import datetime
from pathlib import Path

async def create_migration(name: str, description: str = ""):
    """Create a new database migration file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name.lower().replace(' ', '_')}.sql"
    
    migration_path = Path("scripts/database/migrations") / filename
    
    template = f"""-- Migration: {name}
-- Description: {description}
-- Created: {datetime.now().isoformat()}

-- Add your migration SQL here
-- Remember to include both UP and DOWN operations

-- Example:
-- CREATE TABLE example (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name TEXT NOT NULL,
--     created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- Add indexes
-- CREATE INDEX idx_example_name ON example(name);

-- Add RLS policies
-- ALTER TABLE example ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY example_policy ON example FOR ALL TO authenticated USING (true);
"""
    
    migration_path.write_text(template)
    print(f"Migration created: {migration_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python create_migration.py <migration_name> [description]")
        sys.exit(1)
    
    name = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else ""
    
    asyncio.run(create_migration(name, description))
```

#### Migration Runner
```python
# scripts/database/run_migrations.py
import asyncio
import logging
from pathlib import Path
from typing import List

import asyncpg
from tripsage_core.config import get_settings

logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_path = Path("scripts/database/migrations")
    
    async def run_migrations(self) -> None:
        """Run all pending migrations."""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            # Create migrations table if it doesn't exist
            await self._create_migrations_table(conn)
            
            # Get applied migrations
            applied = await self._get_applied_migrations(conn)
            
            # Get all migration files
            all_migrations = self._get_migration_files()
            
            # Filter pending migrations
            pending = [m for m in all_migrations if m not in applied]
            
            if not pending:
                logger.info("No pending migrations")
                return
            
            # Apply pending migrations
            for migration in pending:
                await self._apply_migration(conn, migration)
                logger.info(f"Applied migration: {migration}")
            
            logger.info(f"Applied {len(pending)} migrations successfully")
            
        finally:
            await conn.close()
    
    async def _create_migrations_table(self, conn: asyncpg.Connection) -> None:
        """Create the migrations tracking table."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    
    async def _get_applied_migrations(self, conn: asyncpg.Connection) -> List[str]:
        """Get list of applied migrations."""
        rows = await conn.fetch("SELECT filename FROM _migrations ORDER BY filename")
        return [row['filename'] for row in rows]
    
    def _get_migration_files(self) -> List[str]:
        """Get sorted list of migration files."""
        files = [f.name for f in self.migrations_path.glob("*.sql")]
        return sorted(files)
    
    async def _apply_migration(self, conn: asyncpg.Connection, filename: str) -> None:
        """Apply a single migration."""
        migration_path = self.migrations_path / filename
        sql = migration_path.read_text()
        
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO _migrations (filename) VALUES ($1)",
                filename
            )

async def main():
    settings = get_settings()
    runner = MigrationRunner(settings.database_url)
    await runner.run_migrations()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### Database Models

#### Pydantic Model with SQLAlchemy Integration
```python
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TripModel(Base):
    """SQLAlchemy model for trips."""
    __tablename__ = "trips"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    budget = Column(Float)
    destinations = Column(JSONB)
    status = Column(String(50), default="planning")
    preferences = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserModel", back_populates="trips")
    flight_searches = relationship("FlightSearchModel", back_populates="trip")
    accommodations = relationship("AccommodationModel", back_populates="trip")

class Trip(BaseModel):
    """Pydantic model for trips."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    budget: Optional[float] = Field(None, gt=0)
    destinations: List[str] = Field(default_factory=list)
    status: str = Field(default="planning")
    preferences: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

---

## AI Agent Development

### LangGraph Agent Implementation

#### Agent Node Definition
```python
from typing import Dict, Any, List
from langgraph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from tripsage.orchestration.state import TripPlanningState
from tripsage_core.services.external_apis.duffel_http_client import DuffelHTTPClient

class FlightSearchAgent:
    """Agent responsible for flight search and recommendations."""
    
    def __init__(self, duffel_client: DuffelHTTPClient):
        self.duffel_client = duffel_client
        self.name = "flight_search_agent"
    
    async def __call__(self, state: TripPlanningState) -> Dict[str, Any]:
        """Execute flight search based on current state."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        if not isinstance(last_message, HumanMessage):
            return {"messages": messages}
        
        # Extract flight search parameters from user message
        search_params = await self._extract_flight_params(last_message.content)
        
        if not search_params:
            return {
                "messages": messages + [
                    AIMessage(content="I need more information about your flight preferences. Please provide origin, destination, and travel dates.")
                ]
            }
        
        # Search for flights
        try:
            flight_options = await self.duffel_client.search_flights(search_params)
            
            # Format response
            response = await self._format_flight_response(flight_options)
            
            return {
                "messages": messages + [AIMessage(content=response)],
                "flight_options": flight_options,
                "current_agent": self.name
            }
            
        except Exception as e:
            error_message = f"I encountered an issue searching for flights: {str(e)}"
            return {
                "messages": messages + [AIMessage(content=error_message)],
                "errors": [str(e)]
            }
    
    async def _extract_flight_params(self, user_input: str) -> Dict[str, Any]:
        """Extract flight search parameters from user input using LLM."""
        # Implementation would use LLM to parse natural language into structured params
        # For brevity, showing simplified version
        return {
            "origin": "NYC",  # Extracted from user input
            "destination": "LAX",
            "departure_date": "2025-06-01",
            "passengers": 1
        }
    
    async def _format_flight_response(self, flight_options: List[Dict]) -> str:
        """Format flight options into user-friendly response."""
        if not flight_options:
            return "I couldn't find any flights matching your criteria. Would you like to adjust your search parameters?"
        
        response = f"I found {len(flight_options)} flight options for you:\n\n"
        
        for i, flight in enumerate(flight_options[:3], 1):  # Show top 3
            response += f"{i}. {flight['airline']} - ${flight['price']}\n"
            response += f"   Departure: {flight['departure_time']}\n"
            response += f"   Arrival: {flight['arrival_time']}\n"
            response += f"   Duration: {flight['duration']}\n\n"
        
        response += "Would you like to see more options or book one of these flights?"
        return response
```

#### Graph Configuration
```python
from langgraph import StateGraph, END
from tripsage.orchestration.nodes import (
    FlightSearchAgent,
    AccommodationSearchAgent,
    ItineraryPlanningAgent,
    BudgetOptimizationAgent
)

def create_trip_planning_graph():
    """Create the trip planning agent graph."""
    
    # Initialize agents
    flight_agent = FlightSearchAgent(duffel_client)
    accommodation_agent = AccommodationSearchAgent()
    itinerary_agent = ItineraryPlanningAgent()
    budget_agent = BudgetOptimizationAgent()
    
    # Create graph
    graph = StateGraph(TripPlanningState)
    
    # Add nodes
    graph.add_node("flight_search", flight_agent)
    graph.add_node("accommodation_search", accommodation_agent)
    graph.add_node("itinerary_planning", itinerary_agent)
    graph.add_node("budget_optimization", budget_agent)
    
    # Define routing logic
    def route_next_agent(state: TripPlanningState) -> str:
        """Determine the next agent based on current state."""
        last_message = state.get("messages", [])[-1]
        current_agent = state.get("current_agent")
        
        # Simple routing logic - could be enhanced with LLM decision making
        if "flight" in last_message.content.lower() and current_agent != "flight_search":
            return "flight_search"
        elif "hotel" in last_message.content.lower() and current_agent != "accommodation_search":
            return "accommodation_search"
        elif "itinerary" in last_message.content.lower() and current_agent != "itinerary_planning":
            return "itinerary_planning"
        elif "budget" in last_message.content.lower() and current_agent != "budget_optimization":
            return "budget_optimization"
        else:
            return END
    
    # Add edges
    graph.add_conditional_edges(
        "flight_search",
        route_next_agent,
        {
            "accommodation_search": "accommodation_search",
            "itinerary_planning": "itinerary_planning",
            "budget_optimization": "budget_optimization",
            END: END
        }
    )
    
    # Set entry point
    graph.set_entry_point("flight_search")
    
    return graph.compile()
```

### Agent Tools

#### Tool Definition
```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

class FlightSearchTool(BaseTool):
    """Tool for searching flights using Duffel API."""
    
    name: str = "flight_search"
    description: str = """
    Search for flights between two destinations.
    Use this tool when users ask about flights, airfare, or travel between cities.
    """
    
    duffel_client: Any = Field(exclude=True)
    
    class FlightSearchInput(BaseModel):
        origin: str = Field(description="Origin airport code or city")
        destination: str = Field(description="Destination airport code or city")
        departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
        return_date: Optional[str] = Field(None, description="Return date for round trip")
        passengers: int = Field(default=1, description="Number of passengers")
        cabin_class: str = Field(default="economy", description="Cabin class preference")
    
    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute flight search synchronously."""
        import asyncio
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute flight search asynchronously."""
        try:
            # Validate input
            search_input = self.FlightSearchInput(**kwargs)
            
            # Search flights
            results = await self.duffel_client.search_flights({
                "origin": search_input.origin,
                "destination": search_input.destination,
                "departure_date": search_input.departure_date,
                "return_date": search_input.return_date,
                "passengers": search_input.passengers,
                "cabin_class": search_input.cabin_class
            })
            
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "message": f"Found {len(results)} flight options"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Flight search failed: {str(e)}"
            }
```

---

## Performance Optimization

### Database Optimization

#### Query Optimization
```python
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload

async def get_trips_with_details(
    user_id: UUID,
    db: AsyncSession,
    limit: int = 10,
    offset: int = 0
) -> List[TripModel]:
    """Optimized query to get trips with related data."""
    
    # Use selectinload for one-to-many relationships
    # Use joinedload for many-to-one relationships
    query = (
        select(TripModel)
        .where(TripModel.user_id == user_id)
        .options(
            joinedload(TripModel.user),  # Many-to-one
            selectinload(TripModel.flight_searches),  # One-to-many
            selectinload(TripModel.accommodations)   # One-to-many
        )
        .order_by(TripModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    return result.unique().scalars().all()

# Index creation for performance
"""
-- In migration file
CREATE INDEX CONCURRENTLY idx_trips_user_created 
ON trips(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_flights_trip_date 
ON flight_searches(trip_id, departure_date);

-- Partial index for active trips
CREATE INDEX CONCURRENTLY idx_trips_active 
ON trips(user_id, updated_at) 
WHERE status IN ('planning', 'booked');
"""
```

#### Caching Strategy
```python
from functools import wraps
from typing import Any, Callable, Optional
import json
import hashlib
from tripsage_core.services.infrastructure.cache_service import CacheService

def cache_result(
    ttl: int = 300,  # 5 minutes default
    key_prefix: str = "",
    use_args: bool = True,
    use_kwargs: bool = True
):
    """Decorator to cache function results."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = CacheService()
            
            # Generate cache key
            if use_args or use_kwargs:
                key_data = {
                    "func": f"{func.__module__}.{func.__name__}",
                    "args": args if use_args else [],
                    "kwargs": kwargs if use_kwargs else {}
                }
                key_hash = hashlib.md5(
                    json.dumps(key_data, sort_keys=True, default=str).encode()
                ).hexdigest()
                cache_key = f"{key_prefix}:{key_hash}" if key_prefix else key_hash
            else:
                cache_key = f"{key_prefix}:{func.__name__}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator

# Usage example
@cache_result(ttl=3600, key_prefix="flights")
async def search_flights_cached(search_params: FlightSearchParams) -> List[Flight]:
    """Cached flight search."""
    return await duffel_client.search_flights(search_params)
```

### API Performance

#### Response Optimization
```python
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncGenerator

async def stream_trip_recommendations(
    trip_id: str,
    user_id: str
) -> AsyncGenerator[str, None]:
    """Stream trip recommendations as they're generated."""
    
    yield "data: {\"type\": \"start\", \"message\": \"Generating recommendations...\"}\n\n"
    
    # Generate recommendations in chunks
    async for recommendation in generate_recommendations_async(trip_id):
        data = {
            "type": "recommendation",
            "data": recommendation,
            "timestamp": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(data)}\n\n"
    
    yield "data: {\"type\": \"complete\", \"message\": \"Recommendations complete\"}\n\n"

@router.get("/trips/{trip_id}/recommendations/stream")
async def stream_recommendations(
    trip_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stream trip recommendations using Server-Sent Events."""
    return StreamingResponse(
        stream_trip_recommendations(trip_id, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Background task processing
async def process_trip_optimization(trip_id: str, user_id: str):
    """Process trip optimization in background."""
    try:
        # Heavy computation
        optimized_itinerary = await optimize_trip_itinerary(trip_id)
        
        # Update database
        await update_trip_optimization_results(trip_id, optimized_itinerary)
        
        # Notify user via WebSocket
        await websocket_manager.send_to_user(
            user_id,
            {
                "type": "optimization_complete",
                "trip_id": trip_id,
                "data": optimized_itinerary
            }
        )
        
    except Exception as e:
        logger.error(f"Trip optimization failed: {e}")
        await websocket_manager.send_to_user(
            user_id,
            {
                "type": "optimization_error",
                "trip_id": trip_id,
                "error": str(e)
            }
        )

@router.post("/trips/{trip_id}/optimize")
async def optimize_trip(
    trip_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start trip optimization in background."""
    background_tasks.add_task(
        process_trip_optimization,
        trip_id,
        current_user.id
    )
    
    return {"message": "Optimization started", "status": "processing"}
```

### Frontend Performance

#### Component Optimization
```typescript
import { memo, useMemo, useCallback, lazy, Suspense } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

// Lazy loading for code splitting
const TripDetailsModal = lazy(() => import('./trip-details-modal'));

interface TripListProps {
  trips: Trip[];
  onTripSelect: (trip: Trip) => void;
  searchTerm: string;
}

export const TripList = memo<TripListProps>(({ trips, onTripSelect, searchTerm }) => {
  // Memoize filtered trips
  const filteredTrips = useMemo(() => {
    if (!searchTerm) return trips;
    return trips.filter(trip =>
      trip.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      trip.destinations.some(dest =>
        dest.toLowerCase().includes(searchTerm.toLowerCase())
      )
    );
  }, [trips, searchTerm]);

  // Memoize callback to prevent unnecessary re-renders
  const handleTripClick = useCallback((trip: Trip) => {
    onTripSelect(trip);
  }, [onTripSelect]);

  // Virtual scrolling for large lists
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: filteredTrips.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120, // Estimated item height
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-96 overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const trip = filteredTrips[virtualItem.index];
          
          return (
            <div
              key={trip.id}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <TripCard trip={trip} onClick={handleTripClick} />
            </div>
          );
        })}
      </div>
    </div>
  );
});

TripList.displayName = 'TripList';
```

---

## Security Guidelines

### API Security

#### Authentication & Authorization
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Verify JWT token and return user."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Permission checking
class Permission(str, Enum):
    READ_TRIPS = "trips:read"
    WRITE_TRIPS = "trips:write"
    DELETE_TRIPS = "trips:delete"
    ADMIN_ACCESS = "admin:access"

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not await user_has_permission(current_user.id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission {permission} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### Input Validation & Sanitization
```python
from pydantic import BaseModel, Field, validator
import bleach
import re

class TripCreateRequest(BaseModel):
    """Validated request for trip creation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    destinations: List[str] = Field(..., min_items=1, max_items=10)
    budget: Optional[float] = Field(None, gt=0, le=1_000_000)
    
    @validator('name', 'description', pre=True)
    def sanitize_text(cls, v):
        """Sanitize text input to prevent XSS."""
        if v is None:
            return v
        # Remove HTML tags and dangerous characters
        return bleach.clean(v, tags=[], strip=True)
    
    @validator('destinations')
    def validate_destinations(cls, v):
        """Validate destination format."""
        if not v:
            raise ValueError("At least one destination is required")
        
        # Check for reasonable destination names
        for dest in v:
            if not re.match(r'^[a-zA-Z\s,.-]+$', dest):
                raise ValueError(f"Invalid destination format: {dest}")
            if len(dest) > 100:
                raise ValueError(f"Destination name too long: {dest}")
        
        return v

# SQL injection prevention with parameterized queries
async def get_trips_by_user_safe(user_id: UUID, db: AsyncSession) -> List[Trip]:
    """Safe database query using parameterized statements."""
    # SQLAlchemy automatically handles parameterization
    query = select(TripModel).where(TripModel.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()

# Rate limiting implementation
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for identifier."""
        now = time()
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        
        return False
```

### Data Protection

#### Encryption & Secrets Management
```python
from cryptography.fernet import Fernet
import os
import base64

class EncryptionService:
    """Service for encrypting sensitive data."""
    
    def __init__(self):
        # In production, get from secure key management service
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        
        self.cipher_suite = Fernet(key.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

# API key management with encryption
class APIKeyService:
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    async def store_api_key(
        self,
        user_id: UUID,
        service_name: str,
        api_key: str,
        db: AsyncSession
    ) -> None:
        """Store encrypted API key."""
        encrypted_key = self.encryption.encrypt(api_key)
        
        key_record = APIKeyModel(
            user_id=user_id,
            service_name=service_name,
            encrypted_key=encrypted_key,
            created_at=datetime.utcnow()
        )
        
        db.add(key_record)
        await db.commit()
    
    async def get_api_key(
        self,
        user_id: UUID,
        service_name: str,
        db: AsyncSession
    ) -> Optional[str]:
        """Retrieve and decrypt API key."""
        query = select(APIKeyModel).where(
            and_(
                APIKeyModel.user_id == user_id,
                APIKeyModel.service_name == service_name,
                APIKeyModel.is_active == True
            )
        )
        
        result = await db.execute(query)
        key_record = result.scalar_one_or_none()
        
        if not key_record:
            return None
        
        return self.encryption.decrypt(key_record.encrypted_key)
```

---

## Deployment Process

### Docker Configuration

#### Multi-stage Dockerfile
```dockerfile
# Dockerfile.api
FROM python:3.12-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash tripsage

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY tripsage/ /app/tripsage/
COPY tripsage_core/ /app/tripsage_core/
COPY scripts/ /app/scripts/

# Set ownership
RUN chown -R tripsage:tripsage /app

# Switch to non-root user
USER tripsage

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Expose port
EXPOSE 8001

# Start application
CMD ["python", "-m", "tripsage.api.main"]
```

#### Docker Compose for Development
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
      target: production
    ports:
      - "8001:8001"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/tripsage
      - REDIS_URL=redis://dragonfly:6379
    depends_on:
      - postgres
      - dragonfly
    volumes:
      - ./logs:/app/logs
    networks:
      - tripsage-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8001
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - tripsage-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=tripsage
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - tripsage-network

  dragonfly:
    image: docker.dragonflydb.io/dragonflydb/dragonfly:latest
    command: --logtostderr --cache_mode --requirepass development_password
    ports:
      - "6379:6379"
    volumes:
      - dragonfly_data:/data
    networks:
      - tripsage-network

volumes:
  postgres_data:
  dragonfly_data:

networks:
  tripsage-network:
    driver: bridge
```

### CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci-cd.yml
name: TripSage CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "18"

jobs:
  test-backend:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_tripsage
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install uv
      run: pip install uv
    
    - name: Install dependencies
      run: uv sync
    
    - name: Run linting
      run: |
        uv run ruff check .
        uv run ruff format --check .
    
    - name: Run type checking
      run: uv run mypy tripsage/ tripsage_core/
    
    - name: Run security scan
      run: uv run bandit -r tripsage/ tripsage_core/
    
    - name: Run tests
      run: uv run pytest --cov=tripsage --cov=tripsage_core --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_tripsage
        REDIS_URL: redis://localhost:6379
        ENVIRONMENT: testing
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  test-frontend:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ env.NODE_VERSION }}
        cache: 'pnpm'
        cache-dependency-path: frontend/pnpm-lock.yaml
    
    - name: Install pnpm
      run: npm install -g pnpm
    
    - name: Install dependencies
      run: |
        cd frontend
        pnpm install --frozen-lockfile
    
    - name: Run linting
      run: |
        cd frontend
        pnpm lint
    
    - name: Run type checking
      run: |
        cd frontend
        pnpm type-check
    
    - name: Run tests
      run: |
        cd frontend
        pnpm test:coverage
    
    - name: Build frontend
      run: |
        cd frontend
        pnpm build

  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    needs: [test-backend, test-frontend, security-scan]
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # Add deployment commands here

  deploy-production:
    if: github.ref == 'refs/heads/main'
    needs: [test-backend, test-frontend, security-scan]
    runs-on: ubuntu-latest
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # Add deployment commands here
```

### Production Deployment

#### Kubernetes Deployment
```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tripsage-api
  labels:
    app: tripsage-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tripsage-api
  template:
    metadata:
      labels:
        app: tripsage-api
    spec:
      containers:
      - name: api
        image: tripsage/api:latest
        ports:
        - containerPort: 8001
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: tripsage-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: tripsage-secrets
              key: redis-url
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: tripsage-api-service
spec:
  selector:
    app: tripsage-api
  ports:
  - port: 80
    targetPort: 8001
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tripsage-api-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.tripsage.ai
    secretName: tripsage-api-tls
  rules:
  - host: api.tripsage.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tripsage-api-service
            port:
              number: 80
```

---

## Summary

This Developer Guide provides comprehensive documentation for building, testing, and deploying TripSage AI. Key highlights:

### Modern Architecture
- **FastAPI + Next.js**: High-performance async backend with modern React frontend
- **Pydantic v2**: Type-safe data validation and serialization
- **LangGraph**: Sophisticated AI agent orchestration
- **DragonflyDB**: 25x faster caching performance

### Development Excellence
- **Type Safety**: Complete TypeScript and Python type hints
- **Testing**: 90%+ coverage with unit, integration, and E2E tests
- **Code Quality**: Automated linting, formatting, and security scanning
- **Performance**: Optimized queries, caching, and async operations

### Production Ready
- **Security**: Comprehensive authentication, authorization, and input validation
- **Scalability**: Horizontal scaling with load balancing and caching
- **Monitoring**: Health checks, logging, and performance metrics
- **CI/CD**: Automated testing, security scanning, and deployment

For additional resources, see:
- [User Guide](USER_GUIDE.md) - End-user documentation
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Testing Guide](TESTING_GUIDE.md) - Testing framework details
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment

Happy coding! 🚀